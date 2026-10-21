#!/usr/bin/env python3
"""
Build the package's environment files from the environment the authors actually used.

Usage:
    # minimal (default): only what the migrated code imports, pinned by role  → ships with the package
    python export_env.py --prefix <envs/name> --needs envs.json -o <pkg>/environment.yml --slug <slug> \
        [--r-out <pkg>/environment-R.yml] [--stata] [--add-missing <pkg> ...]
    python export_env.py -n <env-name> --needs envs.json -o ...        # same, env found by name
    # the authors' whole env, as a record (never shipped)
    python export_env.py --prefix <envs/name> --full -o <target>/_migration/environment-full.yml
    # old behaviour: explicitly requested packages (conda history), all pinned
    python export_env.py --prefix <envs/name> --top-level -o ...

Rules (see references/environments.md):
  * Minimal: keep the conda/pip packages that provide the imports listed in `--needs`
    (detect_envs.py --json, ideally run with --lineage so only migrated code counts), plus the
    conda-installed dependencies of pip packages (so pip does not build them), plus the runtime
    the package needs (python, pip, jupyterlab, ipykernel, nbclient, nbconvert; stata_setup with
    --stata or when Stata code is detected).
  * Pin by role: packages that compute results or draw compared figures are pinned exactly
    (`=x.y.z`, pip `==`); other Python-level packages to minor (`=x.y`); python to minor; system
    libraries are never listed. No build strings.
  * One language per env: `r-*` packages never go into the Python env. `--r-out` writes a separate
    R env (r-base at the authors' minor version, r-irkernel, r-remotes, the R packages the code uses
    that the authors had from conda, pinned, and the system libraries R packages compile against).
    Packages not covered there are installed by environment.R (detect_envs.py --write-r).
  * pip packages installed from git are written as `name @ git+URL@<commit>`.
Works without conda on PATH (--prefix reads conda-meta and site-packages directly).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable  # noqa: E402

# --- roles -------------------------------------------------------------------------------------
# exact pins: numerics, statistics, estimation, ML, optimization, geodata, plotting compared with the paper
PIN_EXACT = {
    "numpy", "scipy", "pandas", "polars", "pyarrow", "numba", "statsmodels", "linearmodels", "scikit-learn",
    "xgboost", "lightgbm", "catboost", "pytorch", "torch", "tensorflow", "jax", "jaxlib", "sympy", "cvxpy", "pyomo",
    "gurobipy", "pulp", "ortools", "networkx", "igraph", "python-igraph", "graph-tool", "pymc", "arviz", "emcee",
    "pystan", "cmdstanpy", "patsy", "formulaic", "pyfixest", "econtools", "rdrobust", "differences", "csdid",
    "geopandas", "shapely", "pyproj", "fiona", "pyogrio", "rasterio", "gdal", "rtree", "libpysal", "esda", "spreg",
    "pysal", "mgwr", "scikit-gstat", "pykrige", "gstools", "xarray", "rioxarray", "netcdf4", "h5py", "dask",
    "georasters", "geostats", "rasterstats", "osmnx", "momepy", "h3", "haversine", "geopy",
    "matplotlib", "seaborn", "plotnine", "plotly", "bokeh", "altair", "cartopy", "contextily", "mapclassify",
    "geoplot", "descartes", "python-kaleido", "kaleido", "pillow", "scikit-image", "opencv",
    "pandas-datareader", "pyreadstat", "openpyxl", "xlrd", "tables", "pytables", "linearmodels", "threadpoolctl",
}
RUNTIME = ["pip", "jupyterlab", "ipykernel", "nbclient", "nbconvert"]
# never listed in a portable env
SYSTEM_PREFIXES = ("lib", "_", "ca-certificates", "openssl", "tzdata", "python_abi", "blas", "icu", "curl", "zlib",
                   "xz", "bzip2", "zstd", "ncurses", "readline", "tk", "sqlite", "krb5", "openjdk", "c-ares", "giflib",
                   "freetype", "fontconfig", "cairo", "pango", "harfbuzz", "fribidi", "expat", "pcre", "gettext",
                   "geos", "proj", "tiledb", "hdf4", "hdf5", "netcdf-c", "poppler", "nss", "nspr", "llvm",
                   "clang", "gcc", "gxx", "gfortran", "compiler", "make", "cmake", "pkg-config", "ld64", "cctools",
                   "openblas", "mkl", "intel-openmp", "llvm-openmp", "tbb")
R_SYSTEM = ["cairo", "freetype", "fontconfig", "fribidi", "harfbuzz", "pkg-config", "make", "compilers"]
R_SPATIAL = {"sf", "terra", "raster", "rgdal", "sp", "stars", "exactextractr", "tigris", "rnaturalearth", "s2", "lwgeom"}
R_SPATIAL_SYSTEM = ["gdal", "proj", "geos", "udunits2"]


def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()


def is_system(name):
    return name.startswith(SYSTEM_PREFIXES) and name not in PIN_EXACT


def pin(name, version, pip=False):
    if not version:
        return name
    if pip:
        return f"{name}=={version}"
    if norm(name) in {norm(x) for x in PIN_EXACT}:
        return f"{name}={version}"
    parts = version.split(".")
    return f"{name}={'.'.join(parts[:2])}" if len(parts) >= 2 else f"{name}={version}"


# --- reading an environment -----------------------------------------------------------------------
def conda_records(prefix):
    recs = {}
    cm = prefix / "conda-meta"
    for j in cm.glob("*.json") if cm.is_dir() else []:
        try:
            d = json.loads(j.read_text())
        except Exception:
            continue
        ch = [x for x in (d.get("channel", "") or "").rstrip("/").split("/") if x]
        if ch and re.match(r"noarch|(linux|osx|win)-\w+$", ch[-1]):
            ch = ch[:-1]
        recs[d["name"].lower()] = {"version": d.get("version", ""), "build": d.get("build", ""),
                                   "channel": ch[-1] if ch else "", "files": d.get("files", []),
                                   "depends": [re.split(r"[\s=<>!]", x)[0].lower() for x in d.get("depends", [])]}
    return recs


def pip_dists(prefix):
    """{normalized name: {name, version, installer, top_level, requires, direct_url}} for dist-info folders"""
    out = {}
    for sp in list(prefix.glob("lib/python3*/site-packages")) + list(prefix.glob("Lib/site-packages")):
        for di in sp.glob("*.dist-info"):
            m = re.match(r"(.+?)-([^-]+)\.dist-info$", di.name)
            if not m:
                continue
            rd = lambda f: (di / f).read_text(errors="replace") if (di / f).exists() else ""  # noqa: E731
            top = [x.strip() for x in rd("top_level.txt").splitlines() if x.strip()]
            if not top:
                for ln in rd("RECORD").splitlines():
                    path = ln.split(",")[0]
                    if not path or path.startswith((di.name, "..", "__pycache__")) or ".dist-info/" in path:
                        continue
                    first = path.split("/")[0]
                    if "/" in path or first.endswith((".py", ".so", ".pyd")):
                        top.append(re.sub(r"(\.cpython.*)?\.(py|so|pyd)$", "", first))
                top = sorted(set(top))
            reqs = re.findall(r"^Requires-Dist:\s*([A-Za-z0-9_.-]+)(?![^\n]*extra\s*==)", rd("METADATA"), re.M)
            durl = {}
            try:
                durl = json.loads(rd("direct_url.json") or "{}")
            except ValueError:
                pass
            name = re.search(r"^Name:\s*(\S+)", rd("METADATA"), re.M)
            out[norm(m.group(1))] = {"name": name.group(1) if name else m.group(1), "version": m.group(2),
                                     "installer": rd("INSTALLER").strip(), "top_level": top,
                                     "requires": [norm(r) for r in reqs], "direct_url": durl}
    return out


def module_owners(prefix, recs, dists):
    """import name -> ('conda'|'pip', package name)"""
    owners = {}
    for name, r in recs.items():
        for f in r["files"]:
            m = re.match(r"(?:lib/python3[^/]*/site-packages|Lib/site-packages)/([^/]+)", f)
            if m:
                mod = m.group(1)
                if mod.endswith((".dist-info", ".egg-info", ".pth")) or mod == "__pycache__":
                    continue
                owners.setdefault(re.sub(r"(\.cpython.*)?\.(py|so|pyd)$", "", mod), ("conda", name))
    for key, d in dists.items():
        if d["installer"] == "pip":
            for mod in d["top_level"]:
                owners[mod] = ("pip", d["name"])
    return owners


def pip_spec(d):
    u = d.get("direct_url") or {}
    vcs = u.get("vcs_info") or {}
    if vcs.get("commit_id") and u.get("url"):
        return f"{d['name']} @ git+{u['url']}@{vcs['commit_id']}"
    if u.get("url", "").startswith("file:"):
        return f"{d['name']}=={d['version']}  # installed from a local folder ({u['url']}): ship it and install with pip install -e"
    return f"{d['name']}=={d['version']}"


def locate_prefix(name):
    for exe in ("mamba", "conda", "micromamba"):
        if shutil.which(exe):
            try:
                out = subprocess.run([exe, "env", "list", "--json"], capture_output=True, text=True, timeout=60).stdout
                for p in json.loads(out).get("envs", []):
                    if Path(p).name == name or (name == "base" and "/envs/" not in p):
                        return Path(p)
            except Exception:
                pass
    import detect_envs
    envs = detect_envs.env_list([])
    return envs.get(name)


def requested(prefix):
    import detect_envs
    return detect_envs.requested_specs(prefix)


# --- writers ------------------------------------------------------------------------------------
def yml(name, channels, conda, pip, comments=()):
    L = [f"name: {name}"] + [f"# {c}" for c in comments] + ["channels:"] + [f"  - {c}" for c in channels] + ["dependencies:"]
    L += [f"  - {d}" for d in conda]
    if pip:
        L.append("  - pip:")
        L += [f"    - {p}" for p in pip]
    return "\n".join(L) + "\n"


def channels_of(recs, names):
    ch = sorted({recs[n]["channel"] for n in names if n in recs and recs[n]["channel"]},
                key=lambda c: (c != "conda-forge", c))
    return [c for c in ch if c not in ("pypi",)] or ["conda-forge"]


def minimal(prefix, needs, stata, add_missing):
    recs, dists = conda_records(prefix), pip_dists(prefix)
    owners = module_owners(prefix, recs, dists)
    modules = sorted(needs.get("python", {}))
    conda, pipn, missing = set(), set(), []
    for mod in modules:
        o = owners.get(mod)
        if not o:
            missing.append(mod)
        elif o[0] == "conda":
            if not o[1].startswith("r-") and o[1] != "python":
                conda.add(o[1])
        else:
            pipn.add(norm(o[1]))
    if stata or needs.get("stata"):
        if "stata-setup" in dists:
            pipn.add("stata-setup")
        else:
            add_missing = list(add_missing) + ["pip:stata_setup"]
    # conda-installed dependencies of pip packages (recursively through pip-installed ones)
    seen, todo = set(), list(pipn)
    while todo:
        k = todo.pop()
        if k in seen or k not in dists:
            continue
        seen.add(k)
        for r in dists[k]["requires"]:
            if r in dists and dists[r]["installer"] == "pip":
                if r not in pipn:
                    pipn.add(r)
                todo.append(r)
            else:
                cand = r if r in recs else next((n for n in recs if norm(n) == r), None)
                if cand and not is_system(cand) and not cand.startswith("r-"):
                    conda.add(cand)
    py = recs.get("python", {}).get("version", "")
    lines = [f"python={'.'.join(py.split('.')[:2])}" if py else "python"]
    for n in RUNTIME:
        if n not in conda:
            lines.append(pin(n, recs[n]["version"]) if n in recs else n)
    lines += sorted((pin(n, recs[n]["version"]) for n in conda if n not in RUNTIME), key=str.lower)
    pip_lines = sorted((pip_spec(dists[k]) for k in pipn if k in dists), key=str.lower)
    for m in add_missing:
        if m.startswith("pip:"):
            pip_lines.append(f"{m[4:]}  # added: needed but not in the authors' env — confirm the version")
        else:
            lines.append(f"{m}  # added: imported by the code but not in the authors' env — confirm the version")
    return channels_of(recs, conda), lines, pip_lines, missing


def full(prefix):
    recs, dists = conda_records(prefix), pip_dists(prefix)
    conda = sorted(f"{n}={r['version']}={r['build']}" for n, r in recs.items())
    pip = sorted(pip_spec(d) for d in dists.values() if d["installer"] == "pip")
    return channels_of(recs, recs), conda, pip


def top_level(prefix):
    recs, dists = conda_records(prefix), pip_dists(prefix)
    req = requested(prefix)
    if not req:
        sys.exit(f"no conda-meta/history in {prefix}: cannot tell top-level packages apart (use --needs)")
    conda = [f"{n}={recs[n]['version']}" if n in recs else req[n].split("::")[-1]
             for n in sorted(req) if not is_system(n)]
    pip = sorted(pip_spec(d) for d in dists.values() if d["installer"] == "pip")
    return channels_of(recs, req), conda, pip


def r_env(prefix, needs, slug):
    recs = conda_records(prefix) if prefix else {}
    used = {x for x in needs.get("r", {})}
    rb = recs.get("r-base", {}).get("version", "")
    lines = [f"r-base={'.'.join(rb.split('.')[:2])}" if rb else "r-base", "r-irkernel", "r-remotes"]
    have = []
    for p in sorted(used, key=str.lower):
        k = f"r-{p.lower()}"
        if k in recs:
            lines.append(f"{k}={recs[k]['version']}")
            have.append(p)
    sysl = list(R_SYSTEM) + (R_SPATIAL_SYSTEM if used & R_SPATIAL else [])
    lines += [f"{s}  # system library (unpinned)" for s in sysl]
    return yml(f"{slug}-r", ["conda-forge"], lines, [],
               ["R environment (separate from the Python env). R packages not listed here are installed by environment.R."]), have


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--name", default=None, help="conda environment name")
    ap.add_argument("--prefix", default=None, help="environment folder (reads conda-meta directly)")
    ap.add_argument("--needs", default=None, help="detect_envs.py --json output (imports of the migrated code)")
    ap.add_argument("--full", action="store_true", help="whole env with builds, as a record (_migration/)")
    ap.add_argument("--top-level", action="store_true", help="explicitly requested packages (conda history)")
    ap.add_argument("-o", "--output", type=Path, default=Path("environment.yml"))
    ap.add_argument("--r-out", type=Path, default=None, help="also write the separate R env (environment-R.yml)")
    ap.add_argument("--slug", default=None, help="'name:' of the exported env (paper slug)")
    ap.add_argument("--stata", action="store_true", help="the package runs Stata via pystata (adds stata_setup)")
    ap.add_argument("--add-missing", nargs="*", default=[], help="packages to add (imports the env lacks); pip:NAME for pip")
    a = ap.parse_args()
    if not a.name and not a.prefix:
        sys.exit("give -n <env> or --prefix <env folder>")
    prefix = Path(a.prefix).expanduser() if a.prefix else locate_prefix(a.name)
    if not prefix or not (prefix / "conda-meta").is_dir():
        sys.exit(f"environment not found ({a.name or a.prefix}); pass --prefix <base>/envs/<name> (see detect_envs.py)")
    slug = a.slug or a.name or prefix.name
    needs = json.loads(Path(a.needs).read_text())["needs"] if a.needs else {}
    comments = []
    if a.full:
        ch, conda, pip = full(prefix)
        comments = [f"FULL record of the authors' environment {prefix} — not for installation on other platforms"]
        mode = "full"
    elif a.top_level or not a.needs:
        if not a.needs:
            print("ℹ️  no --needs given: exporting the explicitly requested packages (--top-level); "
                  "run detect_envs.py --json and pass --needs for the minimal environment", file=sys.stderr)
        ch, conda, pip = top_level(prefix)
        conda = [c for c in conda if not c.startswith("r-")]
        mode = "top-level"
    else:
        ch, conda, pip, missing = minimal(prefix, needs, a.stata, a.add_missing)
        mode = "minimal"
        comments = ["Minimal environment: packages the code imports. Result-computing packages pinned exactly,",
                    "others to minor versions, system libraries left to the solver. Built by export_env.py."]
        if missing:
            print(f"⚠️  imports not provided by {prefix.name}: {', '.join(missing)} — local modules, unused imports, "
                  "or installed another way. Ask, then use --add-missing.", file=sys.stderr)
    assert_writable(a.output)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(yml(slug, ch, conda, pip, comments), encoding="utf-8")
    print(f"✅ {a.output} ({mode}): {len(conda)} conda + {len(pip)} pip entries (from {prefix} → name '{slug}')")
    if a.r_out:
        text, have = r_env(prefix, needs, slug)
        assert_writable(a.r_out)
        a.r_out.write_text(text, encoding="utf-8")
        print(f"✅ {a.r_out}: R env with {len(have)} R package(s) from the authors' conda env; "
              f"the other {len(needs.get('r', {})) - len(have)} go to environment.R (detect_envs.py --write-r)")


if __name__ == "__main__":
    main()

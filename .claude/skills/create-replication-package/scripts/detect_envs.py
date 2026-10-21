#!/usr/bin/env python3
"""
Find the software environments a project was run with, and what its code needs — so the
package's environment files are built from the environment the authors actually used.

Usage:
    python detect_envs.py --project-root <source> [--extra-root <dir>] [--lineage lineage.json] \
        [--env-root <conda base or envs dir> ...] [--stata-ado <PLUS dir>] [--r-lib <R library> ...] \
        --report envs.md --json envs.json
    python detect_envs.py ... --env <name-or-prefix>       # coverage of one chosen env in detail
    python detect_envs.py ... --write-r <target>/replication-package/environment.R \
                              --write-stata <target>/replication-package/setup.do

What it reports
  * Evidence in the project: notebook kernelspecs (conda-env-<name>-py / -r), `conda|mamba|
    micromamba activate <name>` in .sh/.sbatch/notebooks, environment*.yml, requirements*.txt,
    renv.lock, DESCRIPTION, Project.toml, adolist *.pkl, setup.do.
  * Conda/mamba environments on this machine (via `mamba/conda/micromamba env list --json`, or by
    reading <base>/envs/*/conda-meta directly — works without conda on PATH, e.g. from a VM with the
    folder mounted), ranked by evidence and by how many of the code's imports they provide.
  * What the code needs: Python imports (minus the standard library), R packages
    (library/require/p_load/pkg::), Stata user-written commands (ssc/net install lines and common
    SSC commands used), Julia `using`.
  * For Stata: packages installed in the user's PLUS folder (stata.trk) with their source URLs.
  * For R: installed versions found in the env's R library or the user's R libraries.

--write-r writes environment.R that installs, with renv, the R packages the code uses that the
conda env does not already provide (pinned to the installed versions when known).
--write-stata writes setup.do that installs the user-written Stata packages the code uses, from the
exact source each was installed from (stata.trk), with adolist as an alternative.
Read-only on the project and on environments; writes only the requested outputs.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry  # noqa: E402

CODE_EXT = {".py", ".ipy", ".ipynb", ".do", ".ado", ".r", ".rmd", ".jl", ".sh", ".sbatch", ".slurm"}
SKIP = {".git", ".ipynb_checkpoints", "__pycache__", "node_modules", ".Trash"}
MODULE_TO_PKG = {"sklearn": "scikit-learn", "cv2": "opencv", "yaml": "pyyaml", "PIL": "pillow", "bs4": "beautifulsoup4",
                 "osgeo": "gdal", "mpl_toolkits": "matplotlib", "Bio": "biopython", "skimage": "scikit-image",
                 "dateutil": "python-dateutil", "gp": "geopandas", "geopandas": "geopandas", "shapely": "shapely",
                 "linearmodels": "linearmodels", "statsmodels": "statsmodels", "IPython": "ipython", "stata_setup": "stata_setup",
                 "pystata": "stata_setup", "rasterio": "rasterio", "fiona": "fiona", "pyproj": "pyproj", "netCDF4": "netcdf4",
                 "tables": "pytables", "Levenshtein": "python-levenshtein", "docx": "python-docx", "pptx": "python-pptx",
                 "sqlalchemy": "sqlalchemy", "georasters": "georasters", "geostats": "geostats", "rpy2": "rpy2",
                 "gdalconst": "gdal", "ogr": "gdal", "osr": "gdal", "gdal": "gdal", "google": "protobuf"}
COMMON_SSC = {"reghdfe", "ftools", "estout", "esttab", "eststo", "estadd", "outreg2", "binsreg", "binscatter", "ivreg2",
              "ranktest", "ivreghdfe", "ppmlhdfe", "gtools", "winsor2", "coefplot", "spmap", "shp2dta", "geodist", "geonear",
              "carryforward", "egenmore", "unique", "distinct", "fre", "labutil", "reclink", "matchit", "kountry",
              "ivqreg2", "boottest", "rdrobust", "csdid", "did_multiplegt", "eventstudyinteract", "acreg", "ols_spatial_HAC",
              "x_ols", "sxpose", "adolist", "grc1leg", "tuples", "rwolf", "wyoung", "psacalc", "texsave", "listtex",
              "ietoolkit", "missings", "statastates", "jarowinkler", "strgroup", "mdesc", "parmest", "regsave", "matsave",
              "erepost", "avar", "nwcommands", "spatwmat", "spatreg", "xtabond2", "synth", "rd", "rdplot", "cmogram", "conley"}
ESTOUT_ALIASES = {"esttab": "estout", "eststo": "estout", "estadd": "estout", "estpost": "estout"}


def walk(roots):
    for r in roots:
        for dp, dns, fns in os.walk(r):
            dns[:] = [d for d in dns if d not in SKIP]
            for f in fns:
                yield Path(dp) / f


def code_text(p):
    try:
        t = read_text_retry(p)
    except OSError:
        return None, None
    if p.suffix.lower() == ".ipynb":
        try:
            nb = json.loads(t)
        except ValueError:
            return None, None
        k = nb.get("metadata", {}).get("kernelspec", {}).get("name", "")
        src = "\n".join("".join(c["source"]) if isinstance(c["source"], list) else c["source"]
                        for c in nb.get("cells", []) if c.get("cell_type") == "code")
        return src, k
    return t, ""


def is_adolist(p):
    """adolist *.pkl files are small text files listing Stata packages (not Python pickles)."""
    try:
        if p.stat().st_size > 500_000:
            return False
        head = p.read_bytes()[:2000]
        return head[:1] != b"\x80" and (b"http" in head or b"ssc" in head.lower() or b".pkg" in head)
    except OSError:
        return False


def scan_project(roots, only=None):
    ev, needs = defaultdict(list), defaultdict(Counter)
    stdlib = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    local_mods = set()
    files = [p for p in walk(roots)]
    for p in files:
        if p.suffix.lower() in (".py", ".ipy"):
            local_mods.add(p.stem)
        if p.suffix.lower() == ".ado":
            ev["local_ado"].append(p.stem.lower())
    for p in files:
        name, low = p.name, p.name.lower()
        rel = str(p)
        if re.match(r"environment.*\.ya?ml$", low) or low in ("requirements.txt", "renv.lock", "description", "project.toml",
                                                              "manifest.toml", "pipfile", "pyproject.toml", "setup.do") \
                or (low.endswith(".pkl") and is_adolist(p)):
            ev["files"].append(rel)
            if low.startswith("environment"):
                try:
                    m = re.search(r"^name:\s*(\S+)", read_text_retry(p), re.M)
                    if m:
                        ev["env_names"].append((m.group(1), f"name in {name}"))
                except OSError:
                    pass
        if p.suffix.lower() not in CODE_EXT:
            continue
        if only is not None and not any(rel.endswith(o) for o in only):
            continue
        txt, kernel = code_text(p)
        if txt is None:
            continue
        m = re.match(r"conda-env-(.+?)-(py|r)$", kernel or "")
        if m:
            ev["env_names"].append((m.group(1), f"kernelspec of {name}"))
        elif kernel and kernel not in ("python3", "ir", "stata", "julia"):
            ev["kernels"].append((kernel, name))
        for m in re.finditer(r"(?:conda|mamba|micromamba|source)\s+activate\s+([\w.-]+)", txt):
            ev["env_names"].append((m.group(1), f"activate in {name}"))
        for m in re.finditer(r"/envs/([\w.-]+)/bin/(?:python|R)", txt):
            ev["env_names"].append((m.group(1), f"path in {name}"))
        ext = p.suffix.lower()
        lang = "stata" if ext in (".do", ".ado") or (ext == ".ipynb" and "%%stata" in txt) else \
               "r" if ext in (".r", ".rmd") or kernel in ("ir",) or (kernel or "").endswith("-r") else \
               "julia" if ext == ".jl" else "shell" if ext in (".sh", ".sbatch", ".slurm") else "python"
        if lang == "python" or ext == ".ipynb":
            for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+))", txt, re.M):
                mods = [m.group(1)] if m.group(1) else [x.strip().split(" as ")[0] for x in m.group(2).split(",")]
                for mod in mods:
                    top = mod.split(".")[0].strip()
                    if top and top not in stdlib and top not in local_mods and not top.startswith("_"):
                        needs["python"][top] += 1
        if lang == "r" or "%%R" in txt:
            for m in re.finditer(r"(?:library|require|requireNamespace)\(\s*['\"]?([\w.]+)", txt):
                needs["r"][m.group(1)] += 1
            for m in re.finditer(r"p_load\(([^)]*)\)", txt):
                for x in re.findall(r"[\w.]+", m.group(1)):
                    needs["r"][x] += 1
            for m in re.finditer(r"\b([A-Za-z][\w.]+)::", txt):
                needs["r"][m.group(1)] += 1
        if lang == "stata":
            for m in re.finditer(r"(?:ssc|net)\s+install\s+([\w-]+)", txt):
                needs["stata"][m.group(1).lower()] += 1
            for cmd in COMMON_SSC:
                if re.search(r"(?m)^\s*(?:\w+\s*:\s*)*(?:qui(?:etly)?\s+|cap(?:ture)?\s+|noi(?:sily)?\s+)*" + re.escape(cmd) + r"\b", txt):
                    needs["stata"][ESTOUT_ALIASES.get(cmd, cmd)] += 1
        if lang == "julia":
            for m in re.finditer(r"^\s*(?:using|import)\s+([\w., ]+)", txt, re.M):
                for x in m.group(1).split(","):
                    needs["julia"][x.strip().split(".")[0]] += 1
    needs["r"].pop("base", None)
    return ev, needs


# ---------------------------------------------------------------- conda environments
def env_list(env_roots):
    envs = {}
    for exe in ("mamba", "conda", "micromamba"):
        if shutil.which(exe):
            try:
                out = subprocess.run([exe, "env", "list", "--json"], capture_output=True, text=True, timeout=60).stdout
                for pref in json.loads(out).get("envs", []):
                    envs[Path(pref).name if "/envs/" in pref else "base"] = Path(pref)
                break
            except Exception:
                pass
    home = Path.home()
    bases = [Path(x).expanduser() for x in env_roots] + [home / b for b in
             ("miniforge3", "mambaforge", "miniconda3", "anaconda3", "opt/anaconda3", "opt/miniconda3", "micromamba", ".conda")] + \
            [Path("/opt/homebrew/Caskroom/miniforge/base"), Path("/opt/conda")]
    for b in bases:
        if (b / "conda-meta").is_dir():
            envs.setdefault("base", b)
        d = b / "envs" if (b / "envs").is_dir() else (b if b.name == "envs" else None)
        if d and d.is_dir():
            for e in d.iterdir():
                if (e / "conda-meta").is_dir():
                    envs.setdefault(e.name, e)
    return envs


PIP_REQUIRES = set()   # names required by pip-installed distributions (to keep only top-level pip packages)


def env_packages(prefix):
    """{name: (version, channel, source)} from conda-meta and pip dist-info, plus import names provided."""
    pk, provides = {}, set()
    cm = prefix / "conda-meta"
    for j in cm.glob("*.json") if cm.is_dir() else []:
        try:
            d = json.loads(j.read_text())
            ch = [x for x in (d.get("channel", "") or "").rstrip("/").split("/") if x]
            if ch and re.match(r"noarch|(linux|osx|win)-\w+$", ch[-1]):
                ch = ch[:-1]
            pk[d["name"].lower()] = (d.get("version", ""), ch[-1] if ch else "", "conda")
        except Exception:
            pass
    for sp in list(prefix.glob("lib/python3*/site-packages")) + list(prefix.glob("Lib/site-packages")):
        for di in sp.glob("*.dist-info"):
            m = re.match(r"(.+?)-([^-]+)\.dist-info$", di.name)
            if not m:
                continue
            nm = m.group(1).lower().replace("_", "-")
            inst = (di / "INSTALLER").read_text().strip() if (di / "INSTALLER").exists() else ""
            if nm not in pk or inst == "pip":
                pk[nm] = (m.group(2), "pypi" if inst == "pip" else "", "pip" if inst == "pip" else pk.get(nm, ("", "", "conda"))[2])
            meta = di / "METADATA"
            if meta.exists() and inst == "pip":
                reqs = re.findall(r"^Requires-Dist:\s*([A-Za-z0-9_.-]+)(?![^\n]*extra ==)", meta.read_text(errors="replace"), re.M)
                PIP_REQUIRES.update(r.lower().replace("_", "-") for r in reqs)
            tl = di / "top_level.txt"
            if tl.exists():
                provides |= {x.strip() for x in tl.read_text().splitlines() if x.strip()}
        for x in sp.iterdir():
            if x.is_dir() and (x / "__init__.py").exists():
                provides.add(x.name)
            elif x.suffix in (".py", ".so"):
                provides.add(x.name.split(".")[0])
    rlib = prefix / "lib" / "R" / "library"
    rpk = {}
    if rlib.is_dir():
        for d in rlib.iterdir():
            desc = d / "DESCRIPTION"
            if desc.exists():
                v = re.search(r"^Version:\s*(\S+)", desc.read_text(errors="replace"), re.M)
                rpk[d.name] = v.group(1) if v else ""
    return pk, provides, rpk


def requested_specs(prefix):
    """explicitly requested conda specs (like --from-history) from conda-meta/history"""
    h = prefix / "conda-meta" / "history"
    specs = []
    if h.exists():
        for line in h.read_text(errors="replace").splitlines():
            m = re.match(r"#\s*(?:update|install|create) specs:\s*\[(.*)\]", line)
            if m:
                specs += [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
            m = re.match(r"#\s*remove specs:\s*\[(.*)\]", line)
            if m:
                rm = {re.split(r"[=<> ]", x.strip().strip("'\""))[0] for x in m.group(1).split(",")}
                specs = [s for s in specs if re.split(r"[=<> ]", s)[0] not in rm]
    out = {}
    for s in specs:
        out[re.split(r"[=<>! ]", s.split("::")[-1])[0].lower()] = s
    return out


def r_libraries(extra):
    home = Path.home()
    libs = [Path(x).expanduser() for x in extra] + list(home.glob("Library/R/*/*/library")) + \
        list(Path("/Library/Frameworks/R.framework/Versions").glob("*/Resources/library")) + \
        list(home.glob("R/*/*")) + [Path("/usr/lib/R/library"), Path("/usr/local/lib/R/site-library")]
    found = {}
    for lib in libs:
        if lib.is_dir():
            for d in lib.iterdir():
                desc = d / "DESCRIPTION"
                if desc.exists() and d.name not in found:
                    v = re.search(r"^Version:\s*(\S+)", desc.read_text(errors="replace"), re.M)
                    found[d.name] = (v.group(1) if v else "", str(lib))
    return found


def stata_trk(plus_dirs):
    home = Path.home()
    cands = [Path(x).expanduser() for x in plus_dirs] + [home / "Library/Application Support/Stata/ado/plus", home / "ado/plus",
                                                         Path("C:/ado/plus")]
    for d in cands:
        trk = d / "stata.trk"
        if trk.exists():
            pk, src = {}, ""
            for line in trk.read_text(errors="replace").splitlines():
                if line.startswith("S "):
                    src = line[2:].strip()
                elif line.startswith("N "):
                    pk[line[2:].strip().replace(".pkg", "").lower()] = src
                elif line.startswith("D ") and pk:
                    pass
            return d, pk
    return None, {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--extra-root", action="append", default=[])
    ap.add_argument("--lineage", default=None, help="lineage.json: only consider the needed scripts")
    ap.add_argument("--env-root", action="append", default=[], help="conda base or envs dir (if not auto-detected)")
    ap.add_argument("--env", default=None, help="name or prefix of the chosen environment")
    ap.add_argument("--r-lib", action="append", default=[])
    ap.add_argument("--stata-ado", action="append", default=[])
    ap.add_argument("--report", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--write-r", default=None)
    ap.add_argument("--write-stata", default=None)
    a = ap.parse_args()
    roots = [Path(a.project_root).expanduser().resolve()] + [Path(x).expanduser().resolve() for x in a.extra_root]
    only = None
    if a.lineage:
        only = json.loads(Path(a.lineage).read_text())["needed_scripts"]
    ev, needs = scan_project(roots, only)
    envs = env_list(a.env_root)
    if a.env:
        p = Path(a.env).expanduser()
        envs = {p.name: p} if (p / "conda-meta").is_dir() else {k: v for k, v in envs.items() if k == a.env}

    hint = Counter(n for n, _ in ev["env_names"])
    py_needed = set(needs["python"])
    ranked = []
    for name, pref in envs.items():
        pk, provides, rpk = env_packages(pref)
        have = {m for m in py_needed if m in provides or m.lower() in pk or MODULE_TO_PKG.get(m, "").lower() in pk}
        rhave = {r for r in needs["r"] if r in rpk or f"r-{r.lower()}" in pk}
        score = 10 * hint.get(name, 0) + len(have) + len(rhave)
        ranked.append({"name": name, "prefix": str(pref), "evidence": [w for n, w in ev["env_names"] if n == name],
                       "python": pk.get("python", ("", "", ""))[0], "r": pk.get("r-base", ("", "", ""))[0],
                       "py_have": sorted(have), "py_missing": sorted(py_needed - have),
                       "r_have": sorted(rhave), "r_missing": sorted(set(needs["r"]) - rhave), "score": score})
    ranked.sort(key=lambda x: -x["score"])
    rlibs = r_libraries(a.r_lib)
    plus, trk = stata_trk(a.stata_ado)

    res = {"evidence": {k: v for k, v in ev.items()}, "needs": {k: dict(v) for k, v in needs.items()},
           "conda_envs": ranked, "stata_plus": str(plus) if plus else "", "stata_installed": trk,
           "r_libraries_found": len(rlibs)}
    L = ["# Environments", "", "## Evidence in the project", ""]
    for n, w in ev["env_names"]:
        L.append(f"- env `{n}` — {w}")
    for f in ev["files"]:
        L.append(f"- file `{f}`")
    if not ev["env_names"] and not ev["files"]:
        L.append("- none found")
    L += ["", "## Conda/mamba environments on this machine (best match first)", ""]
    if not ranked:
        L.append("- none found (no conda on PATH and no <base>/envs/*/conda-meta under the usual locations; "
                 "pass --env-root, or ask the user where their environments live)")
    for r in ranked[:8]:
        L.append(f"- **{r['name']}** (`{r['prefix']}`) python {r['python'] or '—'}, R {r['r'] or '—'}; "
                 f"imports provided {len(r['py_have'])}/{len(py_needed)}"
                 + (f"; evidence: {', '.join(r['evidence'][:3])}" if r["evidence"] else "")
                 + (f"; missing: {', '.join(r['py_missing'][:12])}" if r["py_missing"] else ""))
    L += ["", "## What the code needs", ""]
    for lang in ("python", "r", "stata", "julia"):
        if needs.get(lang):
            L.append(f"- **{lang}** ({len(needs[lang])}): " + ", ".join(sorted(needs[lang])))
    if needs.get("stata"):
        L += ["", f"## Stata packages installed (`{plus or 'PLUS folder not found — pass --stata-ado'}`)", ""]
        for p_ in sorted(needs["stata"]):
            L.append(f"- {p_}: " + (f"installed from {trk[p_]}" if p_ in trk else "**not found in stata.trk** (built-in, vendored .ado, or check)"))
    if needs.get("r"):
        L += ["", "## R packages (installed versions found)", ""]
        for p_ in sorted(needs["r"]):
            L.append(f"- {p_}: {rlibs[p_][0] + ' (' + rlibs[p_][1] + ')' if p_ in rlibs else 'not found in user R libraries'}")
    text = "\n".join(L) + "\n"
    if a.report:
        assert_writable(a.report, roots)
        Path(a.report).write_text(text)
    else:
        print(text)
    if a.json:
        assert_writable(a.json, roots)
        Path(a.json).write_text(json.dumps(res, indent=2, default=str))

    if a.write_r and needs.get("r"):
        assert_writable(a.write_r, roots)
        chosen = ranked[0] if ranked else None
        in_env = set(chosen["r_have"]) if chosen else set()
        todo = sorted(set(needs["r"]) - in_env)
        if not todo:
            lines = ["# All R packages used by the code are provided by the conda environment (environment.yml).",
                     "# Nothing to install here."]
        else:
            lines = ["# R packages used by the code that are not provided by the conda environment.",
                     "# Generated by detect_envs.py from the authors' installed versions; run inside the env:",
                     "#   mamba run -n <env> Rscript environment.R", "library(renv)", "renv::init(bare = TRUE)"]
            for p_ in todo:
                v = rlibs.get(p_, ("", ""))[0]
                lines.append(f'renv::install("{p_}@{v}")' if v else f'renv::install("{p_}")')
            lines += ['renv::settings$snapshot.type("all")', "renv::snapshot()"]
        Path(a.write_r).write_text("\n".join(lines) + "\n")
        print(f"✅ wrote {a.write_r} ({len(todo)} package(s) via renv; {len(in_env)} already in the conda env)")
    if a.write_stata and needs.get("stata"):
        assert_writable(a.write_stata, roots)
        lines = ["* Installs the user-written Stata packages used by this replication package.",
                 "* Generated by detect_envs.py from the authors' installation (stata.trk). Run once in Stata.", ""]
        local = set(ev.get("local_ado", []))
        for p_ in sorted(needs["stata"]):
            if p_ in local:
                lines.append(f"* {p_}: shipped with the package (.ado in progs/) — not installed here")
                continue
            src = trk.get(p_, "")
            if "repec/bocode" in src.lower() or not src:
                lines.append(f"capture noisily ssc install {p_}, replace")
            else:
                lines.append(f'capture noisily net install {p_}, from("{src}") replace')
        lines += ["", "* Alternative: restore the authors' full package list", "* net install adolist, from(http://fmwww.bc.edu/RePEc/bocode/a)",
                  "* adolist install <slug>.pkl", "", "* Version-sensitive packages vendored in progs/Stata/ (if any) are copied here:",
                  "* shell cp -f ./progs/Stata/<package-version>/* ./progs/Stata/"]
        Path(a.write_stata).write_text("\n".join(lines) + "\n")
        print(f"✅ wrote {a.write_stata} ({len(needs['stata'])} package(s))")


if __name__ == "__main__":
    main()

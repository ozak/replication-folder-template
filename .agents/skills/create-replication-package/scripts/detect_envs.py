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

Also reported: software versions to record (Python/R of the env, Stata `version` statements in the
code and Stata installations on the machine), packages installed from GitHub (with the commit), and
code that downloads at runtime (packages known to fetch data on first use, URLs/download calls).

--write-r writes environment.R: the R packages the code uses that the R env (environment-R.yml next
to it, from export_env.py --r-out) does not provide, at the authors' versions (CRAN archive) or
GitHub commits, dependents first and the packages they depend on LAST (so an extension cannot
upgrade its core package), then one version check per package.
--write-stata writes setup.do that installs the user-written Stata packages the code uses, from the
exact source each was installed from (stata.trk), with the installed version/date as a comment.
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
# packages that download data on first import / first use (offline compute nodes fail)
DOWNLOADS_AT_IMPORT = {"geostats": "dataset from Zenodo", "cartopy": "Natural Earth shapefiles", "nltk": "corpora (nltk.download)",
                       "osmnx": "OpenStreetMap queries", "pygris": "Census TIGER files", "geodatasets": "example data",
                       "wbdata": "World Bank API", "pandas_datareader": "remote data APIs", "yfinance": "Yahoo Finance",
                       "tigris": "Census TIGER files (R)", "rnaturalearth": "Natural Earth (R)", "tidycensus": "Census API (R)",
                       "WDI": "World Bank API (R)", "osmdata": "OpenStreetMap (R)", "geodata": "GADM/WorldClim downloads (R)"}
RE_DOWNLOAD = re.compile(r"(https?://[^\s'\"\)]+)|\b(urlretrieve|urlopen|requests\.get|wget|curl\s|download\.file|"
                         r"\.download\(|copy\s+\"?https?:|webuse|ssc\s+install|net\s+install)", re.I)
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
        for m in RE_DOWNLOAD.finditer(txt):
            if lang != "shell" or "download" in (m.group(0) or "").lower():
                ev["downloads"].append((name, (m.group(0) or "")[:90]))
        if lang == "stata":
            for m in re.finditer(r"(?m)^\s*version\s+(\d+(?:\.\d+)?)\b", txt):
                ev["stata_version"].append((m.group(1), name))
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


def r_description(desc):
    t = desc.read_text(errors="replace")
    t = re.sub(r"\n[ \t]+", " ", t)          # join continuation lines
    f = dict(re.findall(r"^([\w/@.-]+):\s*(.*)$", t, re.M))
    deps = []
    for k in ("Depends", "Imports", "LinkingTo"):
        deps += [re.split(r"[\s(]", x.strip())[0] for x in f.get(k, "").split(",") if x.strip()]
    remote = ""
    if f.get("RemoteType", "").lower() == "github" and f.get("RemoteSha"):
        remote = f"{f.get('RemoteUsername', '')}/{f.get('RemoteRepo', '')}@{f['RemoteSha']}"
    return f.get("Version", ""), {"deps": [d for d in deps if d and d != "R"], "remote": remote,
                                  "repository": f.get("Repository", "")}


def r_libraries(extra):
    """{package: (version, library, {deps, remote, repository})} from the R libraries found"""
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
                    try:
                        v, info = r_description(desc)
                    except OSError:
                        continue
                    found[d.name] = (v, str(lib), info)
    return found


def stata_trk(plus_dirs):
    """(PLUS dir, {package: source}, {package: version/date text}) from stata.trk"""
    home = Path.home()
    cands = [Path(x).expanduser() for x in plus_dirs] + [home / "Library/Application Support/Stata/ado/plus", home / "ado/plus",
                                                         Path("C:/ado/plus")]
    for d in cands:
        trk = d / "stata.trk"
        if trk.exists():
            pk, info, src, cur = {}, {}, "", None
            for line in trk.read_text(errors="replace").splitlines():
                if line.startswith("S "):
                    src = line[2:].strip()
                elif line.startswith("N "):
                    cur = line[2:].strip().replace(".pkg", "").lower()
                    pk[cur] = src
                elif line.startswith("D ") and cur:
                    info.setdefault(cur, {})["installed"] = line[2:].strip()
                elif line.startswith("d ") and cur:
                    t = line[2:].strip()
                    m = re.search(r"(?:Distribution-Date|version|v\.?)\s*:?\s*([\w.]+)", t, re.I)
                    if m and "version" not in info.setdefault(cur, {}):
                        info[cur]["version"] = m.group(1) if "Distribution" not in t else f"dist {m.group(1)}"
            return d, pk, info
    return None, {}, {}


def stata_installs():
    """Stata installations visible on this machine (folder, flavor executables)"""
    out = []
    cands = list(Path("/Applications").glob("Stata*")) + list(Path("/usr/local").glob("stata*")) + \
        list(Path("/opt").glob("stata*")) + list(Path("C:/Program Files").glob("Stata*"))
    for c in cands:
        exes = [x.name for x in c.glob("**/stata-*") if x.name in ("stata-mp", "stata-se", "stata-be")][:3] if c.is_dir() else []
        out.append({"path": str(c), "flavors": exes, "pystata": (c / "utilities" / "pystata").is_dir()})
    for exe in ("stata-mp", "stata-se", "stata"):
        w = shutil.which(exe)
        if w:
            out.append({"path": str(Path(w).resolve().parent), "flavors": [exe], "pystata": (Path(w).resolve().parent / "utilities" / "pystata").is_dir()})
    return out


def yml_r_packages(path):
    """R package names provided by an environment-R.yml (r-<name> entries)"""
    try:
        t = Path(path).read_text()
    except OSError:
        return set()
    return {m.group(1) for m in re.finditer(r"^\s*-\s*r-([\w.]+)", t, re.M)} - {"base", "irkernel", "remotes", "renv"}


def write_environment_r(path, needs_r, rlibs, provided, r_version):
    """dependents first, the packages they depend on last, then version checks"""
    todo = sorted(set(needs_r) - provided, key=str.lower)
    if not todo:
        return ["# All R packages used by the code are provided by environment-R.yml. Nothing to install here."], 0
    deps = {p_: set(rlibs.get(p_, ("", "", {"deps": []}))[2]["deps"]) & set(todo) for p_ in todo}
    # depth = length of the longest chain of packages (within todo) that depend on p_
    rev = {p_: {q for q in todo if p_ in deps[q]} for p_ in todo}
    depth = {}

    def dep_depth(p_, seen=()):
        if p_ in depth:
            return depth[p_]
        if p_ in seen:
            return 0
        depth[p_] = 1 + max([dep_depth(q, seen + (p_,)) for q in rev[p_]] or [-1])
        return depth[p_]
    order = sorted(todo, key=lambda p_: (dep_depth(p_), p_.lower()))
    L = ["# Installs the R packages used by the code that environment-R.yml does not provide, at the",
         "# authors' versions. Generated by detect_envs.py. Run inside the R environment:",
         "#   mamba run -n <slug>-r Rscript environment.R",
         f"# Authors' R version: {r_version or 'unknown — ask'}",
         "# Order: packages that depend on others first; the packages they depend on LAST, so that",
         "# installing an extension cannot upgrade its core package. Do not reorder.",
         'options(repos = c(CRAN = "https://cloud.r-project.org"))',
         'if (!requireNamespace("remotes", quietly = TRUE)) install.packages("remotes")',
         'pin <- function(pkg, version) remotes::install_version(pkg, version = version, upgrade = "never", dependencies = NA)',
         'gh  <- function(ref) remotes::install_github(ref, upgrade = "never", dependencies = NA)', ""]
    checks, unknown = [], []
    for p_ in order:
        v, _, info = rlibs.get(p_, ("", "", {"remote": "", "deps": []}))
        if info.get("remote"):
            L.append(f'gh("{info["remote"]}")   # {p_} {v} from GitHub at a fixed commit')
        elif v:
            L.append(f'pin("{p_}", "{v}")')
        else:
            L.append(f'install.packages("{p_}")   # version not found on the authors\' machine — ask and pin')
            unknown.append(p_)
        if v:
            checks.append(f'  "{p_}" = "{v}"')
    L += ["", "# Every package must have the authors' version", "expected <- c(", ",\n".join(checks), ")",
          "for (p in names(expected)) {",
          "  got <- as.character(packageVersion(p))",
          '  if (got != expected[[p]]) stop(sprintf("%s is %s, expected %s", p, got, expected[[p]]))',
          "}", 'cat("All", length(expected), "R packages have the expected versions\\n")']
    return L, len(todo)


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
    chosen = ranked[0] if ranked else None
    env_rlib = [str(Path(chosen["prefix"]) / "lib" / "R" / "library")] if chosen else []
    rlibs = r_libraries(env_rlib + a.r_lib)   # the chosen env's R library first
    plus, trk, trk_info = stata_trk(a.stata_ado)
    installs = stata_installs()
    r_version = (chosen or {}).get("r", "") or next((re.search(r"/(\d+\.\d+)(?:-arm64|-x86_64)?/", v[1]).group(1)
                                                     for v in rlibs.values() if re.search(r"/(\d+\.\d+)(?:-arm64|-x86_64)?/", v[1])), "")
    software = {"python": (chosen or {}).get("python", ""), "r": r_version,
                "stata_version_in_code": sorted({v for v, _ in ev["stata_version"]}),
                "stata_installations": installs}
    github_r = {p_: rlibs[p_][2]["remote"] for p_ in needs["r"] if p_ in rlibs and rlibs[p_][2]["remote"]}
    downloads_pkgs = {m: DOWNLOADS_AT_IMPORT[m] for m in list(needs["python"]) + list(needs["r"]) if m in DOWNLOADS_AT_IMPORT}

    res = {"evidence": {k: v for k, v in ev.items()}, "needs": {k: dict(v) for k, v in needs.items()},
           "conda_envs": ranked, "stata_plus": str(plus) if plus else "", "stata_installed": trk,
           "stata_package_versions": trk_info, "software": software, "r_github": github_r,
           "downloads_at_import": downloads_pkgs, "r_libraries_found": len(rlibs)}
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
    L += ["", "## Software versions to record (replication-info.json → software; confirm with the user)", ""]
    L.append(f"- Python {software['python'] or '—'}; R {software['r'] or '—'}")
    if needs.get("stata") or ev["stata_version"]:
        L.append(f"- Stata `version` statements in the code: {', '.join(software['stata_version_in_code']) or 'none'} "
                 "— ask which Stata version and flavor produced the paper's numbers")
        for i in installs:
            L.append(f"- Stata installation: `{i['path']}` {', '.join(i['flavors'])}" + (" (pystata found)" if i["pystata"] else ""))
    if needs.get("stata"):
        L += ["", f"## Stata packages installed (`{plus or 'PLUS folder not found — pass --stata-ado'}`)", ""]
        for p_ in sorted(needs["stata"]):
            ver = trk_info.get(p_, {})
            vtxt = f" — {ver.get('version', '')} installed {ver.get('installed', '')}".rstrip() if ver else ""
            L.append(f"- {p_}: " + (f"installed from {trk[p_]}{vtxt}" if p_ in trk else "**not found in stata.trk** (built-in, vendored .ado, or check)"))
    if needs.get("r"):
        L += ["", "## R packages (installed versions found)", ""]
        for p_ in sorted(needs["r"]):
            if p_ in rlibs:
                v, lib, info = rlibs[p_]
                L.append(f"- {p_}: {v} ({lib})" + (f" — GitHub `{info['remote']}`" if info["remote"] else ""))
            else:
                L.append(f"- {p_}: not found in the R libraries searched (pass --r-lib)")
    if downloads_pkgs or ev["downloads"]:
        L += ["", "## Runtime downloads (fail on offline compute nodes; vendor the data or document a first run online)", ""]
        for m, what in sorted(downloads_pkgs.items()):
            L.append(f"- package `{m}` downloads {what} on first use")
        for f, hit in ev["downloads"][:40]:
            L.append(f"- `{f}`: `{hit}`")
        if len(ev["downloads"]) > 40:
            L.append(f"- … {len(ev['downloads']) - 40} more")
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
        ryml = Path(a.write_r).with_name("environment-R.yml")
        provided = yml_r_packages(ryml) if ryml.exists() else set()
        lines, n = write_environment_r(a.write_r, needs["r"], rlibs, provided, r_version)
        Path(a.write_r).write_text("\n".join(lines) + "\n")
        print(f"✅ wrote {a.write_r} ({n} package(s); {len(provided & set(needs['r']))} provided by "
              f"{ryml.name if ryml.exists() else 'no environment-R.yml found next to it'})")
    if a.write_stata and needs.get("stata"):
        assert_writable(a.write_stata, roots)
        sv = ", ".join(software["stata_version_in_code"]) or "unknown"
        lines = ["* Installs the user-written Stata packages used by this replication package.",
                 "* Generated by detect_envs.py from the authors' installation (stata.trk). Run once in Stata.",
                 f"* Stata version used by the authors: {sv} (from `version` statements; confirm). Results and runtimes",
                 "* can differ with another Stata version or with newer package versions (SSC installs the current one).", ""]
        local = set(ev.get("local_ado", []))
        for p_ in sorted(needs["stata"]):
            if p_ in local:
                lines.append(f"* {p_}: shipped with the package (.ado in progs/) — not installed here")
                continue
            src = trk.get(p_, "")
            ver = trk_info.get(p_, {})
            note = f"   // authors had: {ver.get('version', '?')}, installed {ver.get('installed', '?')}" if ver else \
                   "   // authors' version unknown"
            if "repec/bocode" in src.lower() or not src:
                lines.append(f"capture noisily ssc install {p_}, replace{note}")
            else:
                lines.append(f'capture noisily net install {p_}, from("{src}") replace{note}')
        lines += ["", "* If a package changed its estimator since the authors' version, vendor the authors' version",
                  "* into progs/Stata/ (copied below) or use the command's version option (e.g. reghdfe ..., version(5)).",
                  "* Alternative: restore the authors' full package list", "* net install adolist, from(http://fmwww.bc.edu/RePEc/bocode/a)",
                  "* adolist install <slug>.pkl", "", "* Version-sensitive packages vendored in progs/Stata/ (if any) are copied here:",
                  "* shell cp -f ./progs/Stata/<package-version>/* ./progs/Stata/"]
        Path(a.write_stata).write_text("\n".join(lines) + "\n")
        print(f"✅ wrote {a.write_stata} ({len(needs['stata'])} package(s))")


if __name__ == "__main__":
    main()

# Software environments: rules

Read in Phase 1 (detection) and Phase 3 (export). Concrete cases are in `known-issues.md`.

## 1. Ship the minimal environment, not the working one

The authors' working env usually holds everything they ever installed. A replicator needs only
what the package's code loads.

* **Python**: `export_env.py --needs envs.json` (the minimal export) keeps the packages that provide the imports
  found by `detect_envs.py` in the migrated code (`--needs envs.json`), plus what those packages
  need that conda must provide (the conda-side dependencies of pip packages, so pip does not build
  them itself), plus the runtime pieces the package always needs (python, pip, ipykernel, nbclient,
  nbconvert, jupyterlab; `stata_setup`/pystata when Stata is used).
* **R**: `environment.R` installs only packages loaded by the migrated R code (`library`,
  `require`, `pkg::`), with versions from the authors' library.
* **Stata**: `setup.do` installs only user-written commands the migrated `.do`/notebooks call.
* Always keep the **full** working env as a record: `export_env.py --full -o _migration/environment-full.yml`.
  It is never shipped, but explains any difference later.

## 2. Pin by role

| Role | Pin? | Examples |
|---|---|---|
| Computes results: numerics, statistics, estimation, ML, optimization, geodata, spatial statistics | **exact** (`==` for pip, `=x.y.z` for conda) | numpy, scipy, pandas, statsmodels, linearmodels, scikit-learn, geopandas, shapely, pyproj, rasterio, gdal, scikit-gstat, pykrige; R: fixest, sf, terra, data.table, dplyr |
| Draws figures that are compared with the paper | **exact**, together with every extension of it | matplotlib, seaborn, plotnine; ggplot2 + cowplot, patchwork, ggpubr, ggnewscale, ggpattern, hrbrthemes |
| Language runtime | **minor** (`python=3.11`, R 4.3.*) | python, r-base |
| Everything else Python/R level | **minor** or authors' version | requests, tqdm |
| System / C libraries | **never** | openssl, curl, icu, libgdal-core builds, libblas, openjdk, compilers |

The classification lives in `export_env.py` (`PIN_EXACT` list + heuristics). When unsure, pin
the version without the build string. Never pin build strings — they are platform-specific.

## 3. One language, one environment

* Python env: no `r-*` packages (they bring a second R and many system libraries).
* R env (`environment-R.yml`, created only if R is used): `r-base`, `r-irkernel`, the R packages
  available on conda-forge with their versions, plus system libraries R packages compile against
  (`cairo freetype fontconfig pkg-config`, `gdal proj geos udunits2` for spatial work).
  `environment.R` then installs what is not on conda-forge (CRAN archive versions, GitHub commits)
  and checks the version of every pinned package.
* Each env registers its own Jupyter kernel (`python3` from the Python env, `ir` from the R env),
  with an `env` block for variables the runtime needs (e.g. `PROJ_DATA`, `GDAL_DATA` for R).
* Stata, MATLAB, Julia: record version and install method; Julia ships `Project.toml` + `Manifest.toml`.

## 4. Order and pins for packages that depend on each other

When a package has extensions (ggplot2 and its add-ons, `fixest` and helpers), install the
extensions first and the pinned core package **last**, then check:

```r
remotes::install_version("ggplot2", version = "3.4.4", repos = "https://cloud.r-project.org", upgrade = "never")
stopifnot(packageVersion("ggplot2") == "3.4.4")
```

Installing an extension later silently upgrades the core package. `environment.R` written by
`detect_envs.py --write-r` follows this order and ends with one `stopifnot` per pinned package.

## 5. Fixed install sources

* CRAN: `remotes::install_version(pkg, version)` (archive), never plain `install.packages`.
* GitHub / forks: at the exact commit — `remotes::install_github("user/repo@<sha>")`
  (`RemoteSha` in the installed `DESCRIPTION`), `pip install "pkg @ git+https://github.com/u/r@<sha>"`
  (`direct_url.json` in the dist-info).
* Local packages: shipped inside the package (`raw-data/<Source>/…` or `progs/…`) and installed with
  `pip install -e` / `R CMD INSTALL` from `create_env.sh`.
* SSC / net: record the installed version (`stata.trk`, `which <cmd>`); if the estimator changed,
  vendor the authors' version into `progs/Stata/` or use the command's version option.

## 6. Check before shipping

```bash
python3 -B SKILL_DIR/scripts/check_env.py "<target>/replication-package/environment.yml" [environment-R.yml]
```

It solves each env for `linux-64` and `osx-arm64` (add `--platforms win-64` if asked) with
`--dry-run` — nothing is installed — using `mamba`, `micromamba` or `conda`, whichever exists. On a
conflict it names the package(s) and suggests which pin to relax (system libraries first, then
minor-pinned packages; never a result-computing package without asking). Each solve takes about a
minute.

Then, with the user's agreement (it installs), **build once and prove it reproduces**: create the
env, run the fast notebooks with the runner, and compare their outputs file by file with the outputs
from the authors' env (see `reproducibility.md` §5).

## 7. Record exact versions

`replication-info.json` → `software`: Python, R, Stata (flavor + version + build date), Julia,
MATLAB, Gurobi…, and the OS of the machine that produced the paper's numbers. Ask for the Stata
version in Phase 1: a different version can change results (estimator defaults) and runtime. Before
a long run with a different version, time a small sample with both if possible.

## 8. Code that downloads at runtime

`detect_envs.py` flags (a) packages known to download data at first import or first use
(`DOWNLOADS_AT_IMPORT` list: e.g. `geostats`, `cartopy` Natural Earth, `nltk` corpora, `osmnx`,
`pygris`/`tigris`, `rnaturalearth`), and (b) URLs and `download`/`urlretrieve`/`requests.get` calls
in the migrated code. For each: vendor the data into `raw-data/` (preferred, with citation and access
date) or tell the replicator to run the first import on a machine with internet before going to
offline compute nodes (README + index.ipynb note).

## 9. Install scripts

`create_env.sh` must run unattended (`-y`), need no `sudo`, and keep every machine-specific line
(cluster `module load`, Stata path, proxy) in the **EDIT HERE** block at the top. Recommend
miniforge (`mamba`). One install at a time per package cache.

## 10. Troubleshooting (also in the README template)

* `SHA256 doesn't match`, `CondaVerificationError`, corrupted tarballs: `mamba clean --all -y`,
  then retry; never run two installs sharing a cache at once; check disk quota.
* Solve takes forever: use mamba/miniforge, not an old cluster `conda` module; check that the
  yml has no system-library pins.
* R package fails to compile: missing system libraries in the R env (see the table in §3).

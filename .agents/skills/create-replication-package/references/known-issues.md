# Known issues (catalogue)

Concrete problems met in real packages, each tied to a **general rule** in SKILL.md or another
reference. Use this file to recognize a symptom quickly. Never apply a fix just because it is
listed here: apply it when the symptom shows up, and tell the user. Add new entries at the end of
the section they belong to (symptom · cause · fix · package where it was met).

## Environments (rules: `environments.md`)

| Symptom | Cause | Fix | Met in |
|---|---|---|---|
| `mamba env create` runs for hours or fails on Linux on pins such as `curl`, `icu`, `libgdal` | exported the whole working env (100+ packages, incl. system libraries pinned to macOS builds) | `export_env.py` (minimal export, default); full export only as `_migration/environment-full.yml` | MS15875 |
| A second R appears in the Python env; R packages compile against the wrong R | `r-*` packages in the Python env | separate R env (`environment-R.yml`); `export_env.py` drops `r-*` from the Python env | MS15875 |
| `SHA256 doesn't match` / `CondaVerificationError` | two installs sharing one package cache at the same time, interrupted download, full disk/quota | `mamba clean --all -y`; one install at a time; check quota (`quota -s`, `df -h ~`) | MS15875 |
| Cluster `conda` module takes very long to solve | old conda/solver on the cluster module | install miniforge in `$HOME` (or project space) and use `mamba` | MS15875 |
| R figures differ: lighter legend keys, different spacing | ggplot2 ≤3.4 vs ≥3.5 changed legend-key drawing | pin ggplot2 (+ its extensions) to the authors' version, install it last, check it | MS15875 |
| `could not find function "group_by_"` inside `tigris::geo_join()` | dplyr ≥1.2 removed the deprecated underscore verbs | pin dplyr 1.1.4 (or the authors' version) | MS15875 |
| `gdtools` (needed by hrbrthemes) fails to compile on Linux | Cairo/FreeType/fontconfig headers missing | add `r-gdtools cairo freetype fontconfig pkg-config` to the R env | MS15875 |
| R maps fail with `PROJ: proj_create_from_database: Cannot find proj.db` or use a wrong PROJ version | R kernel launched from another env inherits its `PROJ_DATA`/`GDAL_DATA` | kernelspec `env` block set by `create_env.sh` | MS15875 |
| First import fails on a compute node without internet | package downloads data at import (`geostats` → Zenodo) | import once on a login node / node with internet, or vendor the data into `raw-data/` and set the package's data-dir variable | MS15875 |
| Authors' fork behaves differently from CRAN/PyPI version (`did2s`) | package installed from a GitHub fork | install the fork at the exact commit (`remotes::install_github("user/repo@<sha>")`, `pip install git+…@<sha>`) | MS15875 |
| `AttributeError: module 'collections' has no attribute 'Mapping'` | legacy package on Python ≥3.10 | `sitecustomize.py` shim written by `create_env.sh`, or pin Python | OriginLanguages |

## Stata

| Symptom | Cause | Fix | Met in |
|---|---|---|---|
| Different coefficients/SEs with the same code | newer `reghdfe`/`ftools` (SSC installs current versions) | record installed versions in `setup.do`; vendor the old version or use its `version(5)` option | OriginLanguages, MS15875 |
| `margins` after `spregress` ~4× slower | Stata 19 vs the authors' Stata 18 | use the authors' Stata version; time a small sample first | MS15875 |
| `import stata_init` fails sporadically | no free licence seat / Stata could not start | runner retries start failures (`run_notebooks.py`) | MS15875 |

## LaTeX (rules: SKILL.md Phase 5 — compile and check after every rewrite)

| Symptom | Cause | Fix | Met in |
|---|---|---|---|
| `Misplaced \noalign` at `\bottomrule` after an `\input` table body | LaTeX ≥2020 file hooks wrap `\input` | define `\makeatletter\newcommand{\inputbody}[1]{\@@input #1 }\makeatother` and use `\inputbody{tables/Table-1.tex}` for bodies | MS15875 |
| `\subref` prints `??` or errors (TeX Live 2026, amsmath + subcaption) | package interaction | fallback: `\providecommand{\subref}[1]{\ref{#1}}` after the packages, or use `\ref{fig:x}` with subfigure labels | MS15875 |
| Captions read "Hình"/"Bảng" (or another language) | babel loaded a language last (e.g. for a Vietnamese word) | `\selectlanguage{english}` after `\begin{document}`; use `\foreignlanguage{…}{…}` locally | MS15875 |
| Cross-references between paper and appendix are `??` | xr/xr-hyper needs the other document's `.aux` | compile paper, then appendix, then paper again — in sequence, never in parallel; never delete `.aux` files | MS15875 |
| Figure numbers in the package shifted by one | TikZ figures, hand-written tables or subfigure captions counted wrongly | check every number against the compiled `.aux`/PDF (SKILL.md Phase 2) | MS15875 |

## Reproducibility (rules: `reproducibility.md`)

| Symptom | Cause | Fix | Met in |
|---|---|---|---|
| Variogram/kriging fit differs between runs although seeded | multithreaded sums in k-means binning (scikit-gstat) | run the fit inside `threadpoolctl.threadpool_limits(1)` | MS15875 |
| `.dta`/`.csv` differs byte-wise but values are equal | column order built from a `set` or dict | sort or fix the column list | MS15875 |
| Fit results change after an update | SciPy ≥1.15, scikit-gstat 1.0.22 changed optimizers/defaults | pin to the authors' versions | MS15875 |
| Fragile fits differ between Mac and Linux | Apple Accelerate vs OpenBLAS/MKL | flag the step for the reference machine; report the size of the difference | MS15875 |

## Errors in the original code (rules: SKILL.md Phase 2, "Check the original for errors")

| Symptom | Cause | Met in |
|---|---|---|
| Three panels of one figure show the same picture | loop body used a fixed file name instead of `` `var' `` | MS15875 (Figure E3) |
| Two tables meant to differ (radius 5 vs 10) are identical | the code used the same parameter for both | MS15875 (Tables I1–I4) |
| A figure in the paper differs from the regenerated one | figure in the paper made from an older data vintage | MS15875 (Figure 4-b) |

## Backup and syncing (rules: `backup.md`)

| Symptom | Cause | Fix | Met in |
|---|---|---|---|
| DVC cannot restore PDF versions | Google Drive appended `.pdf` to extension-less cache objects | local DVC cache outside synced drives; check cache after each commit | MS15875 |
| Bulk `rm` refused | permission check on deletion | copy to `_migration/removed/` first, then remove | MS15875 |

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a **template** for academic research replication packages. It provides a standardized folder structure, environment setup, and workflow notebooks for papers that mix Python, Stata, and R analysis. When adapting for a specific paper, replace placeholders like `TITLE`, `AWESOME PAPER`, `awesome-project`, and `XXX` throughout the files with actual paper details.

## Repository Layout

```
replication-folder-template/
├── 1-paper/              # LaTeX source (main.tex, bibliography.bib)
├── 2-appendix/           # LaTeX appendix source
├── replication-package/  # Self-contained replication package
│   ├── index.ipynb       # Master orchestration notebook — runs everything
│   ├── environment.yml   # Minimal Python environment (no R)
│   ├── environment-R.yml # Separate R environment (only if R is used)
│   ├── environment.R     # R packages at the authors' versions
│   ├── create_env.sh     # One-step environment creation script
│   ├── setup.do          # Stata package installer (run once in Stata)
│   ├── progs/Python/     # Python Jupyter notebooks
│   └── progs/Stata/      # Stata notebooks (pystata: python3 kernel, `import stata_init`, %%stata cells)
└── replication-zip.ipynb # Creates distributable zip files for submission
```

## Environment Setup

```bash
cd replication-package
bash create_env.sh
```

`create_env.sh` runs unattended (mamba > micromamba > conda, no sudo). Machine-specific lines (cluster `module load`, `USE_ACCELERATE` on macOS) live in its EDIT HERE block. It creates:
- the **Python env** from `environment.yml` — minimal: only what the code imports, result-computing packages pinned exactly, system libraries unpinned, **no `r-*` packages**; registers a Python kernel;
- the **R env** from `environment-R.yml` (only if present) — `r-base`, `r-irkernel`, R packages from conda-forge, system libraries R packages compile against; then runs `environment.R` (CRAN-archive/GitHub installs at the authors' versions, core packages last, version checks) and registers the `ir` kernel with `PROJ_DATA`/`GDAL_DATA` from the R env.

**Stata packages** (run once from within Stata): `do replication-package/setup.do`. It installs each user-written package from its source (authors' versions noted); `adolist install <name>.pkl` is the alternative. Stata runs through **pystata** (`stata_setup` in the Python env).

## Running the Analysis

All steps are orchestrated from `replication-package/index.ipynb`. Before running:

1. Edit `STATA_location` and `version` in the first code cell to point to your Stata installation (e.g., `/Applications/Stata`, `mp`).
2. Run that cell — it writes `progs/Stata/stata_init.py`, which child Stata notebooks `%run` to configure `stata_setup`. **Individual Stata notebooks will fail if this file doesn't exist.**
3. Launch JupyterLab: `jupyter lab`
4. Open `index.ipynb`, restart kernel, and run all cells.

`index.ipynb` runs each child notebook with `progs/Python/run_notebooks.py` (`runner.step("progs/Python/X.ipynb", after=[...])`): in the notebook's folder, no timeout, saved and exported to `html/` even when it fails, Stata notebooks limited to the licence seats, notebooks whose first cell fails (Stata could not start) retried, dependents of failed steps skipped. `PARALLEL = True` in the runner cell runs independent notebooks at once (longest first). Cells guarded by `should_I_run = False` are skipped by default — set to `True` to enable expensive or conditional steps.

**Execute a single Python notebook from the command line:**
```bash
cd replication-package/progs/Python
jupyter nbconvert "NotebookName.ipynb" --to notebook \
  --ExecutePreprocessor.kernel_name=python3 --execute \
  --output "NotebookName.ipynb"
```

**Execute a single Stata notebook:**
```bash
cd replication-package/progs/Stata
jupyter nbconvert "NotebookName.ipynb" --to notebook \
  --execute --ExecutePreprocessor.kernel_name=python3 \
  --output "NotebookName.ipynb"
```

**Execute a Stata `.do` file and capture log:**
```bash
cd replication-package/progs/Stata && stata-mp -b do script.do
```

## Creating the Replication Zip

Run `replication-zip.ipynb` from the repo root. It:
1. Scans `replication-package/` into a DataFrame with an `include` column (default `True`).
2. Sets `include=False` for licensed/confidential dataset rows via `df_files.loc[...]`.
3. Generates `replication-package/directory_structure.{txt,html,md}` — the HTML version is embedded in `replication-package/README.md` via an `<iframe>`.
4. Produces three zip files:
   - `3-replication-package.zip` — public files only
   - `4-confidential-data-not-for-publication.zip` — excluded files only
   - `full-replication.zip` — paper + appendix + both zips (for journal submission)

## Notebook Color Convention (in `index.ipynb`)

| Border color | Meaning |
|---|---|
| Blue | Normal step or sub-step |
| Red | Computationally expensive or problematic step |
| Green | Test / robustness check |

## Key Files to Customize per Paper

| File | What to change |
|---|---|
| `replication-package/README.md` | Paper title, authors, data sources table, step-by-step table |
| `replication-package/index.ipynb` | `STATA_location`, `version`, notebook names per step |
| `replication-package/environment.yml` | `name:` field and pinned dependency versions |
| `replication-package/environment-R.yml`, `environment.R` | R env and R packages (written by the skill from the authors' R) |
| `replication-package/create_env.sh` | EDIT HERE block (`ENV_NAME`, `R_ENV_NAME`, cluster modules) |
| `replication-package/setup.do` | `adolist install <name>.pkl` (regenerate `.pkl` from your Stata env) |
| `replication-zip.ipynb` | `df_files.loc[...]` rows to exclude confidential datasets |

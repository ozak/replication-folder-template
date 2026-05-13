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
│   ├── environment.yml   # Conda/Mamba environment (Python 3.11 + base R packages)
│   ├── environment.R     # Additional R packages installed via renv
│   ├── create_env.sh     # One-step environment creation script
│   ├── setup.do          # Stata package installer (run once in Stata)
│   ├── progs/Python/     # Python Jupyter notebooks
│   └── progs/Stata/      # Stata Jupyter notebooks (stata_kernel)
└── replication-zip.ipynb # Creates distributable zip files for submission
```

## Environment Setup

**Recommended (Mamba):**
```bash
cd replication-package
bash create_env.sh
```

`create_env.sh` handles platform differences automatically: on macOS it installs `libblas=*=*accelerate` (Apple Silicon optimization) and brew packages (`fribidi`, `automake`, `autoconf`); on Linux it runs `module load conda/stata` and `apt-get install libfribidi-dev`.

**Manual (Conda):**
```bash
mamba env create -n Awesome-Project -f replication-package/environment.yml
mamba activate Awesome-Project
python -m stata_kernel.install   # finish Stata kernel setup
R -e "IRkernel::installspec()"   # register R kernel
```

**R packages** — `environment.yml` installs base R and a set of `r-*` conda packages. `environment.R` then runs inside that conda environment to set up renv and install additional R packages:
```bash
mamba run -n Awesome-Project R -f replication-package/environment.R
```
This calls `renv::init(bare=TRUE)`, installs packages via `renv::install()`, and snapshots the environment with `renv::snapshot()`. The result is a hybrid: conda manages Python and base R; renv manages the additional R package layer.

**Stata packages** (run once from within Stata):
```stata
do replication-package/setup.do
```
`setup.do` uses the `adolist` package to restore a saved package list from a `.pkl` file. When adapting for a new paper, regenerate the `.pkl` by running `adolist save <name>.pkl` from a configured Stata installation, then update the `adolist install` line in `setup.do`.

## Running the Analysis

All steps are orchestrated from `replication-package/index.ipynb`. Before running:

1. Edit `STATA_location` and `version` in the first code cell to point to your Stata installation (e.g., `/Applications/Stata`, `mp`).
2. Run that cell — it writes `progs/Stata/stata_init.py`, which child Stata notebooks `%run` to configure `stata_setup`. **Individual Stata notebooks will fail if this file doesn't exist.**
3. Launch JupyterLab: `jupyter lab`
4. Open `index.ipynb`, restart kernel, and run all cells.

`index.ipynb` executes child notebooks via shell calls to `jupyter nbconvert` and simultaneously converts them to HTML, displaying each as an inline IFrame. Cells guarded by `should_I_run = False` are skipped by default — set to `True` to enable expensive or conditional steps.

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
  --execute --ExecutePreprocessor.kernel_name=stata \
  --output "NotebookName.ipynb"
```

**Execute a Stata `.do` file and capture log:**
```bash
stata-mp -b do replication-package/progs/Stata/script.do
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
| `replication-package/environment.R` | `renv::install()` calls for paper-specific R packages |
| `replication-package/create_env.sh` | `ENV_NAME` variable |
| `replication-package/setup.do` | `adolist install <name>.pkl` (regenerate `.pkl` from your Stata env) |
| `replication-zip.ipynb` | `df_files.loc[...]` rows to exclude confidential datasets |

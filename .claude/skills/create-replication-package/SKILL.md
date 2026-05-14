---
name: create-replication-package
description: "Creates a complete, journal-ready academic research replication package from an existing working project folder. Uses the standardized template at https://github.com/ozak/replication-folder-template. Invoke this skill whenever the user wants to create a replication package, prepare code and data for journal submission, package their research for sharing, or mentions 'replication package', 'data availability', 'code submission', 'supplementary materials', 'AEA data deposit', or 'RES/AER/QJE replication requirements'. This is a multi-step workflow covering folder structure creation, code migration and Jupyter notebook conversion, LaTeX figure/table naming standardization, and environment configuration. Trigger this skill even when the user only says 'create a replication package for my project'."
---

# Create Replication Package

Transform a working research project folder into a standardized, journal-ready replication package following the template at `https://github.com/ozak/replication-folder-template`.

The goal is reproducibility: a third-party replicator — given only the replication package and access to any needed licensed data — should be able to reproduce all results by running `index.ipynb` top to bottom.

Read `references/template-structure.md` for the canonical directory layout. Read `references/naming-conventions.md` for figure/table naming rules.

## Phase 1: Discover the project

Scan the source project folder **without modifying anything**. Build a complete picture before transforming anything.

**What to find:**
- **LaTeX files** (`.tex`) — find all `.tex` files in the project. There is often both a working-draft version and a submission-ready version. List them and ask the user: *"Which .tex file is the final/submission version you want to use for the replication package? (This is used to extract figure/table numbering and update paths.)"* Working drafts often have 0 `\includegraphics` commands because figures aren't linked yet. Read the confirmed file to extract: title, authors, journal/manuscript ID, and all figure/table references (`\includegraphics`, `\input`, `\label`, `\caption`).
- **Code files** — every `.py`, `.do`, `.R`, `.sh`, `.sbatch`, `.m` file, and existing `.ipynb` notebooks; note which are data creation vs. analysis vs. output generation
- **Data** — `raw-data/` and `data/` directories plus any dataset files (`.dta`, `.csv`, shapefiles, `.pkl`, `.parquet`, `.xlsx`, `.rds`)
- **Output files** — tables (`.tex` output files) and figures (`.pdf`, `.jpg`, `.png`, `.eps`) in `graphs/`, `figures/`, `tables/`, or `output/` directories
- **Conda environment** — ask the user which conda/mamba environment they use for this project (this is the source for the `environment.yml`)
- **Stata installation** — check if Stata is installed: `which stata-mp || which stata-se || which stata || ls /Applications/Stata* 2>/dev/null`
- **Cluster scripts** (`.sh`, `.sbatch`) — flag to keep as-is alongside their parent language

After scanning, confirm with the user:
- Paper title and authors (from LaTeX — ask if not found)
- Manuscript ID (e.g., `MS20230792`) — if unknown, use a descriptive slug (e.g., `income-inequality-growth`)
- Target output folder (suggest a sibling folder named `<ManuscriptID>-replication`)
- Programming languages actually used (Python, Stata, R, Matlab?)
- Which conda environment to export for `environment.yml`
- Which datasets are licensed or confidential (needed for `replication-zip.ipynb` exclusions)

Don't start Phase 2 until the user confirms.

## Phase 2: Scaffold and clean up

Clone the template from GitHub into the target folder:
```bash
git clone https://github.com/ozak/replication-folder-template "<target-folder>"
```

If the target folder already exists or `git clone` fails (e.g., no internet), fall back to copying from a local clone if one exists:
```bash
cp -r "$(find ~ -maxdepth 6 -name replication-folder-template -type d 2>/dev/null | head -1)" "<target-folder>"
```

**Apply author defaults** — the template uses `{{placeholder}}` tokens for author info and compute specs. Fill them in immediately using the bundled script, which auto-detects `.replication_defaults.yml` walking up from the target folder:
```bash
python scripts/apply_defaults.py "<target-folder>"
```
If no defaults file is found, the script prints the unfilled tokens and exits with an error. In that case, ask the user to copy `.replication_defaults.yml.example` to `.replication_defaults.yml` and fill in their details, then re-run. Once applied, every file under the target folder will have real author names, email, compute specs, etc.

**Immediately clean up template artifacts** — these don't belong in a paper-specific package:
```bash
cd "<target-folder>"
rm -f CLAUDE.md replication-folder-template.code-workspace README.md
rm -f replication-package/environment.R   # only if no R code found
rm -rf replication-package/progs/R        # only if no R code found
rm -f setup.do                            # only if no Stata code found
# Remove template placeholder .tex files (will be replaced by real paper source)
rm -f 1-paper/main.tex 2-appendix/appendix.tex
```

**Customize config files:**
- `replication-package/environment.yml`: use the bundled export script which captures top-level packages with their pinned versions, and keeps the pip section only for packages actually installed via pip (not conda duplicates):
  ```bash
  python scripts/export_env.py -n <user-env-name> \
    -o replication-package/environment.yml \
    --slug <paper-slug>
  ```
  This combines `--from-history` (top-level packages only) with the full export (pinned versions) and strips OS-specific build strings and the `prefix:` line. The result is portable across Linux and macOS.
- `replication-package/create_env.sh`: set `ENV_NAME` to match the slug

**Create empty data subdirectories** mirroring the source project's data organization (code will populate them when run).

**Template placeholder notebooks** — The template includes `progs/Python/Renaming.ipynb` and `progs/Python/Copy-Final.ipynb` which ARE useful (they handle the last-mile output renaming and copying to `1-paper/`). Keep them, but read them and customize paths to match this paper's output locations. Remove `progs/Stata/Stata-Notebook.ipynb` (placeholder, not needed once real notebooks are migrated).

## Phase 3: Migrate and convert code

For each code file, migrate to the appropriate location and format. The conversion preserves logic — scripts are wrapped in notebook cells, not rewritten.

**Already `.ipynb`** → copy directly to `progs/Python/`, `progs/Stata/`, or `progs/R/` based on kernelspec

**`.py` files** → convert to Python notebook, save to `progs/Python/`:
```bash
python scripts/convert_to_notebook.py --lang python <source.py> <dest.ipynb>
```

**`.do` files** → convert to Stata notebook, save to `progs/Stata/`:
```bash
python scripts/convert_to_notebook.py --lang stata <source.do> <dest.ipynb>
```

**`.R` files** → convert to R notebook, save to `progs/R/`:
```bash
python scripts/convert_to_notebook.py --lang r <source.R> <dest.ipynb>
```

**`.sh` / `.sbatch` cluster scripts** → copy as-is to the same `progs/` subfolder as their associated notebooks

**Custom utilities** (`.ado`, `.hlp`, `.py` helpers) → copy to the relevant `progs/` subdirectory

**Data files:**
- Raw/input data → `raw-data/<source-subfolder>/`
- Already-processed data to include → `data/<source-subfolder>/`
- Large or licensed datasets: flag but don't copy — handle in Phase 5

## Phase 4: Standardize figure and table names

The convention (see `references/naming-conventions.md` for full rules):
- `Figure-N`, `Figure-N-a`, `Figure-N-b` for main figures and panels (hyphen before panel letter)
- `Table-N` for main tables; `Table-N-PanelA` for multi-panel
- Appendix figures/tables: use the appendix section letter as prefix — `Figure-D-1-a`, `Table-D-1` for Appendix D; `Figure-E-1`, `Table-E-1` for Appendix E; etc.
- If there is only one appendix section, use `Figure-A-N`, `Table-A-N`

### Step 4a: Confirm the final LaTeX file, then parse it

Before running the parser, confirm with the user which `.tex` file to use (you should already have this from Phase 1, but verify). The parser expects a **submission-ready** file with `\includegraphics` and `\input` commands present. If the working draft has no `\includegraphics` entries (figures linked later), use a submission draft instead. Run:
```bash
python scripts/parse_latex.py <main.tex> [<appendix.tex>] \
  --output replication-package/rename_map.json --print
```

Save `rename_map.json` inside `replication-package/` where it stays with the package.

If the LaTeX uses `\input{section-file.tex}` for whole sections, pass those sub-files too, or note them for manual review.

### Step 4b: Confirm with the user

Present the proposed mapping as a table and ask for corrections before touching any files. Common things to check: panel assignments, appendix section letters, any files the parser missed.

### Step 4c: Copy renamed files and update LaTeX paths

1. **Copy** (preserve originals) files to:
   - `replication-package/graphs/paper/Figure-N-a.ext`
   - `replication-package/tables/paper/Table-N.tex`
   - Mirror in `1-paper/graphs/paper/` and `1-paper/tables/paper/` (paper compilation)
   - Appendix files: also copy to `2-appendix/graphs/paper/` and `2-appendix/tables/paper/`
   - Note: all final output files go in `replication-package/graphs/paper/` and `tables/paper/` for the distribution package; `1-paper/` and `2-appendix/` copies are for LaTeX compilation

2. **Update** every `\includegraphics{...}` and `\input{...}` in the `.tex` files to use the new paths relative to the paper directory: `graphs/paper/Figure-1.pdf`, `tables/paper/Table-1.tex`

3. **Copy** the updated `.tex` files to `1-paper/` and `2-appendix/`

## Phase 5: Configure index.ipynb, README, and replication-zip.ipynb

### index.ipynb

Structure it into logical parts reflecting the analysis flow:
- **Part I**: Creating basic data (raw → clean)
- **Parts II–N**: Major analysis sections
- **Last part**: Rename outputs, copy final tables/figures to paper folders

For each notebook, use the standard execution cell pattern from the template.

**Stata configuration** — in the first cell, set `STATA_location` and `version`:
- Auto-detect from Phase 1 discovery results. Common paths: `/Applications/Stata` (macOS), `/usr/local/stata` (Linux). Version from which binary was found (stata-mp → `mp`, stata-se → `se`).
- Set the values directly in `index.ipynb` — do not leave a placeholder. If detection was ambiguous, ask the user once before writing.
- If Stata is not installed, comment out or remove the Stata init cell.

**Customize the execution steps** — the template has placeholder notebook paths like `progs/Python/XXX.ipynb`. Replace every execution cell with the actual notebooks migrated in Phase 3. Each notebook gets its own cell following the template pattern:

```python
import subprocess, os
should_I_run = True
if should_I_run:
    result = subprocess.run(
        ["jupyter", "nbconvert", "progs/Python/Analysis.ipynb",
         "--to", "notebook", "--execute",
         "--ExecutePreprocessor.kernel_name=python3",
         "--ExecutePreprocessor.timeout=3600",
         "--output", "progs/Python/Analysis.ipynb"],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    print(result.stdout[-2000:] if result.stdout else "")
    if result.returncode != 0:
        print(result.stderr[-2000:])
```

Add a markdown cell above each notebook (or group) explaining what that step produces — which tables/figures it generates. Delete template placeholder cells that have no corresponding migrated notebook.

Create a directory-creation cell at the top listing all needed subdirectories.

Color-coded markdown section headers (from the template):
- **Blue**: normal step; **Red**: computationally expensive (note estimated runtime); **Green**: robustness check

### README.md

Don't leave the template README untouched — it still says "AWESOME PAPER" and "TITLE". Customize `replication-package/README.md` with paper-specific content:
- Title, authors, journal, year, DOI/manuscript ID
- Data sources table (one row per dataset in `raw-data/`, with URL, license, availability)
- Step-by-step table (mirrors index.ipynb sections)
- Software requirements (from the exported environment.yml)
- Computational requirements (runtime, memory, cluster if needed)

### replication-zip.ipynb

This creates the distribution zips. Ask the user explicitly: *"Which datasets in `raw-data/` require a license or data use agreement and should be excluded from the public zip?"*

Then open `replication-zip.ipynb` and add exclusion rules in the designated cell — even if the user says "none", add a commented-out example so the pattern is clear for later:

```python
# --- Exclude licensed or confidential datasets ---
# Uncomment and adapt for any dataset that requires a license:
# df_files.loc[df_files['path'].str.contains('raw-data/LicensedDataset'), 'include'] = False

# Example for this paper: all data is public, nothing excluded.
```

If the user names specific datasets, add active (uncommented) rules for each:
```python
df_files.loc[df_files['path'].str.contains('raw-data/IPUMS'), 'include'] = False
df_files.loc[df_files['path'].str.contains('raw-data/Compustat'), 'include'] = False
```

## Completion checklist

- [ ] Template artifacts removed (CLAUDE.md, .code-workspace, placeholder .tex files, Stata-Notebook.ipynb)
- [ ] `environment.yml` exported from user's actual conda env, name set to paper slug
- [ ] `create_env.sh` ENV_NAME updated
- [ ] R components removed if no R code; Stata components removed if no Stata
- [ ] All code files migrated and converted to notebooks
- [ ] `rename_map.json` in `replication-package/` — confirmed with user
- [ ] Figures/tables renamed and copied to `graphs/paper/` and `tables/paper/`
- [ ] LaTeX `.tex` files updated with new paths (in `1-paper/` and `2-appendix/`)
- [ ] `index.ipynb` covers all steps; `STATA_location` set or marked TODO
- [ ] `README.md` has paper-specific content
- [ ] `replication-zip.ipynb` has exclusion rules for licensed/confidential data

Tell the user what still needs manual attention:
- Testing that each notebook actually executes without errors
- Datasets too large to copy or requiring license agreements
- Running `replication-zip.ipynb` when ready to submit

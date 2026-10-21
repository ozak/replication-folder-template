[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14048457.svg)](https://doi.org/10.5281/zenodo.14048457)

# Replication Folder Template

A standardized folder structure, environment setup, and AI-assisted workflow for turning research projects into journal-ready replication packages. It ships with a **Claude skill** (`create-replication-package`) and a **Codex (ChatGPT) agent** that do most of the conversion work: they find the code that actually produces your paper, migrate it into notebooks, standardize figure and table names, rewrite the LaTeX, build `index.ipynb`, the README and the submission zips, and check that every number in your tables is reproduced.

Based on the replication packages for ["Is Secessionism Mostly About Income or Identity? A Global Analysis of 3,153 Subnational Regions"](https://doi.org/10.1093/ej/ueae110) ([Zenodo](https://doi.org/10.5281/zenodo.14048457)) and "Roots of Cultural and Linguistic Traits".

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Repository Layout](#repository-layout)
3. [Use Case 1: Start a New Project from Scratch](#use-case-1-start-a-new-project-from-scratch)
4. [Use Case 2: Convert an Existing Project with the Claude Skill](#use-case-2-convert-an-existing-project-with-the-claude-skill)
5. [Use Case 3: Convert an Existing Project with Codex (ChatGPT)](#use-case-3-convert-an-existing-project-with-codex-chatgpt)
6. [Installing the Skills](#installing-the-skills)
7. [Paper and Author Information](#paper-and-author-information)
8. [Running the Analysis](#running-the-analysis)
9. [Creating the Replication Zip](#creating-the-replication-zip)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

You only install the skill. You do **not** clone this repository or edit any configuration file:
the skill carries its own copy of the template and creates the package folder. Paper and author
information (all co-authors) is read from your paper's LaTeX, completed with web searches, and
confirmed with you; it is stored in the package itself (`replication-info.json`).

1. **Install the skill once** — download [`create-replication-package.skill`](.claude/skills/create-replication-package.skill) and
   - *Claude desktop app / claude.ai:* add it as a custom skill in Claude's skills settings;
   - *Claude Code:* `unzip create-replication-package.skill -d ~/.claude/skills/`;
   - *Codex:* `unzip create-replication-package.skill -d ~/.agents/skills/`.
2. Ask: *"Create a replication package for my paper."*
3. Answer the three opening questions:
   - **Where is the original project folder?** (e.g. `~/Dropbox/Papers/MyProject`)
   - **Do you have a manuscript ID?** (e.g. `MS20230792` — or "not yet")
   - **Where should the replication package go?** Accept the default — `MyProject-shared/<ID>-replication` in your other synced drive (e.g. Google Drive) at the same relative path — or give another location.
4. Confirm the authors the skill found (names, order, affiliations, e-mails, ORCIDs, websites) and say which computer ran the analysis.
5. Confirm the decisions at each checkpoint (final `.tex`, figure/table names, migration plan, licensed data).
6. When it finishes: create the environment, run `index.ipynb`, check the table comparison, run `replication-zip.ipynb`, upload the zips.

**Starting a new paper?** Ask *"Set up a new paper project with the replication template"* — the skill creates the folder structure for you (see [Use Case 1](#use-case-1-start-a-new-project-from-scratch)).

---

## Repository Layout

```
replication-folder-template/
├── 1-paper/                  # LaTeX source for the main paper
├── 2-appendix/               # LaTeX source for the appendix
├── replication-package/      # Self-contained, submittable replication package
│   ├── index.ipynb           # Master notebook — runs the full analysis
│   ├── README.md             # Social Science Data Editors README template
│   ├── environment.yml       # Minimal Python environment (what the code imports; no R)
│   ├── environment-R.yml     # Separate R environment (only if R is used)
│   ├── environment.R         # R packages at the authors' versions, checked
│   ├── create_env.sh         # Creates the environments and kernels (unattended; EDIT HERE block)
│   ├── setup.do              # Stata package installer
│   ├── progs/Python/         # Python notebooks (incl. Renaming.ipynb, Copy-Final.ipynb) + run_notebooks.py (runner)
│   ├── progs/Stata/          # Stata notebooks (pystata: python3 kernel + %%stata)
│   └── progs/R/              # R notebooks (IRkernel)
├── replication-zip.ipynb     # Creates distributable zips for journal submission
├── .claude/skills/           # Claude skill (instructions, scripts, bundled template copy) + packaged .skill file
├── .agents/skills/           # Codex / ChatGPT agent (create-replication-package)
```

---

## Use Case 1: Start a New Project from Scratch

Use the template as your project folder **from day one** so you are always ready to produce a replication package.

### Step 1 — Create the folder

Ask the skill: *"Set up a new paper project with the replication template."* It asks where the folder should go, the project name, the working title and the co-authors' names; looks up each author's affiliation, e-mail, website and ORCID on the web; asks you to confirm them; and creates the structure (no cloning).

*Without the skill:* `git clone https://github.com/ozak/replication-folder-template my-paper`, delete `.git`, `.claude/`, `.agents/`, `CLAUDE.md`, and replace the `{{title}}`, `{{authors_...}}` placeholders yourself.

### Step 2 — Set up the environment

```bash
cd replication-package
bash create_env.sh
```

This creates a Mamba/Conda environment with Python 3.11, Jupyter, pystata support, R and IRkernel. On macOS it applies Apple Silicon optimizations automatically.

### Step 3 — Work inside the structure

- Python notebooks in `replication-package/progs/Python/`, Stata in `progs/Stata/` (pystata notebooks: first cell `import stata_init`, then `%%stata` cells), R in `progs/R/`
- Raw/input data in `replication-package/raw-data/<Source>/` (one folder per provider); data created by code in `data/<Step>/`
- All paths relative to the notebook's folder: `../../raw-data/...`, `../../data/...`
- LaTeX in `1-paper/` and `2-appendix/`; final figures/tables in `replication-package/graphs|tables/(paper|appendix)/`, copied into flat `graphs/` and `tables/` folders next to each `.tex`, named `Figure-1-a`, `Table-D3`, … (see the naming rules in `.claude/skills/create-replication-package/references/naming-conventions.md`)
- In the paper, keep each table's caption, column headers and notes in the `.tex` and `\input` only the body produced by the code

### Step 4 — Orchestrate from `index.ipynb`

Add one step per notebook to `replication-package/index.ipynb` (the template shows the pattern). Header colors:

| Color | Meaning |
|---|---|
| Blue | Normal step |
| Red | Computationally expensive (guarded with `should_I_run = False`) |
| Green | Test / robustness check |

When you're ready to submit, run `replication-zip.ipynb`. You can also run the skill on the project at any time to check and finish it.

---

## Use Case 2: Convert an Existing Project with the Claude Skill

The **`create-replication-package`** skill turns a working (usually messy) research folder into a journal-ready package. It works in **Claude Code** (terminal) and in **Claude's desktop app (Cowork)** with your folders connected.

### What to have ready

- The original project folder (code, data, paper sources). Co-author copies, external data drives or a journal-submission folder can be added as extra sources.
- The final version of the paper's LaTeX (the skill shows the candidates it finds and asks which one is final).
- Your manuscript ID, if you have one.
- Nothing about your software setup: the skill finds the conda/mamba environment, R, Stata and Julia setup your code used and asks you to confirm.
- Which datasets are licensed or confidential.
- Nothing to install or configure beyond the skill itself: the template comes with the skill, and the authors are taken from your paper (and the web) and confirmed with you.

### Start it

**Claude Code:**
```bash
cd /path/to/your/research/project
claude
```
then type `/create-replication-package`, or just *"Create a replication package for my paper"*.

**Claude desktop app (Cowork):** connect the original folder (and the destination's parent folder, e.g. your Google Drive) and ask *"Create a replication package for my paper"*. The skill asks for access to exactly the folders it needs.

### What it asks first

1. **Where is the original project folder?** (plus any other folders with material for this paper)
2. **Do you have a manuscript ID?** (if not, it uses the project name and later looks for an ID in file names such as editor letters)
3. **Where should the replication package go?** The default follows this layout:

```
<synced drive A, e.g. Dropbox>/<path>/<Project>/                          original — never modified
<synced drive B, e.g. Google Drive>/<path>/<Project>-shared/               shared with co-authors
<synced drive B, e.g. Google Drive>/<path>/<Project>-shared/<ID>-replication/   ← the package
```

You can choose "next to the original" or any other path. The skill refuses destinations inside the original folder and never writes into a non-empty folder.

### What it does

| Phase | What happens | Your checkpoint |
|---|---|---|
| **0 — Locations** | The three questions above; validates the destination | — |
| **1 — Discover** | Surveys the project (and extra sources): candidate `.tex` versions, code by language, data sizes, absolute paths, earlier replication attempts, online-only cloud files (downloaded automatically). Extracts title and **all authors** from the final `.tex` and completes missing affiliations, e-mails, ORCIDs and websites by web search. Detects the **software environment** used: kernelspecs and `mamba activate` lines in the code, environment/requirements/renv files, and the environments on your machine ranked by how many of the code's imports they provide | Final `.tex`; **the author list and details**; **which mamba/conda environment (and R/Stata/Julia setup) was used**; journal, licensed data, slow/cluster steps |
| **2 — Map & trace** | Names every figure and table as LaTeX prints them; finds the files behind tables pasted into the `.tex`; traces each output back to the code and raw data that produce it, so only what the paper needs is migrated | Rename map and migration plan |
| **3 — Scaffold** | Creates the package from the template bundled with the skill, stores the confirmed paper/author info in `replication-info.json` and fills the README, notebooks and paper templates from it. Builds a **minimal** `environment.yml` **from the environment you used** (only what the code imports; result-computing packages pinned exactly, system libraries left free), a separate R environment with `environment.R` (your installed versions, core packages last, checked), and `setup.do` installing each Stata package from the source you installed it from; checks that the environments resolve on Linux and macOS without installing anything | Packages the code imports but your environment lacks; computer used |
| **4 — Migrate** | Copies raw data into `raw-data/<Source>/`; converts each script to a notebook (same code, same order; Stata via pystata); makes every path relative | — |
| **5 — Names & LaTeX** | Writes `1-paper/` and `2-appendix/` `.tex` files pointing at the standardized outputs; builds `Renaming.ipynb`; compares tables | Any table whose numbers differ |
| **6 — index.ipynb** | One step per notebook in dependency order, run by `run_notebooks.py` (saves failed notebooks, Stata licence limit, retries when Stata cannot start, dependencies, optional parallel mode); slow steps guarded, with cluster/local options and tests against shipped data | — |
| **7 — README & zips** | Fills the Data Editors README; sets zip exclusions for licensed data *and the files derived from it* | Exclusion list |
| **8 — Verify** | Static package check, environment check, table comparison, run-twice checks for nondeterministic steps, consistency checks for errors in the original | Final report; decisions that change results |
| **9 — Clean-up** (optional) | Removes code and loop iterations that produce nothing used; verifies used outputs are identical | What to remove |

### Principles it follows

- **Your original folders are never modified.** Nothing is created, edited, moved or deleted there; code is never run in place. The bundled scripts refuse to write anywhere except the destination.
- **Only the code the paper needs.** Source folders often mix papers, versions and experiments; the skill traces from the final figures and tables back to code and data.
- **Code stays as close to the original as possible.** One script becomes one notebook with the same code; only paths, plumbing and output file names change (every change is logged). Code is consolidated only if you ask.
- **Numbers from the code, presentation from the final paper.** Each table's caption, column headers and notes stay in the paper's `.tex` exactly as in your final version; the code produces only the body, which the paper `\input`s. This applies both to tables pasted into the `.tex` and to hand-edited table files the paper included — their header/footer are moved into the paper. Rows you removed or labels you edited in the paper are reapplied, and a comparison checks that every printed number is reproduced.
- **Online-only Dropbox/Google Drive files** are downloaded as needed; you don't have to do anything.
- **Nothing is installed without asking.**

### What you get

```
<ID>-replication/
├── _migration/            # how the package was built: inventory, rename map, lineage report,
│                          #   plan, migration log, original table bodies (not zipped)
├── 1-paper/               # <ID>-main-<date>.tex + graphs/ tables/ it references
├── 2-appendix/            # <ID>-appendix-<date>.tex + graphs/ tables/
├── replication-package/   # index.ipynb, README.md, environment, progs/, raw-data/, data/, outputs
└── replication-zip.ipynb
```

### After the skill finishes

1. `cd replication-package && bash create_env.sh` (once).
2. In Stata: `do setup.do` (once).
3. Open `index.ipynb`, set `STATA_location`/`version` in the first cell, restart and run all (slow steps stay off unless you switch them on).
4. Check tables: ask the skill to *"compare the tables"* (it runs `compare_tables.py`) — all tables should show ✅.
5. Compile `1-paper/` and `2-appendix/` and compare with your submitted PDF.
6. Run `replication-zip.ipynb`, then upload `3-replication-package.zip` (public) to Zenodo / the journal's repository and send `4-confidential-data-not-for-publication.zip` to the data editor if required.

---

## Use Case 3: Convert an Existing Project with Codex (ChatGPT)

The same workflow is available in **Codex** via the `.agents/` copy of the skill (identical instructions and scripts).

1. Install the skill (see below) — no need to clone this repo.
2. Say: `Use $create-replication-package to turn this research project into a journal-ready replication package.` — or describe the goal; `allow_implicit_invocation: true` lets it trigger on natural requests.
3. Answer the same three opening questions and checkpoints as above.

---

## Installing the Skills

The packaged skill [`.claude/skills/create-replication-package.skill`](.claude/skills/create-replication-package.skill) is a zip of the skill folder, which contains the instructions, the helper scripts and a bundled copy of this template (`assets/template/`). That single file is all a user needs.

| Where | How |
|---|---|
| Claude desktop app / claude.ai | Add `create-replication-package.skill` as a custom skill in Claude's skills settings |
| Claude Code (any project) | `unzip create-replication-package.skill -d ~/.claude/skills/` — check with `/skills` |
| Claude Code (inside this repo) | Nothing: `.claude/skills/` is picked up automatically |
| Codex | `unzip create-replication-package.skill -d ~/.agents/skills/` (the repo's `.agents/` copy also includes `agents/openai.yaml`) |

To follow the repository instead of a downloaded copy, symlink the folder:
```bash
ln -s "/path/to/replication-folder-template/.claude/skills/create-replication-package" ~/.claude/skills/
```

**Requirements:** Python ≥ 3.9 (the scripts use only the standard library). Running a finished package needs Mamba/Conda, Jupyter, and Stata/R if the paper uses them.

**For template maintainers:** after editing `1-paper/`, `2-appendix/`, `replication-package/` or `replication-zip.ipynb`, refresh the copy bundled with the skill and rebuild the `.skill` file:
```bash
python3 .claude/skills/create-replication-package/scripts/sync_template.py
python3 .agents/skills/create-replication-package/scripts/sync_template.py
(cd .claude/skills && rm -f create-replication-package.skill && zip -r create-replication-package.skill create-replication-package -x '*.DS_Store' '*__pycache__*')
```

---

## Paper and Author Information

There is no personal profile to set up: papers have different co-authors, so the information belongs to each package. The skill builds `replication-info.json` in the replication folder:

1. **Extract** the title and every author (with affiliation, e-mail and ORCID where printed) from the final `.tex` — `\author`/`\and`, `\thanks`, `\footnote`, `authblk`'s `\affil` are all handled.
2. **Complete** missing affiliations, websites, ORCIDs and e-mails with web searches (faculty pages, ORCID, RePEc/IDEAS), recording each source.
3. **Confirm** with you: the skill shows the list and only uses it once you confirm that these are the authors, in this order, with these details.

For a **new project**, it asks for the working title and your co-authors' names, then does steps 2–3.

The README (title block, contributors, suggested citation, computational requirements), `index.ipynb` and the paper/appendix templates are filled from this file. To change something later, ask the skill (it edits the file with `project_info.py set`, asks you to confirm, and refills the templates).

---

## Running the Analysis

From `replication-package/index.ipynb`:

1. Edit the first cell: `STATA_location` (e.g. `/Applications/Stata`) and `version` (e.g. `mp`).
2. Run it — it writes `progs/Stata/stata_init.py`, which every Stata notebook imports.
3. Launch JupyterLab in the environment:
   ```bash
   mamba activate <env-name>
   jupyter lab
   ```
4. Open `index.ipynb`, restart the kernel, run all cells. Each step executes a notebook with the runner and shows its HTML output (set `PARALLEL = True` in the runner cell to run independent notebooks at once).

**Run a single notebook (Python or Stata/pystata):**
```bash
cd replication-package/progs/Python      # or progs/Stata
jupyter nbconvert "Analysis.ipynb" --to notebook \
  --ExecutePreprocessor.kernel_name=python3 --execute --output "Analysis.ipynb"
```
or, with the runner (saves the notebook and its HTML even when it fails), from `replication-package/`:
```bash
python progs/Python/run_notebooks.py progs/Python/A.ipynb progs/Stata/B.ipynb:after=A --parallel 2
```

---

## Creating the Replication Zip

Run `replication-zip.ipynb` from the folder that contains `replication-package/`. It produces:

- `3-replication-package.zip` — public files only
- `4-confidential-data-not-for-publication.zip` — the excluded (licensed/confidential) files
- `full-replication.zip` — both zips plus the journal checklist, for the editor

Exclusions go in the designated cells, one per licensed source **and its derived data**:
```python
df_files.loc[df_files['file_path'].str.contains('raw-data/LicensedSource'), 'include'] = False
df_files.loc[df_files['file_path'].str.contains('data/DerivedFromLicensedSource'), 'include'] = False
```
The notebook also writes `directory_structure.{txt,html,md}` (shown in the README's file list).

---

## Troubleshooting

| Problem | What to do |
|---|---|
| "Resource deadlock avoided" when reading Dropbox/Google Drive files | Those are online-only files. The skill downloads them through the host automatically; on your own Mac, opening them downloads them. |
| A table shows ❌ in `compare_tables.py` | The code does not reproduce the printed numbers: check the script version, data vintage, sample or seed — never edit the numbers. Suggested `drop_rows` / `replace` fixes are only for presentation differences. |
| `REFUSED: … read-only source folder` | Working as intended — a script tried to write into an original folder. Write to the replication folder instead. |
| A Stata notebook fails with `No module named stata_init` | Run the first cell of `index.ipynb` (it writes `progs/Stata/stata_init.py`). |
| Figure/table missing when compiling `1-paper/` | Run `Renaming.ipynb` then `Copy-Final.ipynb` (or the last part of `index.ipynb`). |

---

## Copyright

&copy; Ömer Özak (2024)

This code and data is provided under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License](https://creativecommons.org/licenses/by-sa/4.0/) and [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html).

![CC BY-SA](http://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg) ![GPLv3](https://www.gnu.org/graphics/gplv3-127x51.png)

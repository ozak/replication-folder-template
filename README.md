[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14048457.svg)](https://doi.org/10.5281/zenodo.14048457)

# Replication Folder Template

A standardized folder structure, environment setup, and AI-assisted workflow for turning research projects into journal-ready replication packages. It ships with a **Claude Code skill** and a **Codex (ChatGPT) agent** that automate most of the conversion work.

Based on the [replication package](https://doi.org/10.5281/zenodo.14048457) for ["Is Secessionism Mostly About Income or Identity? A Global Analysis of 3,153 Subnational Regions"](https://doi.org/10.1093/ej/ueae110).

---

## Table of Contents

1. [Repository Layout](#repository-layout)
2. [Use Case 1: Start a New Project from Scratch](#use-case-1-start-a-new-project-from-scratch)
3. [Use Case 2: Convert an Existing Project with Claude Code](#use-case-2-convert-an-existing-project-with-claude-code)
4. [Use Case 3: Convert an Existing Project with Codex (ChatGPT)](#use-case-3-convert-an-existing-project-with-codex-chatgpt)
5. [Installing the Skills](#installing-the-skills)
6. [Setting Up Author Defaults](#setting-up-author-defaults)
7. [Running the Analysis](#running-the-analysis)
8. [Creating the Replication Zip](#creating-the-replication-zip)

---

## Repository Layout

```
replication-folder-template/
├── 1-paper/                  # LaTeX source for the main paper
├── 2-appendix/               # LaTeX source for the appendix
├── replication-package/      # Self-contained, submittable replication package
│   ├── index.ipynb           # Master notebook — runs the full analysis
│   ├── environment.yml       # Conda/Mamba environment (Python 3.11 + base R)
│   ├── environment.R         # Additional R packages via renv
│   ├── create_env.sh         # One-step environment creation script
│   ├── setup.do              # Stata package installer
│   ├── progs/Python/         # Python Jupyter notebooks
│   ├── progs/Stata/          # Stata Jupyter notebooks (stata_kernel)
│   └── progs/R/              # R Jupyter notebooks (IRkernel)
├── replication-zip.ipynb     # Creates distributable zips for journal submission
├── .claude/skills/           # Claude Code skill (create-replication-package)
├── .agents/skills/           # Codex / ChatGPT agent (create-replication-package)
└── .replication_defaults.yml.example  # Author info template
```

---

## Use Case 1: Start a New Project from Scratch

Use this repo as your project folder **from day one** so everything stays organized and you're always ready to generate a replication package.

### Step 1 — Clone the repo

```bash
git clone https://github.com/ozak/replication-folder-template my-paper
cd my-paper
```

### Step 2 — Set up author defaults (once, globally)

Copy the example file and fill in your details:

```bash
cp .replication_defaults.yml.example .replication_defaults.yml
# Then edit .replication_defaults.yml with your name, email, ORCID, affiliation, etc.
```

`.replication_defaults.yml` is gitignored. The skill walks up the directory tree to find it, so placing it here makes it available to all projects nested inside this folder.

### Step 3 — Set up the environment

```bash
cd replication-package
bash create_env.sh
```

This creates a Mamba/Conda environment with Python 3.11, Jupyter, Stata kernel, R, and IRkernel. On macOS it applies Apple Silicon optimizations automatically.

### Step 4 — Write your code

- Put Python analysis notebooks in `replication-package/progs/Python/`
- Put Stata `.do` files / notebooks in `replication-package/progs/Stata/`
- Put R scripts / notebooks in `replication-package/progs/R/`
- Raw/input data goes in `replication-package/raw-data/<source>/`
- LaTeX source goes in `1-paper/` and `2-appendix/`

### Step 5 — Orchestrate from `index.ipynb`

Open `replication-package/index.ipynb`. For each analysis step, add a cell that calls `jupyter nbconvert --execute` on the corresponding notebook. The template includes color-coded section headers:

| Color | Meaning |
|---|---|
| Blue | Normal step |
| Red | Computationally expensive |
| Green | Robustness check / test |

When you're ready to submit, run `replication-zip.ipynb` from the repo root to create the submission zips.

---

## Use Case 2: Convert an Existing Project with Claude Code

If you already have a working research project and want to convert it into a journal-ready replication package, the **`create-replication-package`** Claude Code skill automates the entire process.

### Prerequisites

- [Claude Code](https://claude.ai/code) installed (`npm install -g @anthropic-ai/claude-code`)
- This repo cloned somewhere on your machine (or internet access so the skill can clone it)

### Install the skill

See [Installing the Skills](#installing-the-skills) below.

### Run the skill

Open Claude Code **from your existing project folder** (or any folder):

```bash
cd /path/to/your/existing/research/project
claude
```

Then type:

```
/create-replication-package
```

Or describe what you want in plain English — the skill triggers automatically on phrases like:

> *"Create a replication package for my paper"*
> *"Prepare my code for AEA/QJE submission"*
> *"Package my research for journal replication requirements"*

### What the skill does

The skill runs a guided, multi-phase workflow:

| Phase | What happens |
|---|---|
| **1 — Discover** | Scans your project: finds `.tex`, `.py`, `.do`, `.R` files, data directories, conda environment |
| **2 — Scaffold** | Clones this template into a new `<ManuscriptID>-replication/` folder, applies your author defaults, removes template placeholders |
| **3 — Migrate code** | Converts `.py`/`.do`/`.R` scripts to Jupyter notebooks; copies existing notebooks; preserves cluster scripts |
| **4 — Rename outputs** | Parses your LaTeX to extract figure/table numbering, renames files to `Figure-N.pdf` / `Table-N.tex` convention, updates LaTeX `\includegraphics` paths |
| **5 — Configure** | Builds `index.ipynb`, customizes `README.md`, sets up `replication-zip.ipynb` exclusions for licensed data |

The skill asks for confirmation at key decision points (LaTeX file to use, manuscript ID, conda environment, licensed datasets) before making changes.

### Notebook conversion example

A script like `analysis.py` becomes `progs/Python/Analysis.ipynb` with each logical block in its own cell. A `regression.do` becomes `progs/Stata/Regression.ipynb` with the Stata kernel.

---

## Use Case 3: Convert an Existing Project with Codex (ChatGPT)

The same workflow is available in **Codex** (ChatGPT with code execution) via the `.agents/` skill.

### Prerequisites

- Access to [ChatGPT with Codex](https://chatgpt.com) (requires a plan with code execution)
- This repo available to your Codex environment (cloned or uploaded)

### Install the agent

See [Installing the Skills](#installing-the-skills) below.

### Run the agent

In a Codex session, use the agent trigger phrase:

```
Use $create-replication-package to turn this research project into a journal-ready replication package.
```

Or describe your goal — the agent's `allow_implicit_invocation: true` setting means it activates on natural language requests about replication packages.

The agent follows the same five-phase workflow as the Claude Code skill and produces the same folder structure and output.

---

## Installing the Skills

### Claude Code skill

The skill lives in `.claude/skills/create-replication-package/`. To make it available in Claude Code:

**Option A — Project-local (only available in this repo):**
The skill is already present in `.claude/skills/` — Claude Code picks it up automatically when you open this folder.

**Option B — Global install (available in any project):**
Copy the skill folder to your global Claude skills directory:

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/create-replication-package ~/.claude/skills/
```

You can then run `/create-replication-package` from **any** project folder in Claude Code.

**Option C — Symlink (stays in sync with this repo):**
```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/.claude/skills/create-replication-package" ~/.claude/skills/create-replication-package
```

After installing, verify with `/skills` in Claude Code — `create-replication-package` should appear in the list.

### Codex agent

The Codex agent configuration lives in `.agents/skills/create-replication-package/agents/openai.yaml`.

**Install:**
```bash
mkdir -p ~/.agents/skills
cp -r .agents/skills/create-replication-package ~/.agents/skills/
```

Or configure it directly in your Codex environment by uploading the `.agents/` folder contents.

---

## Setting Up Author Defaults

The skill auto-fills your name, email, ORCID, affiliation, and compute specs into every new replication package. Set this up once by copying the example file and editing it in place:

```bash
cp .replication_defaults.yml.example .replication_defaults.yml
```

Edit `.replication_defaults.yml`:

```yaml
author_name: "Jane Smith"
author_last_name: "Smith"
author_website: "https://janesmith.com"
author_email: "jsmith@university.edu"
author_orcid: "0000-0000-0000-0000"
author_affiliation: "Department of Economics, University of Somewhere"
author_affiliation_short: "UoS"
author_grants: "Funded by NSF Grant #XXX"

laptop_specs: "MacBook Pro M3, 36 GB RAM, macOS 15"
laptop_memory: "36 GB RAM"
cluster_specs: "University HPC cluster using the `normal` queue (32-core nodes, 256 GB RAM)"
compute_hours: "48 computing hours (~2 actual days)"

institution_logo_url: "https://university.edu/logo.png"
institution_logo_width: "200"
institution_logo_link: "https://university.edu"
```

The skill walks up the directory tree to find this file, so it works from any subfolder of your project.

---

## Running the Analysis

Configure and run from `replication-package/index.ipynb`:

1. Edit the first cell: set `STATA_location` (e.g., `/Applications/Stata`) and `version` (e.g., `mp`).
2. Run that cell — it writes `progs/Stata/stata_init.py` for child Stata notebooks.
3. Launch JupyterLab:
   ```bash
   mamba activate <env-name>
   jupyter lab
   ```
4. Open `index.ipynb`, restart the kernel, and run all cells.

**Run a single notebook from the command line:**
```bash
cd replication-package/progs/Python
jupyter nbconvert "Analysis.ipynb" --to notebook \
  --ExecutePreprocessor.kernel_name=python3 --execute \
  --output "Analysis.ipynb"
```

---

## Creating the Replication Zip

Run `replication-zip.ipynb` from the repo root. It produces:

- `3-replication-package.zip` — public files only (excludes licensed/confidential data)
- `4-confidential-data-not-for-publication.zip` — excluded files
- `full-replication.zip` — paper + appendix + both zips (for journal submission)

Mark datasets to exclude in the designated cell:
```python
df_files.loc[df_files['path'].str.contains('raw-data/IPUMS'), 'include'] = False
```

---

## Copyright

&copy; Ömer Özak (2024)

This code and data is provided under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License](https://creativecommons.org/licenses/by-sa/4.0/) and [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html).

![CC BY-SA](http://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg) ![GPLv3](https://www.gnu.org/graphics/gplv3-127x51.png)

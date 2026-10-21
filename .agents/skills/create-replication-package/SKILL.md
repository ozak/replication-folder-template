---
name: create-replication-package
description: "Creates a journal-ready replication package from an existing (often messy) research project folder, using the template at https://github.com/ozak/replication-folder-template. Use when the user wants to create a replication package, prepare code and data for a journal or data editor, package research for Zenodo, or mentions 'replication package', 'data availability', 'code submission', 'AEA data deposit' or journal replication requirements, even if they only say 'create a replication package for my paper'. Always starts by asking where the original folder is, the manuscript ID and where the package should go, before reading any files. Covers tracing the final paper's tables and figures to code and data, migrating code to notebooks (Python, Stata via pystata, R), naming, LaTeX, index.ipynb, README, zips and verification."
---

# Create Replication Package

Turn a working research folder into a package in which a third party — given only the package
and access to any licensed data — reproduces every number, table and figure by running
`replication-package/index.ipynb` top to bottom.

`SKILL_DIR` below means the folder containing this file. All scripts are standard-library Python
(3.9+): run them as `python3 SKILL_DIR/scripts/<script>.py …`.

> **FIRST ACTION — before any other tool call.** Do not list, read, search or run anything yet
> (not even this skill's references or the current folder). Your first action is to ask the three
> Phase 0 questions in one batch (AskUserQuestion where available, otherwise a short plain-text
> message), then wait for the answers:
> 1. **Where is the original project folder?** If the session was started inside a folder, offer
>    the current working directory as the first (recommended) option — but still ask.
> 2. **Do you have a manuscript ID?** (e.g. `MS20230792`; "not yet" is fine.) Option buttons cannot
>    take typed input, so make the typing path explicit: options *"Not yet — look for it in the
>    files"* and *"Yes — type it in 'Other'"*, and say in the question text *"type the ID in
>    Other"*. Same for any option that needs a path or name: label it *"… (type it in Other)"*.
> 3. **Where should the replication package go?** Default: `<Project>-shared/<ID>-replication` in
>    the user's other synced drive, mirroring the original's path (see Phase 0).
>
> Skip only a question the user's request already answers explicitly. Exploration (Phase 1)
> starts after the answers, and only inside the folders the user named.
> If the user cancels or dismisses the question form, do not proceed and do not assume defaults:
> ask the same three questions again in plain text (numbered, with the defaults shown), and
> accept short free-form answers such as "current folder, MS12345, Google Drive".

After Phase 0, read `references/lessons-from-examples.md` (what two real conversions needed).
Read when you reach the phase: `references/naming-conventions.md` (Phase 2),
`references/template-structure.md` (Phase 3), `references/index-patterns.md` (Phase 6),
`references/readme-guide.md` (Phase 7).

## Two ways the skill is used

* **Convert an existing project** (most requests): follow Phases 0–8 below.
* **Start a new project with the template** ("set up a new paper folder", "start a project with the
  replication template"): ask where the project folder should go, its name/slug, the working
  title and the **co-authors' names**; fill each author's affiliation, e-mail, website and ORCID
  with web searches (`project_info.py set`), show the table and get the user's confirmation
  (`project_info.py confirm`), then run `scaffold.py --info …` (keep the placeholder `.tex` files),
  then explain the conventions in two lines: code in `progs/<Lang>/` with `../../` paths, raw data in
  `raw-data/<Source>/`, one `index.ipynb` step per notebook, tables' head/foot in the `.tex` with
  only bodies `\input` from the code. Running the skill on that folder later completes the package.

## Ground rules

1. **The source folders are read-only — absolutely.** Never edit, move, rename, delete or create
   anything in them (or in earlier replication attempts inside them): no output files, no notebooks
   executed in place, no `git` commands, no `__pycache__` (run Python with `-B` or
   `PYTHONDONTWRITEBYTECODE=1`). Never run the original code inside the source — it writes outputs;
   code runs only in the target. All writes go to the target folder. Every bundled script refuses
   to write inside `--project-root`/`--extra-root` and inside the folders listed in
   `REPLICATION_READONLY`; set it at the start of every shell call:
   `export REPLICATION_READONLY="<originals>:<shared>" REPLICATION_TARGET="<target>" PYTHONDONTWRITEBYTECODE=1`
   (printed by the Phase 0 check).
   Reading cloud files (which may download them, see below) does not change them.
2. **Include only what the paper needs.** Source folders mix papers, versions and experiments.
   Trace from the final paper's figures and tables back to code and data; migrate that.
3. **Preserve the code.** By default each original script becomes one notebook with the same code in
   the same order (split into cells). Change only paths, plumbing and output file names — never
   estimation logic, samples or numbers. Consolidating or reorganizing code happens only if the user
   asks for it. Log every edit in `_migration/migration-log.md` (file, change, why).
4. **Numbers from the code, presentation from the final paper.** Tables are reproduced as the paper
   prints them: the final `.tex` keeps each table's head (caption, label, column headers) and foot
   (`\bottomrule`, notes) verbatim, and `\input`s only the **body** generated by the package. This
   holds whether the paper pasted the table or `\input`/`\include`d a complete, hand-edited table
   file: in the latter case the file's head and foot are moved into the paper. Row
   labels edited or rows dropped in the paper after the code ran are reapplied in `Renaming.ipynb`
   (`replace=`, `drop_rows=`), and `compare_tables.py` proves every printed number is reproduced.
5. **Stop at the ★ checkpoints** and get the user's confirmation; batch questions with the
   AskUserQuestion tool where available.
6. **Ask before installing anything** (pip/conda/brew/Stata packages), even in a sandbox.
7. Keep working files in `<target>/_migration/` (inventory, rename map, lineage, plan, log).
8. **No spaces in names.** Every folder and file created for the package — the shared folder, the
   target, notebooks, data, outputs — replaces whitespace with `-` (runs collapse to one):
   `The Millennia of China` → `The-Millennia-of-China-shared/`, `clean data.do` →
   `clean-data.ipynb`, `raw-data/World Bank/GDP data.csv` → `raw-data/World-Bank/GDP-data.csv`.
   The originals keep their names (read-only); record each rename in the rename map and update
   every reference to it (code paths, `.tex`, `index.ipynb`). Existing path components outside the
   package (e.g. `My Drive`) stay as they are. `check_package.py` fails on any name with spaces.
   They document the migration and are not part of the zipped package.

| Script | Phase | Purpose |
|---|---|---|
| `inventory.py` | 1 | read-only survey: candidate .tex files, code by language, data sizes, cloud-only files, absolute paths, earlier attempts |
| `parse_latex.py` | 2 | final .tex → `rename_map.json` (standard names for every figure/table, sources on disk) |
| `match_inline_tables.py` | 2 | find the generated file behind tables pasted into the .tex |
| `trace_outputs.py` | 2 | outputs → producing scripts → upstream scripts → raw inputs (`lineage.md`) |
| `_safety.py` | 0 | suggest/validate the package location; read-only guard used by all scripts |
| `project_info.py` | 1, 3 | paper title + **all authors** (affiliation, email, ORCID, website) extracted from the final `.tex`, completed by web search, confirmed by the user; stored in `<target>/replication-info.json` |
| `scaffold.py` | 3 | create the package from the template bundled in `assets/template/` (no clone needed) |
| `apply_defaults.py` | 3 | fill the template tokens (title, authors, citation, compute specs) from `replication-info.json` (called by `scaffold.py`) |
| `detect_envs.py` | 1, 3 | which conda/mamba env (and R, Stata, Julia setup) the project used: evidence in the code + envs on the machine ranked by how many imports they provide; writes `environment.R` and `setup.do` from the authors' installed packages |
| `export_env.py` | 3 | portable `environment.yml` from the chosen env (by name, or by reading the env folder directly) |
| `convert_to_notebook.py` | 4 | `.py/.ipy/.do/.R` → notebook (Stata = pystata) |
| `audit_paths.py` | 4 | find / rewrite absolute paths, `cd`, old relative layouts |
| `build_renaming_notebook.py` | 5 | `rename_map.json` → `progs/Python/Renaming.ipynb` |
| `rewrite_tex_paths.py` | 5 | copy of the .tex pointing to `graphs|tables/(paper|appendix)/…`; pasted table bodies → `\input` (head/foot kept) |
| `compare_tables.py` | 5, 8 | every number printed in the paper's tables vs. the regenerated bodies; suggests `replace`/`drop_rows` |
| `check_package.py` | 8 | static verification of the finished package |

---

## Phase 0 — Locations (ask first, before reading anything)

**Default layout to propose** (the author's convention):

```
<synced drive A>/<path>/<Project>/                         original working folder (e.g. Dropbox) — read-only
<synced drive B>/<path>/<Project>-shared/                  shared folder (e.g. Google Drive, shared with co-authors)
<synced drive B>/<path>/<Project>-shared/<ManuscriptID>-replication/   ← the replication package
```

The shared folder mirrors the original's relative path in a *different* synced drive and holds
everything produced for sharing and submission (the replication package, zips, submitted PDFs).
Use `<Project>-replication` until the manuscript ID is known. `<Project>` is the original folder's
name with spaces replaced by `-` (`The Millennia of China` → `The-Millennia-of-China-shared`);
`_safety.py --suggest` does this. If a `-shared` folder with the spaced name already exists, ask
whether to use it or create the hyphenated one.

1. **First thing the skill does** — before reading any file, ask these three questions in one batch
   (AskUserQuestion where available; skip any the request already answers explicitly — "my paper"
   or being started inside a folder is *not* an answer: offer the current folder as the default):
   1. **Where is the original project folder?** (default: the current working directory; plus, optionally, other folders with code, data or
      paper versions for this paper — external data drives, an Overleaf/journal-submission folder,
      earlier shared copies). All read-only.
   2. **Do you have a manuscript ID?** (e.g. `MS20230792`; the "Yes" option must say *type it in
      'Other'*, since option buttons cannot take input). If not, use `<Project>` for now; Phase 1
      looks for one in file names such as editor letters and offers it.
   3. **Where should the replication package go?** Offer: *"Default: `<Project>-shared/<ID>-replication`
      in your other synced drive, mirroring the original's path"* (recommended) · *"Next to the
      original: `<Project>-shared/<ID>-replication`"* · *"Somewhere else"* (user types a path).
2. **Apply the answer.** For either default, compute the concrete path from answers 1–2:
   ```bash
   python3 -B SKILL_DIR/scripts/_safety.py --sources "<original>" [--id <ManuscriptID>] --suggest
   ```
   (option 1 of the output = other synced drive, option 2 = next to the original). Show the
   resulting full path in one line and proceed unless the user objects. If `<Project>-shared`
   already exists, say so: the package goes in a new subfolder; everything else in it stays
   untouched (and may be read as an additional source, e.g. a co-author's working copy).
   When the scripts run in a VM that mounts the folders (e.g. Cowork's `device_bash`), find the
   synced-drive roots with `get_device_info`/`device_list_dir` and apply the same rule by hand.
3. Validate and get the environment line:
   ```bash
   python3 -B SKILL_DIR/scripts/_safety.py --sources "<original 1>" "<original 2>" \
       --shared "<Project>-shared" --target "<Project>-shared/<ID>-replication"
   ```
   It refuses a target inside an original folder, an original inside the target, and a non-empty
   target (never overwrite; ask for another name). The shared folder may contain the target but
   everything else in it is read-only. In Cowork, request access to exactly these folders with
   `device_request_folder_access`, never more.
4. Start **every** shell call with the printed line:
   `export REPLICATION_READONLY="<originals>:<shared>" REPLICATION_TARGET="<target>" PYTHONDONTWRITEBYTECODE=1`
   — all bundled scripts refuse to write anywhere read-only except inside the target.
   Record the locations in `_migration/plan.md` once the target exists.

## Phase 1 — Discover (read-only)

1. Run the inventory on the project and on any co-author/shared copies the user mentions:
   ```bash
   python3 SKILL_DIR/scripts/inventory.py "<source>" --extra "<shared copy>" --output /tmp/inventory.md
   ```
   (Write to `/tmp` or a scratch dir until the target exists; move it to `_migration/` later.)
2. **Online-only files** (Dropbox / Google Drive "online only"). Do not ask the user to download
   anything. On the user's own machine (Claude Code in a terminal) the OS downloads a file when it is
   opened, and the scripts retry transient errors while that happens. In a sandbox/VM that mounts the
   folder (e.g. Cowork's `device_bash`), the cloud provider may not answer and reads fail with
   `[Errno 35] Resource deadlock avoided`. Then:
   ```bash
   python3 -B SKILL_DIR/scripts/inventory.py "<source>" --hydrate-list /tmp/hydrate.txt ...
   ```
   and trigger the downloads through the host — in Cowork, `device_stage_files` on those paths (≤50
   per call; the host app opens the files, which makes the provider download them; tell the user
   in one line that N files are being downloaded to their disk, as the tool requires for large
   batches). Re-run the inventory until the list is empty. Only code and `.tex` files need this in
   Phases 1–2; data files are downloaded when copied in Phase 4. Downloading does not modify the
   files, and Dropbox/Drive manage eviction as usual.
3. **Which .tex is final?** The newest file is often a slide deck or a later draft, and the final
   version may live elsewhere (Overleaf, journal system). Show the candidate table and ask. If the
   final source is a single file with `\appendix`, it will be split into paper + appendix.
4. **Paper and authors** (the package's own metadata — never a personal profile, since papers
   have different co-authors):
   ```bash
   python3 -B SKILL_DIR/scripts/project_info.py extract --tex "<final main.tex>" [--tex "<appendix.tex>"] --out /tmp/replication-info.json
   ```
   It reads `\title`, `\author`/`\and`, `\thanks`/`\footnote`, authblk `\affil`, e-mails and ORCID iDs
   and records where each value came from. Then complete what is missing for each author
   (affiliation if absent, website, ORCID, e-mail) with **web searches** (faculty pages, ORCID,
   RePEc/IDEAS, Google Scholar); keep the affiliation printed in the paper and add each URL used to
   the author's `sources`:
   ```bash
   python3 -B SKILL_DIR/scripts/project_info.py set --file /tmp/replication-info.json \
       --author "Name" --field website=… orcid=… source=<url used>   # or --json '{"authors":[...]}'
   ```
   Add the manuscript ID, journal and year. Then **show the table** (`project_info.py show`) and ask
   the user to confirm that these are the authors, in this order, with these details (corrections
   go through `set`); only then run `project_info.py confirm`. Nothing author-related is written into
   the package before this confirmation.
5. **Software environments.** After the inventory, find what the authors actually ran:
   ```bash
   python3 -B SKILL_DIR/scripts/detect_envs.py --project-root "<source>" [--extra-root …] \
       --report /tmp/envs.md --json /tmp/envs.json      # add --lineage _migration/lineage.json after Phase 2
   ```
   It lists evidence in the project (notebook kernelspecs such as `conda-env-<name>-py`,
   `mamba activate <name>` in cluster scripts, `environment.yml`, `requirements.txt`, `renv.lock`,
   adolist `.pkl`), the conda/mamba environments on the machine ranked by evidence and by how many of
   the code's imports they provide, and what the code needs in each language (Python imports,
   R packages, Stata user-written commands, Julia packages). Then **ask the user** (one batch):
   *"Was a mamba/conda environment used for this project? Best match: `<name>` (python X, N/M imports)
   — use it / another one / none"*; and, when the code uses them: which R (the env's R, a system R,
   renv), which Stata (flavor/location; its PLUS folder for installed packages), Julia project, etc.
   If the environments are not visible (e.g. a VM that only mounts the project), ask where the
   user's environments live and request read access to **that one environment folder** (read-only;
   add it to `REPLICATION_READONLY`). If no environment was used, the package's `environment.yml`
   is built from the detected imports instead (and the user is told it was reconstructed).
6. Read any **earlier replication attempt** found inside the source (RA folders, old packages):
   reuse what is good, never modify it.
7. Ask (one batch): final .tex (and appendix .tex if separate) · journal · if no manuscript ID was
   given in Phase 0, any ID found in file names (e.g. editor letters) — and, if the user confirms it,
   rename the still-empty target to `<ManuscriptID>-replication` · languages actually used ·
   Stata location/flavor (`which stata-mp stata-se stata`, `ls /Applications/Stata*`) · datasets
   that are licensed/confidential · steps that are slow or ran on a cluster · whether any code should
   be consolidated (default: no, one script → one notebook) · output strategy: **(A) Renaming
   notebook** (default: code keeps its output names; a notebook maps them to final names) or **(B)
   code writes final names** (natural when code is consolidated by paper output). Either way tables
   follow ground rule 4.

★ Checkpoint 1 — confirm the answers before Phase 2.

## Phase 2 — Map outputs and trace the code

1. Parse the final LaTeX (main first, then appendix files):
   ```bash
   python3 SKILL_DIR/scripts/parse_latex.py "<main.tex>" ["<appendix.tex>"] \
       --project-root "<source>" --output _migration/rename_map.json --print
   ```
   Review every non-`ok` status: `missing` (file not found — ask), `inline` (table pasted into the
   .tex), `unresolved`, `duplicate`. Check panel letters, overview images, grids and appendix
   letters against the compiled PDF (rules: `references/naming-conventions.md`).
2. Inline tables — match their numbers against generated files:
   ```bash
   python3 SKILL_DIR/scripts/match_inline_tables.py --project-root "<source>" \
       --rename-map _migration/rename_map.json --search tables --update
   ```
   It also looks for the code output behind complete table files the paper `\input`s (often
   hand-edited copies). High recall + precision = the generating file; "as panels" = two files
   combined; no match = hand-made table or a log — ask. Comment hints in the .tex are often stale.
3. Trace producers and data lineage:
   ```bash
   python3 SKILL_DIR/scripts/trace_outputs.py --project-root "<source>" [--extra-root "<shared copy>"] \
       --rename-map _migration/rename_map.json --exclude <unrelated subfolders> \
       --output _migration/lineage.json --report _migration/lineage.md
   ```
   Read `lineage.md` critically: pick one producer when variants tie (`X.ipynb`, `X-old`, `X-CAN`),
   resolve *ambiguous inputs* (file written by many scripts), *unresolved outputs*, raw inputs
   **NOT FOUND** (external drives, co-author machines, downloads) and *dynamic paths*. Open the
   candidate scripts to confirm — the trace is a heuristic, your reading is the check.
4. Write `_migration/plan.md`:
   * **Steps table** grouped in Parts (I. basic data → analysis blocks → rename/copy): step title ·
     source script(s) → new notebook name (Title-Case-Hyphenated, by purpose: `Clean-Merge-Data`,
     `Secession-Conflict-Regressions`) · language · inputs · outputs · figures/tables produced ·
     runtime class (normal / slow → guarded / cluster).
   * **Raw data table**: `raw-data/<Source>` folder (one per provider) · files · citation/URL ·
     licence · ship publicly? Licensed data also blocks **derived** files at fine granularity
     (lineage tells you which) — they go to the confidential zip.
   * Consolidation choices: many small scripts for paper tables may become one notebook organized
     `# Table 1` / `## Panel A`; abandoned variants are not migrated.

★ Checkpoint 2 — present the rename map (name ← source, as a table) and the plan; apply corrections.

## Phase 3 — Scaffold

The user never clones the template or edits configuration files — the skill does it.

1. **Compute specs** (README "Computational requirements"): when running on the user's machine,
   detect them (macOS: `sysctl -n machdep.cpu.brand_string hw.memsize`, `sw_vers -productVersion`;
   Linux: `lscpu`, `free -g`); in a VM ask the user which computer ran the analysis, and whether a
   cluster was used. Save with
   `project_info.py set --file /tmp/replication-info.json --json '{"compute":{"laptop_specs":"…","laptop_memory":"…","cluster_specs":"…"}}'`.
2. **Create the target from the template bundled with the skill** (no clone, no network):
   ```bash
   python3 -B SKILL_DIR/scripts/scaffold.py --target "<target>" --slug <paper-slug> --info /tmp/replication-info.json [--no-r] [--no-stata]
   ```
   It copies the template, drops template-development files, removes R/Stata parts the paper does
   not use, sets the environment name in `environment.yml`/`create_env.sh`, creates the standard
   folders including `_migration/`, stores `replication-info.json` in the target and fills the
   title/author/citation/compute tokens from it (refused if the authors are not confirmed). Later
   corrections: `project_info.py set --file <target>/replication-info.json …`, `confirm`, then
   `apply_defaults.py <target>`. (`--from github` uses the latest
   template from GitHub instead.) Move the Phase 1–2 working files into `<target>/_migration/`.
   For a conversion also delete the placeholder `1-paper/main.tex` and `2-appendix/appendix.tex`
   (replaced in Phase 5).
3. **Environment files from the environments the authors used** (never invented):
   ```bash
   # Python (+ conda R packages): from the chosen env — by name, or by reading its folder directly
   python3 -B SKILL_DIR/scripts/export_env.py -n <env>            -o "<target>/replication-package/environment.yml" --slug <paper-slug>
   python3 -B SKILL_DIR/scripts/export_env.py --prefix <env-folder> -o "<target>/replication-package/environment.yml" --slug <paper-slug> \
       [--add-missing <pkg> ...]     # imports the code needs that the env lacks (from detect_envs), flagged for the user
   # R packages not in the conda env, pinned to the installed versions; Stata packages from their install sources
   python3 -B SKILL_DIR/scripts/detect_envs.py --project-root "<source>" --lineage "<target>/_migration/lineage.json" --env <env> \
       --write-r "<target>/replication-package/environment.R" --write-stata "<target>/replication-package/setup.do"
   ```
   The export keeps only the packages the authors explicitly installed (plus top-level pip
   packages), pinned to the installed versions without build strings, so it is portable. Report
   imports the env does not provide (unused imports, or packages installed another way) and ask before
   adding them. Stata: when the PLUS folder is readable, `setup.do` installs each user-written package
   from the exact source it came from; otherwise (or additionally) run `adolist save <slug>.pkl` in the
   user's Stata and use `adolist install`; **vendor version-sensitive packages** the results depend on
   (e.g. an old `reghdfe`) into `progs/Stata/` with a copy step in `setup.do`. Julia: copy
   `Project.toml`/`Manifest.toml`. Put any extra install steps in `create_env.sh` (local
   `pip install -e`, compatibility shims, kernels). The template's environment files are only a
   fallback when nothing was detected.
4. Create the paper-specific folders from the plan: `raw-data/<Source>/`, `data/<Step>/`, output
   subfolders.

## Phase 4 — Migrate code and data

**Data.** Copy raw inputs into `raw-data/<Source>/` keeping original file names (including licensed
files — exclusion happens at zip time). Data that lived outside the project (external drives,
co-author Dropbox) must be brought in. Include intermediate data only for steps that are too
expensive to rerun, and pair it with a test cell (Phase 6). Large files: keep, but flag for the
README and zip.

**Code.**
* Existing notebooks → copy to `progs/<Lang>/`; set kernelspec to `python3` (Stata-in-Python too)
  or `ir`.
* Scripts →
  ```bash
  python3 SKILL_DIR/scripts/convert_to_notebook.py --lang python|stata|r "<src>" "<target>/replication-package/progs/<Lang>/<New-Name>.ipynb" --source-label "<path in source>"
  ```
  Stata notebooks use **pystata**: python3 kernel, first cell `import stata_init`, every cell
  `%%stata`. Review the cell split and add markdown that says what each section produces.
* Keep as scripts (copy next to the notebooks): cluster/batch scripts (`.sh`, `.sbatch`), scripts
  run with arguments (`python x.py {i}`), `.do` files called on a cluster, helper modules, `.ado`.
* Consolidate only if the user asked for it (OriginLanguages: 97 .do files → three
  `*-Main-Tables-Figures` notebooks with `# Table N` headings). Otherwise keep one notebook per
  original script, same code, same order.

**Paths.** Every notebook runs with cwd = its own folder (`progs/<Lang>/`), so every path is
`../../raw-data/…`, `../../data/…`, `../../graphs/…`, `../../tables/…`. Delete machine-specific
`cd`/`global path`/`if c(username)=="…"` blocks. Then:
```bash
python3 SKILL_DIR/scripts/audit_paths.py "<target>/replication-package/progs"
# write _migration/path_map.json ([[regex, replacement], ...]) from the report, then
python3 SKILL_DIR/scripts/audit_paths.py "<target>/replication-package/progs" --map _migration/path_map.json --apply
```
Repeat until the report is clean (or every remaining hit is justified in the log).

**Outputs.** Strategy A: make the code write into the same relative folders as in the source
(`graphs/Jupyter/…` stays `graphs/Jupyter/…` inside the package) so `rename_map.json` sources stay
valid. Strategy B: edit each `savefig` / `graph export` / `esttab using` to write
`../../graphs/paper/Figure-1-a.pdf`, `../../tables/appendix/Table-D3.tex`, … directly.

## Phase 5 — Names and LaTeX

1. Write the paper sources (never edit the original .tex):
   ```bash
   python3 SKILL_DIR/scripts/rewrite_tex_paths.py --rename-map _migration/rename_map.json "<final.tex>" \
       --out "<target>/1-paper/<ID>-main-<YYYYMMDD>.tex"
   ```
   Same for the appendix (`2-appendix/<ID>-appendix-<YYYYMMDD>.tex`). For every table whose body was
   pasted, the rows between the header `\midrule` and `\bottomrule` become
   `\input{./tables/<paper|appendix>/Table-N}`; head and foot stay verbatim, and the removed rows are
   saved to `_migration/original_bodies/Table-N.tex` (the reference for `compare_tables.py`).
   Tables it lists for manual work: multi-panel tables (keep each panel's header rows in the .tex and
   `\input` `Table-N-Panel-A`, `-B` bodies), tables without booktabs rules, tables inside `\input`'ed
   section files.
   Tables the paper `\input`s or `\include`s as **complete files** (their own `tabular` head/foot,
   often edited by hand so they look right — `"table_file": "full"` in the rename map) are treated the
   same way: the file is inlined into the new .tex with its head and foot verbatim, its body rows become
   `\input{./tables/<loc>/Table-N}`, and the original rows go to `_migration/original_bodies/`.
   (`--keep-table-files` disables this.) Files that already contain only body rows keep their `\input`.
   If paper and appendix are one file, run it once per output and cut at `\appendix`; the appendix
   keeps the preamble, starts with `\appendix` and `\counterwithin{figure}{section}` /
   `\counterwithin{table}{section}`. Copy `.bib`, `.sty`, `.bst`, `.cls` the documents need.
2. Build the renaming notebook (both strategies; rows already final are skipped):
   ```bash
   python3 SKILL_DIR/scripts/build_renaming_notebook.py --rename-map _migration/rename_map.json \
       --out "<target>/replication-package/progs/Python/Renaming.ipynb" [--path-map '[["old/","new/"]]']
   ```
   Pasted tables and complete table files get `extract_body(src, dst, replace=[], drop_rows=[])`:
   only the body rows of the code's output are kept. For complete files, `match_inline_tables.py`
   (Phase 2) looks for the code output the edited file came from (`generator`); if none is found the
   referenced file itself is assumed to be the code's output — confirm with `lineage.md`. Finish every
   `TODO` (unverified sources).
3. Run the producing notebooks and `Renaming.ipynb` **in the target** (before the code is migrated
   you may point `Renaming.ipynb` at existing outputs by copying them into the target — never run
   anything inside the source), then
   ```bash
   python3 SKILL_DIR/scripts/compare_tables.py "<target>" --rename-map _migration/rename_map.json
   ```
   Rows are aligned by their numbers. ✅ = every number printed in the paper is reproduced. Copy the
   suggested `drop_rows` (rows the paper omits, e.g. a commented-out "Mean Dependent" row) and
   `replace` pairs (labels edited in the paper) into the table's `extract_body` call and rerun until
   all tables pass. A ❌ on numbers is never fixed by editing numbers: find the cause (wrong script
   variant, older data vintage, sample, seed, wrong matched source) and tell the user.
4. `progs/Python/Copy-Final.ipynb` (template) needs no edits: it reads both .tex files and copies
   every referenced `graphs|tables/(paper|appendix)/…` file from `replication-package/`.
5. If LaTeX is installed, compile both documents and compare with the original PDF (page count,
   figure/table numbering).

## Phase 6 — index.ipynb

Follow `references/index-patterns.md`. Replace every template placeholder cell with the steps of
`plan.md`, in dependency order:
* title cell (title, authors); Stata cell with the detected `STATA_location`/`version` (remove it
  if no Stata); directory-structure cell listing all folders;
* one blue header + description (inputs, outputs, figures/tables) + run cell per notebook, using the
  template's `!cd ./progs/<Lang>/ && jupyter nbconvert … --execute … && … --to html` pattern
  (`kernel_name=python3` for Python and pystata notebooks, `ir` for R);
* slow steps: red header, runtime estimate, `should_I_run = False`, cluster and local options,
  one-iteration timing, and a green **test** that recomputes a slice and compares it with the
  shipped data;
* last part: `Renaming` then `Copy-Final`.

## Phase 7 — README and zips

1. Fill `replication-package/README.md` section by section (`references/readme-guide.md`): data
   sources table (one row per `raw-data/` folder), software (env, Stata packages incl. vendored
   versions, R), runtime/memory/storage, programs table mirroring index.ipynb with links to outputs,
   instructions, references. Remove template text that does not apply.
2. `replication-zip.ipynb`: add one exclusion cell per licensed source **and its derived files**
   (from lineage), e.g.
   ```python
   df_files.loc[df_files['file_path'].str.contains('raw-data/Ethnologue'), 'include'] = False
   df_files.loc[df_files['file_path'].str.contains('data/AggLangGADMv36'), 'include'] = False
   ```
   Even with nothing to exclude, leave a commented example. Also exclude `.ipynb_checkpoints`,
   `unused/` and bulky `scratch_data/` the user does not want to ship. Ask the user to confirm the
   list.

## Phase 8 — Verify

1. `python3 SKILL_DIR/scripts/check_package.py "<target>"` — fix until **0 errors**; review warnings.
2. Ask before executing anything heavy. With the user's environment, run the fast notebooks (or all
   of `index.ipynb`), rerun `compare_tables.py` (must be all ✅) and compare figures with the
   originals visually. Record results in `migration-log.md`.
3. Report to the user: what was built, what was verified, and what still needs them — notebooks not
   executed, licensed data to obtain, numbers in the text to locate, Zenodo upload, journal checklist.

## Completion checklist

- [ ] Source folders untouched; `_migration/` holds inventory, rename map, lineage, plan, log
- [ ] Only traced code migrated; every paper figure/table has a producer
- [ ] Template artifacts removed; no placeholders (`check_package.py` clean)
- [ ] `environment.yml` from the real env; `create_env.sh` ENV_NAME matches; `setup.do` + `.pkl` (+ vendored packages)
- [ ] All paths relative to `progs/<Lang>/`; `audit_paths.py` clean
- [ ] No spaces in any folder or file name (spaces → `-`); references updated
- [ ] Stata notebooks: pystata (`import stata_init`, `%%stata`)
- [ ] `Renaming.ipynb` complete (no TODO); names follow the convention; `Copy-Final.ipynb` runs
- [ ] Table heads/feet come from the final paper; bodies from the code; `compare_tables.py` all ✅
- [ ] `1-paper/` and `2-appendix/` .tex reference `graphs|tables/(paper|appendix)/…` and compile
- [ ] `index.ipynb` runs every step in order; slow steps guarded with tests
- [ ] README complete (data sources, software, runtime, programs table, instructions)
- [ ] `replication-zip.ipynb` excludes licensed data and its derivatives; user confirmed

# Template Directory Structure

The canonical layout of a finished package built from
`https://github.com/ozak/replication-folder-template`.

Where it lives (default convention, proposed in Phase 0):

```
<synced drive A, e.g. Dropbox>/<path>/<Project>/                     original working folder — read-only
<synced drive B, e.g. Google Drive>/<path>/<Project>-shared/          shared with co-authors
<synced drive B, e.g. Google Drive>/<path>/<Project>-shared/<ManuscriptID>-replication/
```

Inside the replication folder:

```
<ManuscriptID>-replication/
├── _migration/                      # skill working files — NOT zipped (inventory, rename_map.json,
│                                    #   lineage.md, plan.md, migration-log.md)
├── 1-paper/
│   ├── <ID>-main-<YYYYMMDD>.tex     # final paper, paths rewritten to ./graphs/…, ./tables/…
│   ├── <ID>-main-<YYYYMMDD>.pdf
│   ├── bibliography.bib (+ .sty/.bst/.cls needed to compile)
│   └── graphs/  tables/             # flat; only what this .tex uses (copied by Copy-Final.ipynb)
├── 2-appendix/
│   ├── <ID>-appendix-<YYYYMMDD>.tex
│   ├── <ID>-appendix-<YYYYMMDD>.pdf
│   └── graphs/  tables/             # flat; only what this .tex uses
├── replication-package/             # the part that is zipped and deposited
│   ├── index.ipynb                  # master notebook: runs every step in order
│   ├── README.md (+ README.pdf/html) # Social Science Data Editors template, filled in
│   ├── environment.yml              # minimal Python env (name = paper slug), no R packages
│   ├── environment-R.yml            # separate R env (<slug>-r), only if R is used
│   ├── create_env.sh                # creates the env, kernels, extra installs
│   ├── environment.R                # R packages at the authors' versions (core packages last, checked)
│   ├── setup.do                     # Stata packages via adolist (+ vendored versions)
│   ├── <slug>.pkl                   # adolist package list exported from the authors' Stata
│   ├── LICENSE.txt
│   ├── progs/
│   │   ├── Python/                  # notebooks (+ helper .py, cluster .sh/.sbatch)
│   │   │   ├── run_notebooks.py     # runner used by index.ipynb (limits, retries, dependencies)
│   │   │   ├── Renaming.ipynb       # outputs -> Figure-N / Table-N (generated, then finished by hand)
│   │   │   └── Copy-Final.ipynb     # graphs|tables/(paper|appendix) -> 1-paper|2-appendix/graphs|tables/
│   │   ├── Stata/                   # pystata notebooks + .do/.ado; stata_init.py is written by index.ipynb
│   │   └── R/                       # IRkernel notebooks
│   ├── raw-data/<Source>/           # one folder per data provider, original file names
│   ├── data/<Step>/                 # data created by the code
│   ├── graphs/<sub>/  tables/<sub>/ # analysis outputs as the code writes them
│   ├── graphs/paper|appendix/       # final, standardized names
│   ├── tables/paper|appendix/
│   ├── html/                        # HTML of every executed notebook (written by index.ipynb)
│   ├── scratch_data/                # bulky intermediate output (often excluded from the zip)
│   └── directory_structure.{txt,html,md}   # written by replication-zip.ipynb
└── replication-zip.ipynb            # builds the zips below
```

## Execution model

* `index.ipynb` runs from `replication-package/`. Each step cell calls the runner
  (`progs/Python/run_notebooks.py`): `runner.step("progs/Python/X.ipynb", after=[...])`.
  Sequential mode (default) runs the notebook when the cell runs and shows its HTML; parallel mode
  registers the steps and the last cell (`runner.run_all()`) runs them with limits and dependencies.
* The runner executes each notebook **in its own folder** (all paths start with `../../`), with no
  timeout, saves it and writes `html/<name>.html` even when it fails, limits Stata notebooks to the
  licence seats (and cores), retries notebooks that cannot start (first cell fails, e.g.
  `import stata_init` without a free seat), skips dependents of failed steps, and logs runtimes in
  `html/runtimes.json` (longest first next time). Also usable from a shell:
  `python progs/Python/run_notebooks.py progs/Python/A.ipynb progs/Stata/B.ipynb:after=A --parallel 4`.
* Stata: **pystata** (python3 kernel). The first cell of `index.ipynb` writes
  `progs/Stata/stata_init.py` from `STATA_location` and `version`; each Stata notebook starts with
  `import stata_init` and every cell with `%%stata`. Locals persist across cells.
* `.do` files that stay scripts run with `!cd ./progs/Stata/ && stata-mp -b do file.do`, then the
  log is printed and removed — same cwd as notebooks.
* R notebooks run with the `ir` kernel registered by `create_env.sh` from the R environment.

## Distribution zips (replication-zip.ipynb)

* `3-replication-package.zip` — everything in `replication-package/` marked `include=True`
* `4-confidential-data-not-for-publication.zip` — files excluded for licensing (given to the data
  editor only, never published)
* `full-replication.zip` (or `<ID>-replication.zip`) — the two zips + journal checklist, for the
  editor; `1-paper.zip` / `2-appendix.zip` when the journal wants the sources too.

## Why this structure

* Journals (AEA, EJ, RES, QJE…) require a self-contained package that reproduces every number,
  table and figure without the authors' machines.
* Notebooks keep code, narrative and output together; `index.ipynb` makes the run order unambiguous
  and its HTML output documents a full run.
* `1-paper/` and `2-appendix/` compile on their own from the package outputs, which proves the
  outputs in the package are the ones in the paper.

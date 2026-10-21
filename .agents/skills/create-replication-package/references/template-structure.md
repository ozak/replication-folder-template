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
│   ├── <ID>-main-<YYYYMMDD>.tex     # final paper, paths rewritten to graphs|tables/(paper|appendix)/
│   ├── <ID>-main-<YYYYMMDD>.pdf
│   ├── bibliography.bib (+ .sty/.bst/.cls needed to compile)
│   ├── graphs/paper/  tables/paper/          # copied by Copy-Final.ipynb
│   └── graphs/appendix/ tables/appendix/     # only if the main .tex references appendix items
├── 2-appendix/
│   ├── <ID>-appendix-<YYYYMMDD>.tex
│   ├── <ID>-appendix-<YYYYMMDD>.pdf
│   └── graphs/appendix/  tables/appendix/
├── replication-package/             # the part that is zipped and deposited
│   ├── index.ipynb                  # master notebook: runs every step in order
│   ├── README.md (+ README.pdf/html) # Social Science Data Editors template, filled in
│   ├── environment.yml              # conda/mamba env (name = paper slug)
│   ├── create_env.sh                # creates the env, kernels, extra installs
│   ├── environment.R                # extra R packages via renv (only if R is used)
│   ├── setup.do                     # Stata packages via adolist (+ vendored versions)
│   ├── <slug>.pkl                   # adolist package list exported from the authors' Stata
│   ├── LICENSE.txt
│   ├── progs/
│   │   ├── Python/                  # notebooks (+ helper .py, cluster .sh/.sbatch)
│   │   │   ├── Renaming.ipynb       # outputs -> Figure-N / Table-N (generated, then finished by hand)
│   │   │   └── Copy-Final.ipynb     # graphs|tables/(paper|appendix) -> 1-paper/, 2-appendix/
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

* `index.ipynb` runs from `replication-package/`. It executes each child notebook in place:
  `!cd ./progs/Python/ && jupyter nbconvert "X.ipynb" --to notebook --ExecutePreprocessor.kernel_name=python3 --execute --output "X.ipynb" && jupyter nbconvert "X.ipynb" --to html --output "../../html/X.html"`
  and shows the HTML in an IFrame.
* Every child notebook therefore runs with **cwd = its own folder** — all paths start with `../../`.
* Stata: **pystata** (python3 kernel). The first cell of `index.ipynb` writes
  `progs/Stata/stata_init.py` from `STATA_location` and `version`; each Stata notebook starts with
  `import stata_init` and every cell with `%%stata`. Locals persist across cells.
* `.do` files that stay scripts run with `!cd ./progs/Stata/ && stata-mp -b do file.do`, then the
  log is printed and removed — same cwd as notebooks.
* R notebooks use `--ExecutePreprocessor.kernel_name=ir`.

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

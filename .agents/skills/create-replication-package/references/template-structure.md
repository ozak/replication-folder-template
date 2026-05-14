# Template Directory Structure

The canonical layout for a replication package built from the template at `https://github.com/ozak/replication-folder-template`.

## Top-level structure

```
<ManuscriptID>-replication/
├── 1-paper/                         # Paper LaTeX source and compiled output
│   ├── <ManuscriptID>-main-<DATE>.tex
│   ├── <ManuscriptID>-main-<DATE>.pdf
│   ├── main.bib
│   ├── tables/paper/                # Final paper tables (Table-1.tex, ...)
│   └── graphs/paper/                # Final paper figures (Figure-1.pdf, ...)
│
├── 2-appendix/                      # Appendix LaTeX source and compiled output
│   ├── <ManuscriptID>-appendix-<DATE>.tex
│   ├── <ManuscriptID>-appendix-<DATE>.pdf
│   ├── tables/paper/                # Appendix tables (Table-A-1.tex, ...)
│   └── graphs/paper/                # Appendix figures (Figure-A-1.pdf, ...)
│
├── replication-package/             # Self-contained reproducible package
│   ├── index.ipynb                  # Master orchestration notebook — runs everything
│   ├── README.md                    # Documentation for replicators
│   ├── environment.yml              # Conda/Mamba environment (Python 3.11 + base R)
│   ├── environment.R                # Additional R packages via renv (if R is used)
│   ├── create_env.sh                # One-step environment creation script
│   ├── setup.do                     # Stata package installer (if Stata is used)
│   ├── LICENSE.txt                  # CC BY 4.0 or appropriate license
│   │
│   ├── progs/                       # Analysis code organized by language
│   │   ├── Python/                  # Python notebooks (.ipynb) + helper scripts
│   │   ├── Stata/                   # Stata notebooks + .do files + .ado utilities
│   │   └── R/                       # R notebooks (if R is used)
│   │
│   ├── raw-data/                    # Input datasets (from the source project)
│   │   └── <source>/                # One subdirectory per data source
│   │
│   ├── data/                        # Processed/intermediate data (created by code)
│   │   └── <type>/                  # Organized by output type or analysis step
│   │
│   ├── tables/                      # Generated tables
│   │   ├── paper/                   # Final paper tables (Table-N.tex)
│   │   └── <intermediate>/          # Intermediate outputs per specification
│   │
│   ├── graphs/                      # Generated figures
│   │   ├── paper/                   # Final paper figures (Figure-N.ext)
│   │   └── <intermediate>/          # Intermediate outputs
│   │
│   ├── html/                        # HTML versions of executed notebooks (auto-generated)
│   ├── scratch_data/                # Large intermediate computational outputs
│   └── directory_structure.*        # Auto-generated file listing (txt/html/md)
│
└── replication-zip.ipynb            # Creates distributable zip files
```

## File naming conventions

| Item | Convention | Example |
|---|---|---|
| Main paper LaTeX | `<ManuscriptID>-main-<YYYYMMDD>.tex` | `MS20230792-main-20240919.tex` |
| Appendix LaTeX | `<ManuscriptID>-appendix-<YYYYMMDD>.tex` | `MS20230792-appendix-20240919.tex` |
| Final figures (paper) | `Figure-N.ext` | `Figure-1.pdf` |
| Final figures (appendix) | `Figure-A-N.ext` | `Figure-A-1.pdf` |
| Final tables (paper) | `Table-N.tex` | `Table-1.tex` |
| Final tables (appendix) | `Table-A-N.tex` | `Table-A-1.tex` |

## Distribution zips (created by replication-zip.ipynb)

- `3-replication-package.zip` — public files only (excludes licensed/confidential data)
- `4-confidential-data-not-for-publication.zip` — excluded files
- `<ManuscriptID>-replication.zip` — full package for journal submission

## Key design decisions

**Why this structure?** Journals like AER, QJE, and RES require a self-contained package where a replicator can reproduce all results without access to the author's machine. The `replication-package/` folder is designed to be zipped and submitted as-is (minus any licensed data).

**Why notebooks?** Jupyter notebooks make the analysis transparent — each step is visible with code, outputs, and narrative in one place. `index.ipynb` ties everything together so the replication order is unambiguous.

**Why separate 1-paper/ and 2-appendix/?** Journals often require separate submissions of the manuscript and supplementary materials. Keeping them separate also means LaTeX paths are stable regardless of how the submission is assembled.

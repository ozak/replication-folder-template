# Filling in replication-package/README.md

The template README follows the Social Science Data Editors template (accepted by AEA, EJ, RES,
QJE…). `apply_defaults.py` fills the title, all authors (contributors, title block, citation) and compute specs from `replication-info.json`; everything below is paper-specific.
Both published packages are good models — CountryStability (Zenodo 10.5281/zenodo.14048457) and
OriginLanguages.

| Section | What to write | Where the information comes from |
|---|---|---|
| Title block | title, authors, journal, year, DOI (or manuscript ID until published) | final .tex, user |
| Suggested citation | paper + package (Zenodo DOI once minted) | user |
| **Overview** | "All computations are explained and executed from `index.ipynb` ([HTML](./index.html))"; machine used for testing; which steps are red (slow) and that tests confirm shipped data; mamba/conda instructions; which licensed datasets are *not* included | index.ipynb, user |
| Statement about Rights | tick both boxes only if true; ask the user | user |
| License for Data | CC BY 4.0 / CC BY-SA 4.0 / NC — ask | user |
| Summary of Availability | tick *some data cannot be made publicly available* when anything is excluded; add the 5-year preservation line for licensed data | replication-zip exclusions |
| **Details on Data Sources** | table: `Directory` (= `raw-data/<Source>`), full citation with link and access date, `Provided` (Yes/No), `Freely accessible` (URL or N/A + how to obtain/purchase). One row per `raw-data/` folder — no folder without a row, no row without a folder | lineage.md raw inputs, user |
| File list | keep the iframe to `directory_structure.html` (written by replication-zip.ipynb); blue = included, red = excluded | — |
| Software Requirements | Python/Stata/R versions; full package list from `environment.yml`; Stata packages from `setup.do`/`.pkl` (and vendored versions, e.g. reghdfe 5.6.8); R packages; OS tested | environment.yml, setup.do |
| Controlled Randomness | seeds set (where), or "no randomness" | grep code for `seed` |
| Memory, Runtime, Storage | summary checkboxes + details per expensive step (cluster specs from defaults, runtimes measured) | timing cells, user |
| **Description of programs/code** | table *Step · Scripts/Notebooks executed · Outputs generated*, grouped by Part exactly as in index.ipynb; outputs are links to the files (data, `graphs/paper/Figure-N`, `tables/paper/Table-N`) | plan.md, index.ipynb, rename_map.json |
| License for Code | usually CC BY 4.0 / MIT | user |
| Instructions to Replicators | unzip `3-replication-package.zip` (+ confidential zip if granted); `bash create_env.sh`; `do setup.do` in Stata; edit `STATA_location`; `jupyter lab` in the env; open `index.ipynb`; restart & run all | — |
| List of tables and programs | tick "all numbers in text" and "all tables and figures"; optionally a table Figure/Table → notebook → output file (generate from rename_map + lineage) | rename_map.json, lineage.md |
| References | every data source cited above, in full | — |

Also produce `README.pdf` / `README.html` (e.g. `pandoc README.md -o README.pdf`, ask before
installing pandoc) when the journal wants a PDF README.

Remove every template sentence that does not apply (R section if no R, cluster text if no
cluster). `check_package.py` flags leftover placeholders.

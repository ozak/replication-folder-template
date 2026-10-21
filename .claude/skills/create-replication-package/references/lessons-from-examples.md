# Lessons from real conversions

Read this when planning a migration. The first two packages were built by hand from messy folders;
the third was built with the skill. The skill now automates what they had to discover.

## Case 1 — CountryStability → MS20230792-replication (EJ 2025)

*Desmet, Ortuño-Ortín & Özak, "Is Secessionism Mostly About Income or Identity?"*

| Source situation | What the package did |
|---|---|
| Dropbox project folder shared with **another paper** (≈150 scripts in `progs/`, most for a Facebook-data project) | Only the ~20 scripts on the path to the paper's outputs were migrated. `trace_outputs.py` reproduces this selection (236 code files → 21) |
| A co-author working copy on Google Drive (`CountryStability-shared/`) where scripts had already become notebooks | Used as a second source (`--extra` / `--extra-root`); the replication was built from it |
| Many paper versions (`SecessionsNov2022.tex`, `…Jan2023`, `…August2023`, `manuscript.tex`) | The final one was confirmed; the package holds `MS20230792-main-20240919.tex` + `MS20230792-appendix-20240919.tex` |
| Figures referenced as `../graphs/Jupyter/Secession/SecUnion2/Msimulations_…_small.pdf`; 30 tables **pasted** into the .tex, with presentation edits made only in the paper (rows commented out, labels shortened) | `Renaming.ipynb` copies outputs to `graphs/paper/Figure-N[-x]`. Table 1 kept its head/foot in the paper and `\input`s only the body (`tables/paper/Table-1.tex` holds just the rows) — **the approach the skill now uses for every pasted table**. Other tables were rebuilt as full floats in Renaming (less faithful to later paper edits) |
| Overview map + two regional panels per figure | `Figure-1.jpg`, `Figure-1-a.jpg`, `Figure-1-b.jpg` |
| 1,000,000-row calibration run on SMU's cluster; 269-country language aggregation (>1 week on a laptop) | Red steps with `should_I_run = False`, SLURM `sbatch --array` option, local loop option, one-row timing demo, and green **tests** that recompute one row and compare with the shipped archive (`calibration_output_files.tar.xz`) |
| Licensed data (Ethnologue/WLMS, World Religion Database, ACLED, GTD) | Excluded from the public zip **together with every derived file that reveals it** (`data/AggLangGADMv36`, `data/Basic/GADMv36_adm1`, `scratch_data/GEcon`, …) |
| Stata .do files run on the cluster (`secessions_001-1.do`, `run_stata.sbatch`) | Kept as scripts next to the notebooks and called from index.ipynb |
| Stata via `stata_kernel` | (The template has since moved to **pystata**; use it for new packages) |

## Case 2 — OriginLanguages → MS20240011-replication (EJ)

*Galor, Özak & Sarid, "Roots of Cultural and Linguistic Traits"*

| Source situation | What the package did |
|---|---|
| 97 `.do` files (many variants: `…Clustered`, `…SameN`, `…Restricted`, `_old`), 30 `.py/.ipy` | Consolidated **by paper output**: `Main-Tables-Figures.ipynb`, `WVS-Main-Tables-Figures.ipynb`, `EASCCS-Main-Tables-Figures.ipynb` with headings `# Table 1`, `## Panel A`; data steps became `WALS`, `Ethnologue`, `ASJP-*`, `Clean-Merge-Data` notebooks |
| `.do` files that `cd "~/Dropbox/…/data/"` and write `../tables/New/…`; co-author paths `/Users/assaf_sarid/Dropbox/…`; GIS rasters on `/Volumes/My Book/…` | Every path made relative to the notebook folder (`../../data/…`); external-drive data copied into `raw-data/` |
| Code wrote outputs with final names directly (`esttab using "../../tables/Table-1.tex"`) | "Code writes final names" strategy; `Editing-Renaming-Tables-Figures.ipynb` keeps only the rows between `\midrule` and `\bottomrule` (body-only, head/foot in the paper) for e.g. Table 2's panels, and copies to paper/appendix folders |
| One `.tex` with paper + appendix (`origins-2024-ej-rr1.tex`) | Split into `1-paper/…main…tex` and `2-appendix/…appendix…tex` |
| 3×3 grids of binscatter panels | `Figure-B1a1 … B1c3` (now `Figure-B1-a1 … Figure-B1-c3`) |
| Raw data downloaded long ago (WALS 2014) | Notebook loads the original download **and** compares it with the current release / Wayback Machine copy |
| Results depend on an old `reghdfe` | `reghdfe-v5.6.8` vendored in `progs/Stata/`; `setup.do` copies it after `adolist install` |
| Python 3.11 broke legacy packages (`collections.Mapping`) | `create_env.sh` writes a `sitecustomize.py` compatibility shim; local package installed with `pip install -e ./raw-data/WALS/cldfbench-wals` |
| An RA's earlier half-finished package inside the source (`MS20240011-replication/` with `paper_tables.do`, `problems in replication.docx`) | Read it for hints; never overwrite it |
| Unused notebooks kept in `progs/*/unused/` | Better: do not migrate them; if the user insists, keep `unused/` and exclude it in replication-zip |

## Case 3 — MS15875 "Millet, Rice, and Isolation" (Oct 2026)

Built with this skill; Python + R + Stata, run on a cluster with a 4-seat Stata licence. The general
rules it led to are in `environments.md`, `reproducibility.md`, `cluster.md`, `backup.md`; the
concrete problems are in `known-issues.md`.

| Source situation | What the package did / what the skill does now |
|---|---|
| Authors' working env with 106 packages (Gurobi, graph-tool, Earth Engine, OpenJDK); hours to solve, failed on Linux | Minimal env from the imports, result-computing packages pinned, system libraries free; full env kept in `_migration/`; `check_env.py` solves linux-64 and osx-arm64 before shipping |
| R packages inside the Python env pulled a second R | Separate R env + kernel with `PROJ_DATA`/`GDAL_DATA` |
| R figures depended on ggplot2 ≤3.4, dplyr 1.1, a GitHub fork | Pinned core packages installed last and checked; fork at a fixed commit |
| Stata/MP with 4 network seats; 11-hour `margins` notebooks; Stata 19 4× slower than 18 | `run_notebooks.py`: Stata seat limit, retry when Stata cannot start, slow steps first, dependencies; authors' Stata version recorded |
| Kriging fit varied between runs | Run-twice check; threads limited; authors chose how to treat the paper's draw |
| TikZ figures and hand-written tables shifted the numbering | Numbers from the compiled `.aux` |
| Errors found in the original (Figure E3 loop, Tables I1–I4 identical, Figure 4-b stale) | Consistency checks in Phases 2 and 8; reported, fixed only with the authors' consent |
| Code produced far more than the paper used (≈390 estimations, ≈120 used) | Optional clean-up phase, verified by identical used outputs |
| DVC cache in Google Drive lost PDF versions | Caches outside synced drives (`backup.md`) |

## Recurring problems to expect

1. **Cloud placeholders**: Dropbox/Drive "online-only" files fail with `[Errno 35] Resource
   deadlock avoided` when read from a sandbox/VM mount (273 code files in CountryStability, 46 in
   OriginLanguages). On the user's Mac they download on open. From a sandbox, trigger the download
   through the host (Cowork: `device_stage_files`) — staging `origins-2024-ej-rr1.tex` made it
   readable from the VM afterwards. The user should never have to do this by hand.
2. **The final .tex is not the newest file** — or not in the folder at all (Overleaf, journal
   system). Always confirm.
3. **Comment hints lie**: `%./tables/…/X.tex` comments next to pasted tables are often stale;
   trust `match_inline_tables.py` scores, and check panels (two files matched together).
4. **Variants with the same output name** (`Secession-Figs.ipynb`, `-CAN`, `-Main`): prefer the
   most recent one that writes the exact file, and confirm.
5. **Notebook kernelspecs** like `conda-env-country-stability-py`: index.ipynb overrides them
   with `--ExecutePreprocessor.kernel_name=python3`; set child kernelspecs to `python3` anyway.
6. **Text numbers**: numbers quoted in the text (shares, counts) must come from some notebook
   cell — note where in the README ("List of tables and programs").

## Check on the CountryStability draft (Aug 2023)

Running `rewrite_tex_paths.py` → `Renaming.ipynb` (`extract_body`) → `compare_tables.py` on the
draft and its own outputs: 23 pasted tables became body-only `\input`s (7 multi-panel tables listed
for manual work); 13 of the 14 that had a matched source reproduced **every printed number**; the
only presentation differences were a "Mean Dependent" row commented out in the paper (→
`drop_rows=['Mean Dependent']`) and labels wrapped over two lines; one table (Soviet Union) had a
wrong matched source and was correctly flagged.

## Check on CountryStability-shared/manuscript.tex (complete table files)

That manuscript `\input`s 51 table files; 50 are complete floats (caption, headers, notes) produced
by the old Renaming notebook and partly edited. `rewrite_tex_paths.py` moved all 50 heads/feet into
the paper and replaced their bodies with `\input`s; `match_inline_tables.py` located the code outputs
(`tables/Jupyter/baseline/Table-2-Panel-A.tex`, …). After `extract_body`, 44 tables reproduced every
printed number (fixes suggested: drop the "Mean Dependent" row, rejoin wrapped labels); the rest had
no or a wrong code output among the files searched and were flagged.

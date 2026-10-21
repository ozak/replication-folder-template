# Reproducibility checks

Read in Phase 8. A package can be *reproducible* (same output every run) without *matching the
paper*, and can match the paper by luck without being reproducible. Check both.

## 1. Determinism: run twice and compare

Candidates (found by reading the code; grep for `seed`, `random`, `rng`, `bootstrap`, `simulate`,
`KMeans`, `n_jobs`, `Parallel`, `parfor`, `variogram`, `krig`, `optimize`, `glob`, `listdir`): random draws,
bootstrap, simulation, MCMC, k-means/clustering, iterative optimizers, kriging/variograms,
machine learning, multithreaded numerics, parallel loops, anything reading the clock or the
file system order (`glob`, `os.listdir`, Stata `dir`), `set`/dict iteration deciding order.

For each candidate step that is not too slow: copy the package (or just the step's inputs, notebook
and output folders) to two scratch folders, run the notebook in each with the runner, and compare the
outputs (§5). Never run it twice inside the package itself. For slow steps, ask the user whether to
run the check on the server.

## 2. Common causes and fixes

| Cause | Fix (ask before changing code that affects results) |
|---|---|
| No seed, or seed set after the first draw | set the seed at the top of the notebook / before the loop; R `set.seed`, Stata `set seed`, numpy `default_rng(seed)` passed down |
| Multithreaded reductions (BLAS, OpenMP, numba, joblib, k-means) | `threadpoolctl.threadpool_limits(1)` around the fit; `OMP_NUM_THREADS=1`; Stata `set processors 1` for the step |
| Parallel workers finishing in different orders | sort results by key before saving |
| Order from `set`/dict/`glob`/`os.listdir` | `sorted(...)`; explicit column lists |
| Floating-point summation order | usually harmless; report the size; compare with tolerance |
| Library version changed the algorithm | pin to the authors' version (`environments.md`) |
| BLAS backend (Accelerate vs OpenBLAS vs MKL) | cannot be removed across platforms; flag the step |

## 3. When a step varies: the paper is one draw ★

If the outputs of a step differ between runs, the numbers in the paper are one realization. Do not
pick a fix alone. Present to the authors, with the size of the variation in the printed numbers:

1. **Fix the variation** (seed, threads, ordering) and update the paper's numbers if they change.
2. **Fix the paper's draw**: hard-code the parameters the paper used (e.g. fitted variogram
   parameters) and keep the estimation code as documentation.
3. **Keep the variation** and document it in the README (range across runs).

Record the decision in `migration-log.md`.

## 4. Platform-sensitive steps

Fragile fits (near-singular matrices, many local optima, tight convergence tolerances) can differ
between machines. List them in `plan.md` and in the README ("results verified on <machine>; on
other platforms the n-th decimal of Table X may differ"), and verify them in the final run on the
reference machine.

## 5. Comparing outputs and explaining differences

Compare two output trees file by file: identical bytes → equal. Otherwise by type: csv/tsv/xlsx/dta/
parquet — load and compare values with a tolerance, ignoring column order (and report if only the
order differs); `.tex` tables — `compare_tables.py` logic, every number; figures — render PDFs to PNG
and compute a pixel difference (when PyMuPDF/Pillow are available; ask before installing), otherwise
compare sizes and look at both. Write a short script in `_migration/` for this when there are many
files. Every difference reported to the user says **which numbers, how large, why** (or that the
cause is unknown).

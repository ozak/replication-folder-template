# index.ipynb cell patterns

Copy these patterns (they come from the two published packages). Keep the template's colored
headers: **blue** = normal step, **red** = expensive/problematic step, **green** = test.

## Header and setup (top of the notebook)

1. Title cell: paper title, subtitle, authors (replace the template's `TITLE`, `FURTHER TITLE`).
2. "Instructions for replication" header.
3. Stata setup cell (keep only if Stata is used) — set the detected values, do not leave the
   placeholder comment as the only guidance:
   ```python
   STATA_location = '/Applications/Stata'   # <-- EDIT this path
   version = 'mp'                           # <-- EDIT: mp, se, or be
   ```
4. Directory-structure cell: the standard folders plus every `data/<Step>`, `graphs/<sub>`,
   `tables/<sub>` the code writes to (replicators without the licensed data still get the tree).

## Part / Step headers

```html
<div style="border-left: 5px solid blue; padding: 10px; background-color: #f9f9f9; border-radius: 5px; font-size: 30px;">
    <h1>Part I. Creating basic data</h1>
</div>
```
```html
<div style="border-left: 5px solid blue; padding: 10px; background-color: #f9f9f9; border-radius: 5px; font-size: 20px;">
    <h1>Step 2: Creating Ethnologue-based data</h1>
</div>

Original data is located in `./raw-data/Ethnologue/`; outputs are written to `./data/Ethnologue/`.
```
Sub-steps use `<h3>Step 2.1: …</h3>`. Under each header say **what the step produces** (files,
and which figures/tables) and link the notebook: ``run jupyter notebook [`./progs/Python/X.ipynb`](./progs/Python/X.ipynb)``.

Typical part structure: I. basic data (raw → clean) · II–N. analysis blocks (calibration,
counterfactuals, regressions, maps…) · last: rename, clean and copy tables and figures.

Steps that take hours: when the authors agree, split them into a compute notebook that saves its
estimates (coefficients, margins, predictions) to `data/<Step>/` and a separate plotting/table
notebook that reads them, so restyling a figure never needs the long rerun (Stata: also keep the
`.gph` files; `graph use` + `gr_edit` restyles without recomputing).

## Run a notebook (Python, Stata via pystata, R)

The template's runner cell (after the Stata setup) creates `runner`; every step is one cell:

```python
%%time
runner.step("progs/Python/WALS.ipynb")
```
```python
%%time
runner.step("progs/Stata/Main-Tables-Figures.ipynb", after=["Clean-Merge-Data"])
```
* `after=[...]`: the steps whose outputs this notebook reads (from `lineage.md`). Always fill it —
  it is what makes parallel mode safe and what skips a step whose inputs failed.
* Kernel: chosen from the notebook (`ir` for R, `python3` otherwise, including pystata).
* Other limited resources: `uses={"gurobi": 1}` and `LIMITS = {"gurobi": 1}` in the runner cell.
* Long or cluster runs: set `PARALLEL = True` in the runner cell; the step cells then only register,
  and the last cell `runner.run_all()` runs everything (see `cluster.md`).
* The last cell (`runner.run_all()`) prints the summary table in both modes; keep it.
* Do not go back to `!jupyter nbconvert …` cells: they lose the notebook when it fails.

## Run a .do file that stays a script

```python
%%time
file_name = 'list_regions'
!cd ./progs/Stata/ && stata-mp -b do {file_name}.do
with open(f'./progs/Stata/{file_name}.log') as fh:
    print(fh.read())
!rm ./progs/Stata/{file_name}.log
```

## Expensive step (red): cluster option, local option, guarded

```html
<div style="border-left: 5px solid red; padding: 10px; background-color: #f9f9f9; border-radius: 5px;">
<h1>Option 1 (suggested): Use computer cluster and SLURM</h1></div>
```
```python
%%time
should_I_run = False
if should_I_run:
    !cd ./progs/Python/ && sbatch --array=1-269 scriptMPGADMv36.sh
```
```python
%%time
should_I_run = False          # THIS MAY TAKE A VERY LONG TIME (>1 week on a laptop)
if should_I_run:
    for i in range(1, 270):
        !python ./progs/Python/proc_agglanguageMPGADM36.py {i}
```
State the estimated runtime and the machine it was measured on. Ship the outputs of the
expensive step in `data/` so later steps run without it.
A guarded notebook is `if should_I_run: runner.step("progs/…/X.ipynb")`. Because its outputs are
shipped, later steps do **not** list it in `after=[...]` (a step that was not run counts as missing).

## Test (green): recompute a slice and compare with the shipped data

Use this whenever a step is guarded (CountryStability did it for the language aggregation, the
1-million-row calibration, and the aggregation of 1M output files):

```python
%%time
should_I_run = True
if should_I_run:
    !python ./progs/Python/Secession-Union.py {i}      # one row only
```
```python
original = pd.read_stata('./scratch_data/test/calibration_0.5_0.3.dta')   # extracted from the shipped archive
new = pd.read_stata('./scratch_data/Jupyter/calibration_0.5_0.3.dta')
diff = original.merge(new, on=keys, suffixes=['_or', '_new'])
print('Max abs difference:', (diff['share_or'] - diff['share_new']).abs().max())
```
Follow with a markdown cell stating the conclusion ("The datasets are identical; tiny differences
come from OS/BLAS and do not affect results").

## Timing demo for a step too long to run

```python
%%time
!python ./progs/Python/Secession-Union.py 1
```
```python
print('So it can take about', 3 * 1e6 / 60 / 24, 'days on one core')
```

## Data downloads and third-party scripts

When raw data is downloaded by code (WALS via cldfbench, EA/SCCS via R) the step writes into
`raw-data/<Source>/` and the README states the access date. When a provider ships its own
merge script (WVS/EVS `EVS_WVS_Merge Syntax_stata.do`), read it, patch the `[YOUR PATH]`
placeholders in a cell, and run it from its folder — do not edit the provider's file by hand.

## Last part

```
Part LAST. Rename, Clean, and Copy Tables and Figures
  Step 1: run progs/Python/Renaming.ipynb
  Step 2: run progs/Python/Copy-Final.ipynb
```

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

## Run a notebook (Python, or Stata via pystata)

```python
%%time
notebook_name = 'WALS'
!cd ./progs/Python/ && jupyter nbconvert "{notebook_name}.ipynb" --to notebook --ExecutePreprocessor.kernel_name=python3 --execute --output "{notebook_name}.ipynb" && jupyter nbconvert "{notebook_name}.ipynb" --to html --output "../../html/{notebook_name}.html" 
url = f"./html/{notebook_name}.html"
IFrame(url, width=800, height=400)
```
For a Stata notebook change only the folder (`./progs/Stata/`); the kernel stays `python3`.
For R: `./progs/R/` and `--ExecutePreprocessor.kernel_name=ir`.
Add `--ExecutePreprocessor.timeout=-1` for long notebooks. Put `from IPython.display import IFrame`
in a cell before the first run cell.

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

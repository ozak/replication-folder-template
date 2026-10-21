# Running the package on a cluster or server

Read in Phase 6 when any step is slow, and when writing the README. Write a short
submission script for the user's scheduler from the essentials in §3.

## 1. Environment on the cluster

* Install miniforge in the home or project space (`bash Miniforge3-Linux-x86_64.sh -b -p $HOME/miniforge3`)
  and use `mamba`; cluster `conda` modules are often old and very slow to solve.
* `cd replication-package && bash create_env.sh` on a **login node** (it needs internet). Do the
  first import of packages that download data there too (`environments.md` §8).
* One install at a time; check the quota (`quota -s`) before installing.

## 2. Finding commercial software on the node

Stata:
```bash
module avail stata            # name of the module, if any
module load stata             # or stata/18, …
which stata-mp stata-se stata
readlink -f "$(which stata-mp)"           # → …/stata18/stata-mp
ls "$(dirname "$(readlink -f "$(which stata-mp)")")/utilities/pystata"   # must exist
```
`STATA_location` in `index.ipynb` is the folder that contains `utilities/` (e.g. `/opt/stata18`),
`version` is `mp`, `se` or `be`. Smoke test (inside the env):
```bash
python -c "import sys; sys.path.append('$STATA_DIR/utilities'); from pystata import config; config.init('mp'); from pystata import stata; stata.run('display c(stata_version) c(processors)')"
```
The banner printed at start shows the licence ("4-user 8-core network …"); the runner reads the
seat count from it.

MATLAB / Gurobi / other licensed tools: same pattern — module, path, a one-line smoke test, and the
number of seats or tokens for the runner's resource limit.

## 3. Submitting

* One node (`--nodes=1`), enough cores for `MAX_PARALLEL` × threads per notebook, memory for the
  largest step, walltime generous (`-t 2-00:00:00`); jobs that hit the walltime lose everything not
  saved — the runner saves each notebook when it finishes or fails.
* Submit **from `replication-package/`** so relative paths resolve.
* No nbconvert timeout for long notebooks: `--ExecutePreprocessor.timeout=-1` (the runner uses
  `timeout=None`).
* Run headless: `jupyter nbconvert --to notebook --execute index.ipynb --ExecutePreprocessor.timeout=-1 --output index.ipynb`
  (or `python progs/Python/run_notebooks.py --plan run-plan.json`).
* Array jobs (`sbatch --array=1-N`) for embarrassingly parallel scripts called with an index; the
  aggregation step depends on the array (`--dependency=afterok:<jobid>`).

PBS/Torque: `qsub` with `#PBS -l nodes=1:ppn=N,walltime=…`; LSF: `bsub -n N -W …`. Same rules.

## 4. Long runs: what to leave to the server

Once the code is final, do not rerun hours-long steps locally to "check". Fix the code, verify on
the fast steps locally, and leave the full run for the reference machine. Steps whose compute is
expensive should save their estimates to `data/` so figure/table styling can be redone from them
(SKILL.md Phase 4, "compute vs presentation").

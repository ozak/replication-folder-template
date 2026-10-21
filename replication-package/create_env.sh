#!/usr/bin/env bash
# Creates the software environments of this replication package and registers the Jupyter kernels.
#
#   cd replication-package && bash create_env.sh
#
# Runs unattended (no prompts, no sudo). Run it on a machine with internet access (on a cluster:
# the login node). One install at a time: two installs sharing a package cache corrupt it.
# Troubleshooting:
#   "SHA256 doesn't match" / CondaVerificationError -> mamba clean --all -y, then rerun
#   solving takes very long -> use miniforge's mamba (https://conda-forge.org/download/),
#                              not an old cluster conda module
#   out of space -> check your quota (quota -s / df -h ~)
set -euo pipefail

# ============================== EDIT HERE ==============================
ENV_NAME="awesome-project"          # Python environment (environment.yml)
R_ENV_NAME="awesome-project-r"      # R environment (environment-R.yml); ignored if that file is absent
USE_ACCELERATE=0                    # macOS: 1 = Apple Accelerate BLAS (faster, may change the last digits of fragile fits)

# Clusters only: load what the cluster provides (uncomment / adapt). Prefer your own miniforge
# installation over a cluster conda module.
# module purge
# module load stata/18
# export PATH="$HOME/miniforge3/bin:$PATH"
# ======================================================================

cd "$(dirname "$0")"
OS="$(uname)"
echo "Environments: $ENV_NAME${R_ENV_NAME:+ and $R_ENV_NAME} on $OS"

# --- pick a solver: mamba > micromamba > conda
if command -v mamba >/dev/null 2>&1; then SOLVER=mamba
elif command -v micromamba >/dev/null 2>&1; then SOLVER=micromamba
elif command -v conda >/dev/null 2>&1; then SOLVER=conda
else echo "No mamba/conda found. Install miniforge: https://conda-forge.org/download/" >&2; exit 1; fi

env_exists() { $SOLVER env list 2>/dev/null | awk '{print $1}' | grep -qx "$1"; }

make_env() {   # make_env <name> <yml>
    if env_exists "$1"; then
        echo "Environment $1 exists: updating it from $2"
        if [ "$SOLVER" = micromamba ]; then $SOLVER install -y -n "$1" -f "$2"; else $SOLVER env update -n "$1" -f "$2"; fi
    elif [ "$SOLVER" = micromamba ]; then
        $SOLVER create -y -n "$1" -f "$2"
    elif [ "$SOLVER" = mamba ]; then
        $SOLVER env create -y -n "$1" -f "$2"
    else
        $SOLVER env create -n "$1" -f "$2"
    fi
}
inenv() { local n="$1"; shift; $SOLVER run -n "$n" "$@"; }

# --- Python environment
make_env "$ENV_NAME" environment.yml
if [ "$OS" = "Darwin" ] && [ "$USE_ACCELERATE" = 1 ]; then
    $SOLVER install -y -n "$ENV_NAME" -c conda-forge "libblas=*=*accelerate"
fi
inenv "$ENV_NAME" python -m ipykernel install --user --name "$ENV_NAME" --display-name "Python ($ENV_NAME)"

# --- R environment (separate, so the Python env never pulls in a second R)
if [ -f environment-R.yml ]; then
    make_env "$R_ENV_NAME" environment-R.yml
    [ -f environment.R ] && inenv "$R_ENV_NAME" Rscript environment.R
    inenv "$R_ENV_NAME" R -q -e "IRkernel::installspec(name = 'ir', displayname = 'R ($R_ENV_NAME)')"
    # the R kernel must use the R env's PROJ/GDAL data, whichever environment starts Jupyter
    R_PREFIX="$(inenv "$R_ENV_NAME" Rscript -e 'cat(R.home())' | sed 's|/lib/R$||')"
    inenv "$ENV_NAME" python - "$R_PREFIX" <<'PY'
import json, sys
from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager
prefix = Path(sys.argv[1])
spec = Path(KernelSpecManager().get_kernel_spec("ir").resource_dir) / "kernel.json"
k = json.loads(spec.read_text())
env = k.setdefault("env", {})
for var, sub in (("PROJ_DATA", "share/proj"), ("PROJ_LIB", "share/proj"), ("GDAL_DATA", "share/gdal")):
    if (prefix / sub).is_dir():
        env[var] = str(prefix / sub)
spec.write_text(json.dumps(k, indent=1))
print(f"R kernel {spec}: {env}")
PY
fi

# --- Stata: pystata comes with Stata; set STATA_location/version in index.ipynb.
# --- Extra steps for this paper (local packages, compatibility shims, data needed at first import):
# inenv "$ENV_NAME" pip install -e ./raw-data/<Source>/<local-package>
# inenv "$ENV_NAME" python -c "import <package-that-downloads-data>"   # needs internet once

echo "Done. Start Jupyter with:  $SOLVER activate $ENV_NAME && jupyter lab"

#!/bin/bash

# Define the Conda environment name
ENV_NAME="Awesome-Project"

echo "Environment Name: $ENV_NAME"

# Determine the operating system
OS="$(uname)"

if [ "$OS" == "Linux" ]; then
    # Linux-specific commands
    echo "This is Linux"
    # Add Linux-specific commands here
    module purge
    module load conda
    module load stata/mp

fi

mamba env create -n $ENV_NAME -f environment.yml

# Activate the environment using source
#source $(mamba info --base)/etc/profile.d/conda.sh
mamba activate $ENV_NAME

if [ "$OS" == "Darwin" ]; then
    # macOS-specific commands
    echo "This is macOS"
    # Add macOS-specific commands here
    mamba run -n $ENV_NAME mamba install -c conda-forge -y "libblas=*=*accelerate"
fi

# Finish installing stata-kernel
mamba run -n $ENV_NAME python -m stata_kernel.install

# Install additional R packages and kernel
mamba run -n $ENV_NAME R -e "IRkernel::installspec()"

# You may need to install the fribidi library for your OS:
# Linux
if [ "$OS" == "Linux" ]; then
    # Linux-specific commands
    echo "This is Linux"
    # Add Linux-specific commands here
    sudo apt-get update
    sudo apt-get install libfribidi-dev

fi

# MACOS: Assumes you have brew installed
if [ "$OS" == "Darwin" ]; then
    echo "This is macOS"

    for pkg in fribidi automake autoconf; do
        if ! brew list --formula | grep -q "^$pkg\$"; then
            echo "Installing $pkg..."
            brew install "$pkg"
        else
            echo "$pkg is already installed"
        fi
    done
fi

# Initialize an renv project
#echo "Initializing renv project in the R environment..."
#mamba run -n $ENV_NAME R -e 'renv::init(bare = TRUE); renv::status(); renv::dependencies(); renv::snapshot(); '
#mamba run -n $ENV_NAME R -e 'renv::snapshot()'
#mamba run -n $ENV_NAME R -e 'renv::install(c("broom", "easypackages", "fixest", "furrr", "future", "gridExtra", "haven"));renv::install(c("tidyverse", "data.table", "ggplot2", "binsreg", "essentials", "dplyr", "remotes", "easypackages", "lfe", "languageserver"))'
#mamba run -n $ENV_NAME R -e "install.packages("ggchicklet", repos = "https://cinc.rud.is")"

# Install python kernel with name of environment
mamba run -n $ENV_NAME python -m ipykernel install --user --name=conda-env-$ENV_NAME-py

# Activate the environment
echo 'To activate this environment, use: mamba activate' $ENV_NAME

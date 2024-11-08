# Import renv to create environment
library(renv)

# Initialize renv
renv::init(bare = TRUE)

# Install dependiencies and packages
renv::install(c("broom", "easypackages", "fixest", "furrr", "future", "gridExtra", "haven"))
renv::install(c("tidyverse", "data.table", "ggplot2", "binsreg", "essentials", "dplyr", "remotes", "easypackages", "languageserver"))
renv::install("devtools")
renv::install(c("ggeffects", "margins", "tictoc", "purrr", "haven"))
Sys.unsetenv("GITHUB_TOKEN")
devtools::install_github("elbersb/shapley")

# Check status 
renv::status()

# Create snapshot
renv::settings$snapshot.type("all")
renv::snapshot()

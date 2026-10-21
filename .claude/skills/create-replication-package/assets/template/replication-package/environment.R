# Installs the R packages used by the code that environment-R.yml does not provide, at the
# authors' versions. The skill writes this file (detect_envs.py --write-r). Run inside the R env:
#   mamba run -n <slug>-r Rscript environment.R
# Order: packages that depend on others first; the packages they depend on LAST, so that
# installing an extension cannot upgrade its core package. Do not reorder.
options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("remotes", quietly = TRUE)) install.packages("remotes")
pin <- function(pkg, version) remotes::install_version(pkg, version = version, upgrade = "never", dependencies = NA)
gh  <- function(ref) remotes::install_github(ref, upgrade = "never", dependencies = NA)

# Examples:
# gh("user/repo@<commit sha>")      # GitHub package or fork, at a fixed commit
# pin("cowplot", "1.1.3")           # extensions first
# pin("ggplot2", "3.4.4")           # core package last

# Every package must have the authors' version
expected <- c(
  # "ggplot2" = "3.4.4"
)
for (p in names(expected)) {
  got <- as.character(packageVersion(p))
  if (got != expected[[p]]) stop(sprintf("%s is %s, expected %s", p, got, expected[[p]]))
}
cat("All", length(expected), "R packages have the expected versions\n")

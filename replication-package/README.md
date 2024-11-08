---
contributors:
  - [Ömer Özak](http://omerozak.com)

---

<div style="line-height: 1.1;">
    <h1><strong>TITLE</strong></h1>
    <h1><strong>FURTHER TITLE</strong></h1>
    <h1>by</h1>
    <h1><strong><a href="http://omerozak.com">Ömer Özak</a></strong></h1>
</div>

# Replication Repository

This repository contains the data and code to replicate the analyses performed in ["AWSOME PAPER]() by [Ömer Özak](http://omerozak.com).   If you use the code or data in this repository, please cite both the original paper and the dataset.

Suggested citation:

```cite
Özak, Ömer. (20XX) "AWESOME PAPER (Replication Package)"
```

## Overview

We have created a set of notebooks to help you replicate our analysis. All computations are explained and executed from the [main Jupyter notebook `index.ipynb`](./index.ipynb) ([HTML output](./index.html)).

Most analyses and replication steps should run on a personal computer, provided there is enough memory available—the code was tested on a MacBook Pro with 64 GB RAM. Sections or steps highlighted in <span style="color: red;">red</span> can be run on a personal laptop or desktop but may take too much time to be feasibly reproduced there.

If desired, you can use a cluster or supercomputer to exploit embarrassingly parallel processing using the code we provide. Alternatively, to avoid the need of additional computing resources, we have provided tests to confirm that the data we have created and shared is identical to that generated using the code and data we provide for each step.

If you are interested in performing the analyses on your own computer, you need to fork, clone, or download this repository. Install [Mamba](https://mamba.readthedocs.io/en/latest/) or [Conda](https://www.anaconda.com/), and create the Conda/Mamba environment using the included [environment.yml](./environment.yml) file. Follow [these instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) to install `conda`. Once installed, follow [these instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file) to create a `conda` environment using the provided `yml` file.

**Recommendation:** Since installing using `conda` can be slow and sometimes difficult, we recommend using [Mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html) instead. Follow [these instructions](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html) to install `mamba`. Once `mamba` is installed, use [`create_env.sh`](./create_env.sh) or [`environment.yml`](./environment.yml) to create the environment.

While all computations can be run from the [main notebook](./index.ipynb), you can also execute the underlying notebooks step by step. Each notebook offers additional explanations of what is being done.

The replication folder contains all code and data to produce all tables and figures in the paper. With the exception of licensed products that need to be purchased (e.g., [World Language Mapping System (Version 16) (WLMS16)](https://worldgeodatasets.com/language/) and [World Religions Database (WRD)](https://www.worldreligiondatabase.org/)) all raw data used in the analysis is included in the replication file (further information see below).

## Data Availability and Provenance Statements

### Statement about Rights

- [X] I certify that the author(s) of the manuscript have legitimate access to and permission to use the data used in this manuscript. 
- [X] I certify that the author(s) of the manuscript have documented permission to redistribute/publish the data contained within this replication package. Appropriate permission are documented in the [`LICENSE.txt`](LICENSE.txt) file.

### License for Data

The data are licensed under [![](https://img.shields.io/badge/License%20-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/) license. See [`LICENSE.txt`](./LICENSE.txt) for details.

### Summary of Availability

- [ ] All data **are** publicly available.
- [X] Some data **cannot be made** publicly available.
- [ ] **No data can be made** publicly available.
- [X] Licensed data used in this paper and not provided as part of the public replication package will be preserved for 5 years after publication, in accordance with journal policies. 

### Details on Data Sources

All data from each data source is in a separate directory within [./raw-data/](./raw-data/) as explained below.

| Directory                     | Source                                                                                                                                                           | Provided | Freely Accessible |
|--------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-------------------|
| ACLED                         | Raleigh, C., Linke, R., Hegre, H. and Karlsen, J. (2010). Introducing ACLED: An armed conflict location and event dataset, Journal of peace research 47(5): 651–660. Accessed on September 17, 2020. | No       | [https://acleddata.com/data-export-tool/](https://acleddata.com/data-export-tool/) |
| Calibration                   | Government Finance Statistics Yearbook (GSF) of the International Monetary Fund (IMF). Defense spending for years 1995-2015. | Yes      | [https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d3b015045405](https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d3b015045405) |
| Desmet-Gomes-Ortuno-JDE-2020   | Desmet, K., Gomes, J. F. and Ortuño-Ortín, I. (2020). The geography of linguistic diversity and the provision of public goods, Journal of Development Economics 143: 102384. | No       | N/A               |
| EstebanMayoralRay              | Esteban, J., Mayoral, L. and Ray, D., 2012. Ethnicity and conflict: An empirical study, American Economic Review, 102(4), pp.1310-1342. | Yes      | [https://doi.org/10.1257/aer.102.4.1310](https://doi.org/10.1257/aer.102.4.1310) |
| Ethnologue                    | World Language Mapping System (WLMS) Version 16. Dataset licensed by SIL International. | No       | N/A               |
| Federal                       | Treisman, D., 2008. Decentralization Dataset. | Yes      | [http://www.sscnet.ucla.edu/polisci/faculty/treisman/](http://www.sscnet.ucla.edu/polisci/faculty/treisman/) |
| FragilityIndex                | Fragile State Index (FSI) data for years 2006-2021. | Yes      | [https://fragilestatesindex.org/excel/](https://fragilestatesindex.org/excel/) |
| GED                           | Pettersson, T., et al. (2021). UCDP/PRIO Georeferenced Event Dataset (GED). Accessed on September 19, 2020. | Yes       | [https://ucdp.uu.se/downloads/index.html#ged_global](https://ucdp.uu.se/downloads/index.html#ged_global) |
| GEcon                         | Nordhaus, W. et al., 2006. The G-Econ Database on Gridded Output: Methods and Data, Yale University. | Yes      | [https://gecon.yale.edu/](https://gecon.yale.edu/) |
| GPW                           | Gridded Population of the World (GPW), v4. | Yes      | [https://sedac.ciesin.columbia.edu/data/collection/gpw-v4](https://sedac.ciesin.columbia.edu/data/collection/gpw-v4) |
| GTD                           | START (2022). Global Terrorism Database. Analysis uses the September 2019 version accessed on November 6, 2019. | No       | [https://www.start.umd.edu/gtd](https://www.start.umd.edu/gtd) |
| Joshua-Project                | Joshua Project. Accessed April 2024. | No       | [https://joshuaproject.net/](https://joshuaproject.net/) |
| Landscan                      | Bright, E. and P. R. Coleman, 2001. Landscan 2000, 2005, Oak Ridge, TN: Oak Ridge National Laboratory. | Yes      | [https://landscan.ornl.gov/](https://landscan.ornl.gov/) |
| PWT                           | Feenstra, R. C., Inklaar, R. and Timmer, M. P. (2015), The Next Generation of the Penn World Table, American Economic Review, 105(10), 3150-3182. | Yes      | [www.ggdc.net/pwt](www.ggdc.net/pwt) |
| RegionalAuthorityIndex         | Hooghe, L., et al. (2016). Measuring regional authority: A postfunctionalist theory of governance, Volume I, Oxford University Press. | Yes      | [https://garymarks.web.unc.edu/data/regional-authority-2/](https://garymarks.web.unc.edu/data/regional-authority-2/) |
| Regions                       | GADM, the Database of Global Administrative Areas, version 3.6. | No       | [https://gadm.org/](https://gadm.org/) |
| Sambanis                      | Sambanis, N., et al. (2018). Sdm: A new data set on self-determination movements, Journal of Conflict Resolution 62(3): 656–686. | Yes      | [https://journals.sagepub.com/doi/10.1177/0022002717735364](https://journals.sagepub.com/doi/10.1177/0022002717735364) |
| SovietUnion                   | Flakierski, H. (2017). Income inequalities in the former Soviet Union and its republics, Routledge. | Yes      | N/A               |
| Wikipedia                     | Wikipedia, The Free Encyclopedia, s.v. "List of Active Secessionist movements". Accessed October 12, 2020. | Yes      | <ul><li>[List of active separatist movements in Africa](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Africa)</li><li>[List of active separatist movements in Asia](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Asia)</li><li>[List of active separatist movements in Europe](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Europe)</li><li>[List of active separatist movements in North America](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_North_America)</li><li>[List of active separatist movements in Oceania](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Oceania)</li><li>[List of active separatist movements in South America](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_South_America)</li></ul> |
| WorldReligionDatabase          | Zurlo, G. A., 2024. World Religion Database (WRD), Leiden/Boston: Brill. | No       | N/A               |

## File list

The frame below shows the directory structure of the full replication package. Files in <span style="color: blue;">blue</span> are included in the replication package. Files in <span style="color: red;">red</span> are not. You can access the ASCII txt version (no colors) [here](./directory_structure.txt).

<div style="border: 3px solid #4CAF50; border-radius: 8px; padding: 10px; background-color: #f9f9f9;">
<iframe src="./directory_structure.html" width="100%" height="400px" style="border:none;">
        Your browser does not support iframes.
</iframe>
</div>

## Computational requirements

### Software Requirements

- [X] The replication package contains one or more programs to install all dependencies and set up the necessary directory structure.

- Stata (code was last run with version 18)
  - the program [`setup.do`](./setup.do) will install all dependencies locally, and should be run once.
  - dependencies:
        - `abar`
        - `acreg`
        - `adolist`
        - `avar`
        - `bacondecomp`
        - `bcuse`
        - `betacoef`
        - `bimap`
        - `binscatter`
        - `binscatter2`
        - `binsreg`
        - `boottest`
        - `catplot`
        - `center`
        - `cltest`
        - `clusterbs`
        - `clustse`
        - `coefplot`
        - `collin`
        - `colrspace`
        - `copydesc`
        - `corrtex`
        - `csdid`
        - `did_imputation`
        - `did_multiplegt`
        - `distinct`
        - `dm0014`
        - `dm0038_1`
        - `dm49`
        - `dm69`
        - `dm79`
        - `drdid`
        - `dups`
        - `egenmore`
        - `erepost`
        - `estout`
        - `event_plot`
        - `eventdd`
        - `eventstudyinteract`
        - `eventstudyweights`
        - `fapara`
        - `fre`
        - `ftools`
        - `geodist`
        - `gr0017`
        - `gr0021_2`
        - `gr0034`
        - `gr0059_1`
        - `gr0070`
        - `gr0073`
        - `gsample`
        - `gtools`
        - `hdfe`
        - `hhi`
        - `hilo`
        - `iscogen`
        - `ivreg2`
        - `ivreg2h`
        - `ivreghdfe`
        - `joyplot`
        - `kdens2`
        - `labellist`
        - `marimekko`
        - `mat2txt`
        - `matin4-matout4`
        - `matsort`
        - `mean2`
        - `moremata`
        - `moss`
        - `outreg2`
        - `overid`
        - `palettes`
        - `plausexog`
        - `plottabs`
        - `ppmlhdfe`
        - `psacalc`
        - `ranktest`
        - `rcheck`
        - `rdrobust`
        - `reghdfe`
        - `regife`
        - `rego`
        - `resboot_mediation`
        - `scheme-burd`
        - `schemepack`
        - `sdecode`
        - `sg151_2`
        - `sg161`
        - `sg162`
        - `sg76`
        - `sgmediation`
        - `snp10`
        - `speccurve`
        - `specurve`
        - `spost13_ado`
        - `st0002`
        - `st0030_3`
        - `st0035_1`
        - `st0036`
        - `st0037_3`
        - `st0043_2`
        - `st0053_3`
        - `st0108`
        - `st0150_4`
        - `st0171_1`
        - `st0173_1`
        - `st0225`
        - `st0292`
        - `st0337_1`
        - `st0368_2`
        - `st0549`
        - `st0582_1`
        - `st0589`
        - `stripplot`
        - `sum2`
        - `sutex`
        - `sxpose`
        - `synth`
        - `tab2docx`
        - `tab2xl`
        - `tabplot`
        - `treemap`
        - `twowayfeweights`
        - `unique`
        - `wbopendata`
        - `weakiv`
        - `wyoung`
        - `xtimportu`
        - `xtivreg2`
        - `zoib`
- Python (code was last run with version 3.11.6)
  - the file "[`environment.yml`](./environment.yml)" lists these dependencies, please follow instructions above to setup the `conda/mamba` environment.
  - dependencies:
    - `python=3.11.6`
    - `ipython=8.10.0`
    - `dask=2023.6.0`
    - `dask-labextension=6.1.0`
    - `geopandas=0.12.2`
    - `geos=3.11.1`
    - `gdal=3.6.2`
    - `geoplot=0.5.1`
    - `georasters=0.5.29`
    - `ipyparallel=8.4.1`
    - `jupyter=1.0.0`
    - `jupyterlab=3.5.3`
    - `jupyter_contrib_nbextensions=0.7.0`
    - `mapclassify=2.8.0`
    - `matplotlib=3.9.2`
    - `matplotlib-base=3.9.2`
    - `nodejs=18.15.0`
    - `numpy=1.26.4`
    - `nb_conda_kernels=2.3.1`
    - `nbclassic=0.5.1`
    - `nbclient=0.7.2`
    - `nbconvert=7.2.9`
    - `pandas=2.2.2`
    - `pandas-datareader=0.10.0`
    - `plotly=5.24.0`
    - `pip=24.2`
    - `pycountry=24.6.1`
    - `pyproj=3.5.0`
    - `requests=2.32.3`
    - `scipy=1.14.1`
    - `seaborn=0.13.2`
    - `shapely=2.0.1`
    - `scikit-learn=1.5.1`
    - `stata_kernel=1.12.2`
    - `statsmodels=0.14.2`
    - `unidecode=1.3.8`
    - `xlrd=2.0.1`
    - `libblas=3.9.0`
    - `ca-certificates=2024.8.30`
    - `certifi=2024.8.30`
    - `openssl=3.1.7`
    - `openpyxl=3.1.5`
    - `cython==3.0.11`
    - `formulaic==1.0.2`
    - `future==1.0.0`
    - `geocoder==1.38.1`
    - `geonamescache==2.0.0`
    - `interface-meta==1.3.0`
    - `isounidecode==0.3`
    - `linearmodels==6.0`
    - `mypy-extensions==1.0.0`
    - `pyhdfe==0.2.0`
    - `ratelim==0.1.6`
    - `setuptools-scm==8.1.0`
    - `stargazer==0.0.7`
    - `wrapt==1.16.0`  

Portions of the code use bash scripting, which may require Linux/MACOS.

Portions of the code use SLURM scripting, which requires a Linux server. 

### Controlled Randomness

- [X] No Pseudo random generator is used in the analysis described here.

### Memory, Runtime, Storage Requirements

#### Summary

Approximate time needed to reproduce the analyses on a standard (CURRENT YEAR) desktop machine:

- [ ] <10 minutes
- [ ] 10-60 minutes
- [ ] 1-2 hours
- [ ] 2-8 hours
- [ ] 8-24 hours
- [ ] 1-3 days
- [X] 3-14 days
- [ ] > 14 days

Approximate storage space needed:

- [ ] < 25 MBytes
- [ ] 25 MB - 250 MB
- [ ] 250 MB - 2 GB
- [ ] 2 GB - 25 GB
- [X] 25 GB - 250 GB
- [ ] > 250 GB

- [ ] Not feasible to run on a desktop machine, as described below.

#### Details

The code was last run on a **Macbook Pro laptop with M3 Max Chipset, 64GB RAM, MacOS version 14.6.1 with 1TB of free space**. 

Portions of the code were last run on SMU's M3 cluster using the `standard-s` and `standard-l` queues, which provide access to a **AMD EPYC 7763 64-Core Processor server with 128-cores, 512 GB of RAM, 12 TB of fast local storage running Linux Ubuntu 22.04.4 LTS**. Computation took about **500K computing hours (~10 actual days)**. 


## Description of programs/code

| **Step**                                        | **Script/Notebook Executed**                                                  | **Outputs Generated**                                                                                              |
|-------------------------------------------------|-------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| <tr><td colspan="3" align="center"><strong>Part I: Creating Basic Data</strong></td></tr>  | | |
| **Step 1: Generating XXX data**          | [./progs/Python/Creating-XXX-data.ipynb](./progs/Python/Creating-XXX-data.ipynb)   | [`./data/XXX`](./data/XXX) |
| **Step 2: Create More Stuff**  | [./progs/Python/MoreStuff.py](./progs/Python/MoreStuff.py) | [`./data/MoreStuff/MoreStuff1.csv`](./data/MoreStuff/MoreStuff1.csv), and similar files located in [./data/MoreStuff/](./data/MoreStuff/)  |
| <tr><td colspan="3" align="center"><strong>Part II: Whatever you did next</strong></td></tr>  | | |
| **Step 1:**     | [./progs/Stata/step1.do](./progs/Stata/step1.do),  | [`./data/Step1/Step1.dta`](./data/Step1/Step1.dta) |
| **Step 2:**     | [./progs/Python/Step2.ipynb](./progs/Python/Step2.do),  | [`./data/Step2/Step2.dta`](./data/Step2/Step2.dta) |
| <tr><td colspan="3" align="center"><strong>Part III: Rename, Clean, and Copy Tables and Figures</strong></td></tr>  | | |
| **Step 1: Rename and Clean Tables and Figures**   | [./progs/Python/Renaming.ipynb](./progs/Python/Renaming.ipynb)   | [`./graphs/paper/Figure-1-a.jpg`](./graphs/paper/Figure-1-a.jpg), [`./graphs/paper/Figure-1-b.jpg`](./graphs/paper/Figure-1-b.jpg), [`./graphs/paper/Figure-1.jpg`](./graphs/paper/Figure-1.jpg), [`./tables/paper/Table-1.tex`](./tables/paper/Table-1.tex), [`./tables/paper/Table-2.tex`](./tables/paper/Table-2.tex), [`./tables/paper/Table-3.tex`](./tables/paper/Table-3.tex) |
| **Step 2: Copy Tables and Figures**   | [./progs/Python/Copy-Final.ipynb](./progs/Python/Copy-Final.ipynb)   | Copied tables and figures to the final output folder as requested by Journal.  |

### License for Code

The code is licensed under [![](https://img.shields.io/badge/License%20-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/) license. See [`LICENSE.txt`](./LICENSE.txt) for details.

## Instructions to Replicators

- Download and extract the zipped replication files 
	- `3-replication-package.zip` 
	- `4-confidential-data-not-for-publication.zip`.
- Execute the code [`setup.do`](./setup.do)
- Start `jupyter lab` from the `country-stability` environment created above.
- Open the [main Jupyter notebook `index.ipynb`](./index.ipynb) 
- Restart kernel and execute all cells (or execute each cell by hand)

### Details

- [`setup.do`](./setup.do): will install all Stata packages that existed on our system at the time of the replication. 
- [main Jupyter notebook `index.ipynb`](./index.ipynb): 
	- Executes all underlying code in Python and Stata
	- Generates data and tests
	- Creates all tables and figures in paper

## List of tables and programs

The provided code reproduces:

- [X] All numbers provided in text in the paper
- [X] All tables and figures in the paper

## References

* Bright, E. and P. R. Coleman, 2001. Landscan 2000, 2005, Oak Ridge, TN: Oak Ridge National Laboratory. Available online at [https://landscan.ornl.gov/](https://landscan.ornl.gov/)
* Desmet, K., Gomes, J. F. and Ortuño-Ortín, I. (2020). [The geography of linguistic diversity and the provision of public goods](https://doi.org/10.1016/j.jdeveco.2019.102384), Journal of Development Economics 143: 102384.
* Esteban, J., Mayoral, L. and Ray, D., 2012. [“Ethnicity and conflict: An empirical study”](https://doi.org/10.1257/aer.102.4.1310). American Economic Review, 102(4), pp.1310-1342. 
* Feenstra, Robert C., Robert Inklaar and Marcel P. Timmer (2015), "The Next Generation of the Penn World Table" American Economic Review, 105(10), 3150-3182, available for download at [www.ggdc.net/pwt](www.ggdc.net/pwt)
* Flakierski, H. (2017). Income inequalities in the former Soviet Union and its republics, Routledge.
* [Fragile State Index (FSI)](https://fragilestatesindex.org/) data for years 2006-2021 available online at [https://fragilestatesindex.org/excel/](https://fragilestatesindex.org/excel/)
* GADM, the Database of Global Administrative Areas, version 3.6 available at [https://gadm.org/](https://gadm.org/)
* Government Finance Statistics Yearbook (GSF) of the International Monetary Fund (IMF). Defense spending for years 1995-2015, available at [https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d3b015045405](https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d3b015045405).
* Gridded Population of the World (GPW), v4 available at [https://sedac.ciesin.columbia.edu/data/collection/gpw-v4](https://sedac.ciesin.columbia.edu/data/collection/gpw-v4)
* Hooghe, L., Marks, G., Schakel, A. H., Osterkatz, S. C., Niedzwiecki, S. and Shair-Rosenfield, S. (2016). Measuring regional authority: A postfunctionalist theory of governance, Volume I, Oxford University Press. Available online at [https://garymarks.web.unc.edu/data/regional-authority-2/](https://garymarks.web.unc.edu/data/regional-authority-2/)
* Joshua Project. Available online at [https://joshuaproject.net/](https://joshuaproject.net/). Accessed April 2024.
* Nordhaus, W., Azam, Q., Novoa Corderi, D., Hood, K., Victor, N., Mohammed, M., Miltner, A. and J. Weiss, 2006. “The G-Econ Database on Gridded Output: Methods and Data,” New Haven, CT: Yale University. Available online at [https://gecon.yale.edu/](https://gecon.yale.edu/)
* Melander, E., Möller, F. and M. Öberg, 2009. “Managing Intrastate Low-Intensity Armed Conflict 1993- 2004: A New Dataset,” International Interactions, 35(1): 58-85. UCDP Managing Intrastate Low-intensity Conflict (MILC) dataset v.10 available online at [https://ucdp.uu.se/downloads/index.html#milc](https://ucdp.uu.se/downloads/index.html#milc). Accessed on September 19, 2020.
* Pettersson, T., Davis, S., Deniz, A., Engström, G., Hawach, N., Högbladh, S., Sollenberg, M. and M. Öberg, 2021. “Organized Violence 1989-2020, with a Special Emphasis on Syria,” Journal of Peace Research, 58(4): 809-825. UCDP/PRIO Georeferenced Event Dataset (GED) available at [https://ucdp.uu.se/downloads/index.html#ged_global](https://ucdp.uu.se/downloads/index.html#ged_global). Accessed on September 19, 2020.
* Raleigh, C., Linke, R., Hegre, H. and Karlsen, J. (2010). Introducing ACLED: An armed conflict location and event dataset, Journal of peace research 47(5): 651–660. Available at [https://acleddata.com/data-export-tool/](https://acleddata.com/data-export-tool/). Accessed on September 17, 2020.
* Sambanis, N., Germann, M. and Schädel, A. (2018). [Sdm: A new data set on self- determination movements with an application to the reputational theory of conflict](https://journals.sagepub.com/doi/10.1177/0022002717735364), Journal of Conflict Resolution 62(3): 656–686. Data accessible at [https://journals.sagepub.com/doi/suppl/10.1177/0022002717735364/suppl_file/supplementary_materials.zip](https://journals.sagepub.com/doi/suppl/10.1177/0022002717735364/suppl_file/supplementary_materials.zip)
* START (National Consortium for the Study of Terrorism and Responses to Terrorism). (2022). Global Terrorism Database, 1970 - 2020 [data file]. Available at [https://www.start.umd.edu/gtd](https://www.start.umd.edu/gtd). Analysis uses the September 2019 version accessed on November 6, 2019.
* Treisman, D., 2008. Decentralization Dataset. Available online at [http://www.sscnet.ucla.edu/polisci/faculty/treisman/](http://www.sscnet.ucla.edu/polisci/faculty/treisman/). Federal. Accessed on August 10, 2016.
* Weidmann, N. B., Rød, J. K., and L.-E. Cederman. 2010. “Representing Ethnic Groups in Space: A New Dataset”. Journal of Peace Research 47(4): 491–99.
* Wikipedia, The Free Encyclopedia, s.v. "List of Active Secessionist movements". Multiple entries accessed on October 12, 2020 available at
	* [List of active separatist movements in Africa](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Africa)
	* [List of active separatist movements in Asia](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Asia)
	* [List of active separatist movements in Europe](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Europe)
	* [List of active separatist movements in North America](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_North_America)
	* [List of active separatist movements in Oceania](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_Oceania)
	* [List of active separatist movements in South America](https://en.wikipedia.org/wiki/List_of_active_separatist_movements_in_South_America)
* World Language Mapping System (WLMS) Version 16. Dataset licensed by SIL International.
* Zurlo, G. A., 2024. [World Religion Database (WRD)](https://www.worldreligiondatabase.org/), Leiden/Boston: Brill.

---

# Copyright 

This data and code is provided under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License](https://creativecommons.org/licenses/by-sa/4.0/). ![](http://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)

[<img src="https://github.com/measuring-culture/Expanding-Measurement-Culture-Facebook-JRSI/blob/e3698e2166d224a251a3123886cc7831b85a87b9/pics/SMUlogowWordmarkRB.jpg?raw=true" width="250">](http://omerozak.com)
[<img src="https://github.com/measuring-culture/Expanding-Measurement-Culture-Facebook-JRSI/blob/e3698e2166d224a251a3123886cc7831b85a87b9/pics/UC3M.png?raw=true" width="200">]()

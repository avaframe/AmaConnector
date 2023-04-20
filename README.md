# AmaConnector

### Usage
The scripts gathered in the AmaConnector can be used to fetch data from the Ama database and perform simple statistical analysis of the dataset. In runScripts, you can find different example scripts that demonstrate options to explore the available datasets.

#### runFetchData.py
search the database for recorded events and provide the dataset as a pandas dataframe with one row per event

#### runFetchDataAnalysis.py
search the database for recorded events and provide the dataset as a pandas dataframe with one row per event, filter for events with info on release and runout point, project geometry info to desired projection, compute travel length of release-runout along avalanche thalweg (in xy), altitude drop and corresponding travel angles, same for origin to deposition and origin to transit points, create plots of this analysis for each event as well as summary plots of the full dataset like histograms of travel angles, boxplots of travel angles, travel lengths and altitude drops


### Prerequisites

In order to run the AmaConnector functions, the following packages need to be installed:

* geopandas
* psycopg2
* gdal
* avaframe


### Installation

Create a new conda environment (https://conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) for the AmaConnector, activate it and install pip, numpy and cython in this environment:

    conda create --name ama
    conda activate ama
    conda install pip numpy cython

install AvaFrame (see also detailed instructions in: https://docs.avaframe.org/en/latest/).
As a next step, install the following libraries for example using conda or pip:

    conda install -c conda-forge gdal
    conda install -c conda-forge geopandas
    pip install psycopg2-binary

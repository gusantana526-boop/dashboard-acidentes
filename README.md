README – Occupational Accidents and Climate Data Repository - Brazil 2006 to 2024

Overview



This repository contains the datasets and R scripts used to construct a comprehensive Brazilian database linking occupational accident records with meteorological variables across Brazil from 2006 to 2024. The main goal of this repository is to provide a consistent and reproducible data infrastructure to investigate the effects of climate and climate change on the incidence of occupational accidents across Brazil. The repository is structured to ensure transparency, reproducibility, and clear separation between raw, processed, and final compiled datasets. All documentation adheres to a strict academic and scientific standard.



Repository Structure



The repository is organized into two main directories:



1\. data/



This folder contains all datasets used and produced throughout the research process. It is subdivided as follows:



1.1. raw data/

Contains the original, unprocessed datasets. These include:



1.1.1. /municipalities/

&nbsp;	

Municipal-level information from the Brazilian Institute of Geography and Statistics (Instituto Brasileiro de Geografia e Estatística - IBGE), used to retrieve the geographic coordinates of each municipality. Later used to define the closest weather station to each occupational accident location.



1.1.2. /occupational accidents/



This folder contains the occupational accident records obtained from the Brazilian Notifiable Diseases Information System (Sistema de Informação de Agravos de Notificação - SINAN). There are two zip folders within, one with the .csv data collected from SINAN divided by years, from 2006 to 2024, and the other includes a compilated version, with all the data from 2006 and 2024 in a single .csv, and another .csv with a simplified version, keeping only the relevant variables to use in the process of collecting the weather variables. Along with the datasets, there is a data dictionary explaining the variables, based on the official data dictionary from SINAN.

&nbsp;	

1.1.3. /weather data/



This folder contains the climatic variables collected by automatic weather station located across Brazil. The data is provided by the National Meteorology Institute (Instituto Nacional de Meteorologia - INMET). We used both daily and hourly meteorological data. Both are available in its raw version, along with a data dictionary for each case, as some variables change. We also provided a catalogue of weather stations available for each year, with information regarding their name, code, and geographical coordinates, which are needed further to combine with the occupational accident records.



The data in the raw data folder are presented as the original version.



1.2. imputed data/

Contains the meteorological datasets after data imputation using the Amelia package. Both daily and hourly climate data were processed to fill missing observations while preserving the temporal and spatial structure of the original data. The imputed datasets are organized in hourly and daily folders, each divided in folders for each year. The data dictionary presented in the weather data folder can be used for this dataset as well.



1.3. compiled database/

Includes the final compiled database that integrates occupational accident data with meteorological variables. This dataset represents the main analytical product, enabling statistical and epidemiological analyses of the relationships between climatic conditions and occupational health outcomes. There is one data dictionary providing a description of the occupational accident records along with the weather data collected for each record.



All datasets are stored in CSV format, and data dictionaries are provided as PDF documents to describe the variables and their corresponding metadata.



2\. r scripts/



This folder includes all R scripts developed for data preparation and processing. Each script is designed for a specific step of the workflow, including the imputation of daily and hourly climatic datasets and the compilation of the final integrated database. We included commentary and explanation inside each script to guide its use.



The compilation of the final database integrating work accident data with the meteorological data involved a critical spatial-temporal matching process, designed to assign the most relevant climate station data to each accident record. The matching process was executed based on the following steps:



I- Geographic Coordinates Retrieval: The latitude and longitude coordinates for the municipality of each accident were retrieved from the IBGE municipal data.

II- Distance Calculation: The Haversine formula was employed to calculate the great-circle distance between the geographic center of the accident municipality and all available INMET meteorological stations.

III- Proximity Vector: A vector of meteorological stations, ordered from the closest to the farthest, was generated for each accident municipality.



The assignment of meteorological data to an accident record followed a sequential, proximity-based search:



I- The algorithm iterates through the ordered proximity vector of stations, starting with the closest one.

II- For the current station, the script verifies if meteorological records exist for the specific date of the accident.

III- If the record is found and is not empty, the meteorological variables from that station are assigned to the accident record, and the search terminates for that specific accident.

IV- If the record is missing or empty, the search proceeds to the next closest station in the vector.

V- The search is strictly limited by a maximum distance threshold of 150 kilometers between the accident municipality and the meteorological station. If no suitable record is found within this radius, the meteorological data for that accident is treated as missing in the final compiled database.



This methodology ensures that the assigned meteorological data is both temporally relevant (matching the accident date) and spatially proximate (within a 150 km radius), maintaining the scientific rigor of the analysis.



All scripts were developed and executed in RStudio.



Purpose and Use



The repository serves as a structured foundation for research on the intersection of occupational health and climate science in Brazil. By consolidating meteorological and health surveillance data, this database supports empirical analyses of how climatic variations—and, by extension, climate change—affect workers’ health outcomes.



Notes



All data included here comply with ethical and legal requirements for secondary data use in research. Sensitive personal identifiers have been removed or anonymized according to Brazilian data protection standards.


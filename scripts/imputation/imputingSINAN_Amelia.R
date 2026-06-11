# This R Script is a work done by Guilherme Neto Ferrari (ORCID: https://orcid.org/0000-0001-6198-2616)
# With the help of Dr Gislaine Camila Lapasini Leal and Dr Paulo César Ossani
# The database was created as part of his Computer Science Doctorate Degree in the State University of Maringá, Brazil
# The database represents an innovative resource to investigate the relationship between climate change and occupational health in Brazil
# The usage of these scripts or data should cite the repository (10.5281/zenodo.17458229)

# ---
# Needed libraries
# ---

library(dplyr)      # For data manipulation
library(foreach)    # For parallel processing loop
library(doParallel) # For registering and using parallel backend

# Detects and registers the number of cores
num_cores <- parallel::detectCores() - 1
cl <- makeCluster(num_cores)
registerDoParallel(cl)

# Set the working directory
setwd(".../data/raw data/")

# ---
# Function to calculate the Great-circle distance (Haversine formula) between two points on Earth.
#
# Arguments:
#   latitude1, longitude1: Coordinates of the first point (e.g., the accident).
#   latitude2, longitude2: Coordinates of the second point (e.g., the weather station).
# ---
earth_dist <- function(latitude1, longitude1, latitude2, longitude2) {
  
  r = 6371 # Approximate radius of the Earth in kilometers
  
  deg_rad = pi / 180 # Conversion factor from degrees to radians
  
  # Convert coordinate differences to radians
  rad_Lat = deg_rad * (latitude2  - latitude1)
  rad_Lon = deg_rad * (longitude2 - longitude1)
  
  # Apply the Haversine formula
  a = sin(rad_Lat / 2) * sin(rad_Lat / 2) + cos(deg_rad * latitude1) * cos(deg_rad * latitude2) * sin(rad_Lon / 2) * sin(rad_Lon / 2)
  
  # Calculate the distance
  distance = 2 * r * asin(sqrt(a))
  
  return(distance)
  
}

# --- Data Loading and Preparation ---

# Load municipal coordinates data (IBGE data source) - Located in /raw data/municipalities
municipal_coords_df = read.csv("list_municipalities_IBGE.csv",sep=";",head=T)

# Truncate the municipality ID to the first 6 characters
municipal_coords_df$municipio <- substring(municipal_coords_df$municipio,1,6)

# Load accident data (with latitude and longitude) - Located in /raw data/occupational accidents/all SINAN records
accident_data_raw <- read.csv("simplified_all2006to2024data.csv", sep=";",head=T)

# Merge accident data with municipal coordinates based on municipality ID
accident_data_merged <- merge(accident_data_raw, municipal_coords_df[, c("municipio", "lat", "lon")],
                              by.x = "ID_MUNICIP", by.y = "municipio", all.x = TRUE)

# Load the catalog of weather stations - locate in /raw data/weather data
station_catalog_df <- read.csv("catalogue of weather stations.csv",sep=";",head=T)

# Define the range of years to process
years <- 2006:2024

# Define the number of parts for parallel processing - It should be customizable according to your needs
parts <- 10

# --- Main Processing Loop (Parallelized by Year) ---

for(year_n in years){
  # Filter accident data for the current year (Note: '!data0[,3] != n,' keeps all rows where column 3 IS the year_n)
  data_year <- accident_data_merged[!accident_data_merged[,3] != year_n,]
  print(year_n)
  
  total_rows <- nrow(data_year) # Total number of records (accidents) for the year
  
  # Calculate the size of each part for parallel processing
  part_size <- ceiling(total_rows / parts)
  
  # Parallel loop using foreach
  foreach(pt = 1:parts, .packages = c("utils","dplyr")) %dopar% {
    # Calculate start and end indices for the current part
    start_index <- (pt - 1) * part_size + 1
    end_index <- min(pt * part_size, total_rows)
    
    # Subset the data for the current processing part
    data_subset <- data_year[start_index:end_index, ]
    
    # Define the names for the new columns
    new_col_names <- c("STATION_CODE", 
                       "DISTANCE_KM", 
                       "PRECIPITATION", 
                       "ATMOSPHERIC PRESSURE", 
                       "DRY BULB TEMPERATURE", 
                       "DEW POINT TEMPERATURE", 
                       "RELATIVE HUMIDITY", 
                       "WIND SPEED", 
                       "STATION_RANK")
    
    # Pre-allocate the columns (from index 8 to 17, a total of 10 new columns)
    # Ensures that data_subset has 17 columns before starting to fill them.
    data_subset[, (ncol(data_subset) + 1):(ncol(data_subset) + 9)] <- NA
    
    names(data_subset)[8:16] <- new_col_names
    
    num_proc_rows <- nrow(data_subset)
    
    # Loop through each accident record in the subset
    for(i in 1:num_proc_rows) {
      
      # Extract accident coordinates (replacing comma decimal with dot)
      lat1 <- as.numeric(sub(",", ".", data_subset[i,6])) # Accident latitude
      lon1 <- as.numeric(sub(",", ".", data_subset[i,7])) # Accident longitude
      
      min_distances <- NULL
      
      # Filter station catalog for the current year
      stations_year <- station_catalog_df[station_catalog_df[,6] == year_n,]
      
      # Loop through each station available in the current year
      for(k in 1:nrow(stations_year)) {
        
        station_code <- stations_year[k,3]
        
        # Extract station coordinates (replacing comma decimal with dot)
        lat2 <- as.numeric(sub(",", ".", stations_year[k,4])) # Station latitude
        lon2 <- as.numeric(sub(",", ".", stations_year[k,5])) # Station longitude
        
        # Calculate the distance between accident and station
        result <- earth_dist(lat1, lon1, lat2, lon2)
        
        # Store the distance result
        min_distances <- rbind(min_distances, result)
      }
      
      # Sort the distances in ascending order
      distances_sorted <- sort(min_distances)
      iterator <- 1
      
      data_filled <- FALSE
      
      # Loop through sorted distances to find the closest valid weather data
      while (iterator <= length(distances_sorted)) {
        
        # Check if the closest station is within a 500 km radius
        if(distances_sorted[iterator] < 500){
          
          print(iterator)
          # Find the index/position of the closest city (station) in the original distance list
          closest_index <- which(min_distances %in% distances_sorted[iterator])
          
          # Extract accident date and time
          accident_date_raw <- data_subset[i,4] # Accident date (raw format)
          # Convert raw date (e.g., YYYYMMDD) to Date object
          date_accident <- as.Date(paste(substring(accident_date_raw,7,8),substring(accident_date_raw,5,6),substring(accident_date_raw,1,4),sep="/"),"%d/%m/%Y")
          hour_accident <- data_subset[i,5] # Accident hour
          
          # Check if the accident hour is available (i.e., hourly data is needed)
          if(!is.na(hour_accident)){
            # Hourly Data Processing Block
            
            base_path <- ".../data/raw data/weather data/hourly/"
            
            year_folder_path <- file.path(base_path, year_n)
            
            # Search for the hourly climate file associated with the closest station code
            file_name <- list.files(path = year_folder_path,
                                    pattern = paste("_", stations_year[closest_index,3], "_*.*", sep = ""), full.names = F)
            
            # Read the hourly data file with error handling
            hourly_data <- tryCatch({
              read.csv(paste0(year_folder_path,"/", file_name), sep = ",", head = TRUE, dec = ",", stringsAsFactors = FALSE, fileEncoding = "ISO-8859-1")
            }, error = function(e) {
              message("Error reading climate file: ", file_name)
              return(NULL)
            })
            
            # Convert climate data columns (3 to 8) to numeric, handling comma decimal separators
            hourly_data <- hourly_data %>%
              mutate(across(3:8, ~ as.numeric(gsub(",", ".", .))))
            
            # If file reading failed, skip to the next closest station
            if (is.null(hourly_data)) {
              iterator <- iterator + 1
              next
            }
            
            # Replace missing value code (-9999) with NA
            hourly_data[hourly_data == -9999] <- NA
            
            # Filter data by matching accident date and hour
            data_day <- hourly_data[as.Date(hourly_data[,1]) == date_accident,]
            # Extract hour from the second column and match with accident hour
            data_day <- data_day[as.integer(substr(as.character(data_day[,2]),1,2)) == hour_accident,]
            
            # Check if matching hourly data was found
            if (nrow(data_day) > 0){
              
              day_row <- data_day[1, 3:8]
              
              # Check if all climate fields for the matched date/hour are valid (not NA)
              if(all(!is.na(day_row))){
                # Fill the accident record with weather data from the closest valid station
                data_subset[i, "STATION_CODE"] <- stations_year[closest_index,3] # Weather station code
                data_subset[i, "DISTANCE_KM"] <- distances_sorted[iterator] # Distance to weather station
                data_subset[i,10:15] <- data_day[,3:8] # Weather data
                data_subset[i, "STATION_RANK"] <- iterator # Rank of the station by distance
                data_filled <- TRUE
                break # Exit the while loop since data was successfully filled
                
              }else{
                # Data found but has NA/invalid values, skip to next closest station
              }
              
            } else {
              message("Invalid day or hour in file")
              iterator <- iterator + 1
            }
          }else{
            # Daily Data Processing Block (if accident hour is missing)
            
            base_path <- ".../data/raw data/weather data/daily/"
            
            year_folder_path <- file.path(base_path, year_n)
            
            # Search for the daily climate file associated with the closest station code (removing spaces from code)
            file_name <- list.files(path = year_folder_path,
                                    pattern = paste("_", gsub(" ", "",stations_year[closest_index,3]), "_*.*", sep = ""), full.names = F)
            
            # Read the daily data file with error handling
            daily_data <- tryCatch({
              read.csv(paste0(year_folder_path,"/", file_name), sep = ",", head = TRUE, dec = ",", stringsAsFactors = FALSE, fileEncoding = "ISO-8859-1")
            }, error = function(e) {
              message("Error reading climate file: ", file_name)
              return(NULL)
            })
            
            # If file reading failed, skip to the next closest station
            if (is.null(daily_data)) {
              iterator <- iterator + 1
              next
            }
            
            # Replace string "null" with the missing value code
            daily_data[daily_data == "null"] <- -9999
            
            # Replace missing value code (-9999) with NA
            daily_data[daily_data == -9999] <- NA
            
            # Convert climate data columns (2 to 7) to numeric, handling comma decimal separators
            daily_data[,2:7] <- lapply(daily_data[,2:7], function(x) as.numeric(gsub(",", ".", x)))
            
            
            # Filter data by matching accident date
            data_day <- daily_data[as.Date(daily_data[,1]) == date_accident,]
            
            # Check if matching daily data was found
            if (nrow(data_day) > 0){
              # Check if all climate fields for the matched date are valid (not NA)
              if(all(!is.na(data_day[1, 2:7]))){
                # Fill the accident record with weather data from the closest valid station
                data_subset[i, "STATION_CODE"] <- station_catalog_df[closest_index,3] # Weather station code
                data_subset[i, "DISTANCE_KM"] <- distances_sorted[iterator] # Distance to weather station
                data_subset[i,10:15] <- data_day[,2:7] # Weather data (Note: 6 columns being copied to 7 slots 10:16)
                data_subset[i, "STATION_RANK"] <- iterator
                data_filled <- TRUE
                break # Exit the while loop
              }else{
                print("Empty values")
                iterator <- iterator + 1
              }
            }else{
              print("Invalid day or hour")
              iterator <- iterator + 1
            }
            iterator <- iterator + 1
          }
          iterator <- iterator + 1
        }else{
          # Distance is >= 500 km, no need to check further stations in this iteration
          iterator <- iterator + 1
        }
      }
      
      # If the loop finished without finding valid data, fill the record with NA
      if (!data_filled) {
        data_subset[i,8:16] <- NA
      }
    }
    
    # Define the output file path for the current part - EDIT IT
    output_filename <- file.path(".../", paste0("SINAN_IMPUTED", year_n, paste0("part_"), pt, ".csv"))
    # Write the processed data part to a CSV file (using semicolon as separator)
    write.table(file = output_filename, data_subset, sep=";", dec=",", row.names = FALSE)
  }
  year_n = year_n+1 # Increment year_n (though the for loop handles the main iteration)
}

# Stop the parallel cluster
stopCluster(cl)
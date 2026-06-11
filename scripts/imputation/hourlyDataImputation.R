# This R Script is a work done by Guilherme Neto Ferrari (ORCID: https://orcid.org/0000-0001-6198-2616)
# With the help of Dr Gislaine Camila Lapasini Leal and Dr Paulo César Ossani
# The database was created as part of his Computer Science Doctorate Degree in the State University of Maringá, Brazil
# The database represents an innovative resource to investigate the relationship between climate change and occupational health in Brazil
# The usage of these scripts or data should cite the repository (10.5281/zenodo.17458229)

# ---
# Needed libraries
# ---

library(Amelia)   # For Multiple Imputation (Amelia II)
library(dplyr)    # For data manipulation
library(lubridate)# For date and time manipulation
library(stringr)  # For string operations (e.g., regex matching)

# ---
# Function to perform robust multiple imputation using Amelia
#
# Arguments:
#   data_df: The data frame to be imputed.
#   m: The number of imputations to perform (default is 5).
#   timeout_seconds: Timeout limit in seconds for the imputation process (default is 300).
# ---
robust_impute <- function(data_df, m = 5, timeout_seconds = 300) {
  # Use SYSTEM TIMEOUT to force stop the imputation if it takes too long
  result <- tryCatch({
    # Set the time limit for the imputation function call
    setTimeLimit(timeout_seconds, transient = TRUE)
    
    # Perform multiple imputation using Amelia II
    imputation_result <- Amelia::amelia(
      data_df, 
      m = m,                     # Number of imputations
      p2s = 1,                   # Controls when to stop if convergence problems occur
      ts = "time_index",         # Specify the time series variable for imputation
      idvars = "datetime",       # Variables to exclude from the imputation model (fixed effects)
      polytime = 1,              # Order of the polynomial for time trend (linear)
      empri = 0.1 * nrow(data_df) # Empirical prior constraint on the correlation matrix
    )
    
    setTimeLimit()  # Remove the time limit after successful completion
    return(imputation_result)
  }, error = function(e) {
    setTimeLimit()  # Remove the time limit in case of error
    # Check if the error was caused by a timeout
    if(grepl("timeout", e$message)) {
      cat("   ⏰ Timeout - file with infinite collinearity detected\n")
    }
    return(NULL) # Return NULL if imputation fails or times out
  })
  
  return(result)
}

# ---
# Function to combine multiple imputation results by averaging the imputed data
#
# Arguments:
#   imputation_list: A list of imputed data frames (usually from the 'imputations' element of the amelia result).
# ---
combine_imputations <- function(imputation_list) {
  # Check if the list is empty
  if (length(imputation_list) == 0) return(NULL)
  
  # Initialize the average with the first imputed dataset
  average_imputed <- imputation_list[[1]]
  
  # Sum the values of the subsequent imputed datasets (excluding the first column, which is usually 'datetime')
  for (i in 2:length(imputation_list)) {
    # Only sum the non-ID columns
    average_imputed[, -1] <- average_imputed[, -1] + imputation_list[[i]][, -1]
  }
  
  # Calculate the mean by dividing the sum by the total number of imputations
  average_imputed[, -1] <- average_imputed[, -1] / length(imputation_list)
  return(average_imputed)
}

# ---
# Main script execution
# ---

# Base path for input data files - EDIT IT
base_path <- ".../data/raw data/weather data/hourly/"
# Define the range of years to process
years <- 2006:2024

# Loop through each year
for (year_n in years){
  
  # Construct the full path for the current year's folder
  year_folder_path <- file.path(base_path, year_n)
  
  # Set the working directory to the current year's folder
  setwd(year_folder_path)
  
  # List all files ending with .csv or .CSV in the current directory
  data_files <- list.files(pattern = "\\.csv$|\\.CSV$", full.names = TRUE)
  
  # Note: The original code had a fixed index for 'arquivo', but the loop below overwrites it. 
  # Retaining the original structure for exact translation, but commenting it out:
  # data_file <- data_files[20]
  
  # Loop through each data file found
  for (data_file in data_files){
    
    # Use regular expression to extract metadata (station info) from the filename
    file_info <- stringr::str_match(
      basename(data_file),
      "(?i)INMET_(N|NE|S|SE|CO)_([A-Z]{2})_([A-Z]\\d{3})_(.+?)_\\d{2}-\\d{2}-\\d{4}.*?(\\d{4})\\.csv"
    )
    
    # Extract the parts to create the new standardized filename
    # info[6]: Year (YYYY), info[4]: Station ID, info[2]: Region (N/NE/S/SE/CO), 
    # info[3]: State, info[5]: Station Name
    new_filename_base <- paste0(file_info[6],"_",file_info[4],"_",file_info[2],"_",file_info[3],"_",file_info[5])
    cat("Processing:", new_filename_base, "\n")
    
    # Use tryCatch to handle potential errors during file reading or processing
    tryCatch({
      # Read the CSV file. Skip 8 lines of header, use semicolon as separator, 
      # comma as decimal separator, and specify ISO-8859-1 encoding.
      original_data <- read.csv(data_file, skip = 8, sep = ";", head = T, dec = ",", stringsAsFactors = T, fileEncoding = "ISO-8859-1")
      
      # Select specific columns (by index) from the read data
      original_data = original_data[c(1,2,3,4,8,9,16,19)]
      
      # Standardize the date format if the first date column contains a hyphen (e.g., YYYY-MM-DD)
      if(grepl("-", original_data[1,1])) {
        original_data[,1] <- format(as.Date(original_data[,1], format = "%Y-%m-%d"), "%Y/%m/%d")
      }
      
      # Prepare data for datetime conversion
      data_temp <- original_data
      # Extract only the hour part from the second column
      data_temp[,2] <- substr(data_temp[,2],1,2)
      # Convert the date column to character for concatenation
      data_temp[,1] <- as.character(data_temp[,1])
      # Pad the hour column with a leading zero if it has only one digit
      data_temp[,2] <- ifelse(nchar(data_temp[,2]) == 1, paste0("0", data_temp[,2]), data_temp[,2])
      
      # Create a POSIXct datetime object by pasting date and hour, formatted as YYYY/MM/DD HH
      datetime <- as.POSIXct(paste(data_temp[,1], sprintf("%02s", data_temp[,2])), format = "%Y/%m/%d %H", tz = "UTC")
      # Remove the original date and hour columns
      data_temp <- data_temp[,-c(1,2)]
      # Combine the new datetime column with the remaining data
      data_df <- data.frame(datetime, data_temp)
      
      # Replace the INMET missing value code (-9999) with R's NA
      data_df[data_df == -9999] <- NA
      # Create a time index variable for use in Amelia
      data_df$time_index <- 1:nrow(data_df)
      
      # Prepare data for final output format (pre-imputation)
      data_df_temp <- data_df %>%
        mutate(
          day = as.Date(datetime),         # Extract date part
          hour = format(datetime, "%H")   # Extract hour part
        )
      
      # Reorder columns: day, hour, followed by all other columns (excluding original ID/time vars)
      final_data_pre_impute <- data_df_temp[, c("day", "hour", setdiff(names(data_df_temp), c("day", "hour", "datetime", "time_index")))]
      
      # Define the output folder path - EDIT IT
      output_folder <- paste0("../",year_n)
      
      # Create the output folder if it doesn't exist
      if (!dir.exists(output_folder)) dir.create(output_folder, recursive = TRUE)
      
      cat("   📈 Dataset with", nrow(data_df), "observations\n")
      
      # Check if any missing values exist in the data columns (excluding ID/time index)
      if (any(is.na(data_df[, 3:8]))) {
        
        # Identify columns that are entirely NA or contain only a single unique non-NA value (constant columns)
        # Amelia may fail with such columns if they are highly collinear
        constant_cols <- names(data_df)[sapply(data_df, function(x) all(is.na(x)) || length(unique(na.omit(x))) == 1)]
        # Select data for imputation, excluding the constant columns
        data_to_impute <- data_df[, !(names(data_df) %in% constant_cols)]
        
        # Check if enough non-constant columns remain for imputation
        if(ncol(data_to_impute) < 3){
          cat("   ⏭️  Skipping - too few columns after removing constants\n")
          # Save the original (unimputed) data with the final structure
          csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
          write.csv(data_df, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
          next
        }
        
        # Perform robust imputation
        imputation_result <- robust_impute(data_to_impute, m = 5, timeout_seconds = 120)
        # Extract the list of imputed datasets
        imputation_list <- if (!is.null(imputation_result)) imputation_result$imputations else NULL
        
        # Handle case where imputation failed (e.g., timeout or error)
        if (is.null(imputation_list)) {
          cat("   ❌ Imputation failed - skipping file\n")
          # Save the original (unimputed) data with the final structure
          csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
          write.csv(final_data_pre_impute, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
          next
        }
        
        # Combine the imputations by averaging the values
        average_imputed <- combine_imputations(imputation_list)
        
        # Handle case where combination failed
        if (is.null(average_imputed)) {
          cat("   ❌ Error combining imputations\n")
          next
        }
        
        # Re-attach the constant columns to the averaged imputed data if they were removed
        if (length(constant_cols) > 0) {
          # Select the constant columns and their values (keeping structure)
          constant_values <- data_df[, constant_cols, drop = FALSE]
          # Bind the constant columns back
          average_imputed <- cbind(average_imputed, constant_values)
          # Ensure columns are in the original order
          average_imputed <- average_imputed[, names(data_df)]
        }
        
        # Remove the 'time_index' column which is no longer needed
        imputed_values <- average_imputed[,-8] 
        
        # Prepare the imputed data for the final output format (day, hour, vars)
        final_imputed_data_temp <- imputed_values %>%
          mutate(
            day = as.Date(datetime),
            hour = format(datetime, "%H")
          ) %>%
          # Select day, hour, all other columns, and explicitly remove 'datetime'
          select(day, hour, everything(), -datetime)
        
        # Reorder columns to the final desired structure (day, hour, data variables)
        final_imputed_data <- final_imputed_data_temp[, c("day", "hour", setdiff(names(final_imputed_data_temp), c("day", "hour", "datetime")))]
        
        # Construct the final CSV filename and path
        csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
        # Write the final imputed data to CSV
        write.csv(final_imputed_data, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
        cat("   ✅ File saved (with imputation)\n")
        
      } else {
        # --- DATASET IS ALREADY COMPLETE - SAVE DIRECTLY ---
        cat("   💾 Complete dataset - saving without imputation\n")
        # Construct the final CSV filename and path
        csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
        # Write the complete original data (in the final structure) to CSV
        write.csv(final_data_pre_impute, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
      }
    }, error = function(e) {
      # Catch and report any errors that occur during the file processing block
      cat("   ❌ Processing error:", e$message, "\n")
    })
  }
}

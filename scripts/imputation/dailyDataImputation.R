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
# This version is tailored for daily data, using 'Data.Medicao' as the time series variable.
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
      ts = "Measurement.Date",   # Specify the time series variable (the date column)
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
  
  # Sum the values of the subsequent imputed datasets (excluding the first column, which is the time variable)
  for (i in 2:length(imputation_list)) {
    # Only sum the non-ID/time columns
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
base_path <- ".../data/raw data/weather data/daily/"
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
  
  # Loop through each data file found
  for (data_file in data_files){
    
    # Use regular expression to extract metadata (station ID and year) from the filename
    # info[2]: Station ID (AXXX), info[3]: Start Year (YYYY)
    file_info <- stringr::str_match(
      basename(data_file),
      "(?i)^dados_([A-Z]\\d{3})_D_(\\d{4})-\\d{2}-\\d{2}_\\d{4}-\\d{2}-\\d{2}\\.csv$"
    )
    
    # Create the new standardized filename base: Year_StationID
    new_filename_base <- paste0(file_info[3],"_",file_info[2])
    cat("Processing:", new_filename_base, "\n")
    
    # Use tryCatch to handle potential errors during file reading or processing
    tryCatch({
      # Read the CSV file. Skip 10 lines of header, use semicolon as separator, 
      # comma as decimal separator, and specify ISO-8859-1 encoding.
      data_df <- read.csv(data_file, skip = 10, sep = ";", head = TRUE, dec = ",", stringsAsFactors = FALSE, fileEncoding = "ISO-8859-1")
      # Select specific columns (by removing indices 5, 7, 9, 10, 12)
      data_df = data_df[,-c(5,7,9,10,12)]
      
      # Replace string "null" with the INMET missing value code
      data_df[data_df == "null"] <- -9999
      
      # Replace INMET missing value code (-9999) with R's NA
      data_df[data_df == -9999] <- NA
      
      # Convert data columns (indices 2 to 7) to numeric, replacing comma decimal separator with dot
      data_df[,2:7] <- lapply(data_df[,2:7], function(x) as.numeric(gsub(",", ".", x)))
      
      # Convert the date column (named "Data.Medicao" in the imported data) to Date format
      data_df$Data.Medicao = as.Date(data_df$Data.Medicao)
      # Rename the date column for translation consistency with the previous script,
      # though the ts argument in amelia will still use the original name for consistency.
      # Renaming here for clarity in the rest of the script.
      names(data_df)[names(data_df) == "Data.Medicao"] <- "Measurement.Date"
      
      # Define the output folder path - EDIT IT
      output_folder <- paste0("...",year_n)
      
      # Create the output folder if it doesn't exist
      if (!dir.exists(output_folder)) dir.create(output_folder, recursive = TRUE)
      
      cat("   📈 Dataset with", nrow(data_df), "observations\n")
      
      # Check if any missing values exist in the data columns (indices 2 to 7)
      if (any(is.na(data_df[, 2:7]))) {
        
        # Identify columns that are entirely NA or contain only a single unique non-NA value (constant columns)
        constant_cols <- names(data_df)[sapply(data_df, function(x) all(is.na(x)) || length(unique(na.omit(x))) == 1)]
        # Select data for imputation, excluding the constant columns
        data_to_impute <- data_df[, !(names(data_df) %in% constant_cols)]
        
        if(!is.data.frame(data_to_impute) || ncol(data_to_impute) < 3){
          cat("   ⏭️  Skipping - too few columns after removing constants\n")
          # Save the original (unimputed) data
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
          # Save the original (unimputed) data
          csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
          write.csv(data_df, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
          cat("   ✅ File saved (original) \n")
          next
        }
        
        # Combine the imputations by averaging the values
        average_imputed <- combine_imputations(imputation_list)
        
        # Handle case where combination failed
        if (is.null(average_imputed)) {
          cat("   ❌ Error combining imputations\n")
          # Save the original (unimputed) data
          csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
          write.csv(data_df, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
          cat("   ✅ File saved (original) \n")
          next
        }
        
        # Re-attach the constant columns to the averaged imputed data if they were removed
        if (length(constant_cols) > 0) {
          # Select the constant columns and their values
          constant_values <- data_df[, constant_cols, drop = FALSE]
          # Bind the constant columns back
          average_imputed <- cbind(average_imputed, constant_values)
          # Ensure columns are in the original order
          average_imputed <- average_imputed[, names(data_df)]
        }
        
        # Construct the final CSV filename and path
        csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
        # Write the final imputed data to CSV
        write.csv(average_imputed, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
        cat("   ✅ File saved (with imputation)\n")
        
      } else {
        # --- DATASET IS ALREADY COMPLETE - SAVE DIRECTLY ---
        cat("   💾 Complete dataset - saving without imputation\n")
        # Construct the final CSV filename and path
        csv_filename <- file.path(output_folder, paste0(new_filename_base, ".csv"))
        # Write the complete original data to CSV
        write.csv(data_df, csv_filename, row.names = FALSE, fileEncoding = "ISO-8859-1")
        cat("   ✅ File saved (original) \n")
      }
    }, error = function(e) {
      # Catch and report any errors that occur during the file processing block
      cat("   ❌ Processing error:", e$message, "\n")
    })
  }
}

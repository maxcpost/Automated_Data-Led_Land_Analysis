import pandas as pd
import time
import os
import glob
import traceback
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
import shutil
import re
import argparse
import math
import sys
import json
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from tqdm import tqdm
import requests
import random
import numpy as np

# Define the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Rich console for output
console = Console()

# Path to the directory for storing MCDC files
MCDC_DIR = "database/MCDC"

# Global verbose flag that will be set via command-line arguments
VERBOSE = False

# Define the columns to keep in the master CSV (all radii will be added)
KEEP_COLUMNS = [
    'TotPop', 'Age0_4', 'Age5_9', 'Age10_14', 'Age15_19', 'Age20_24', 'Age25_34', 
    'Age35_44', 'Age45_54', 'Age55_59', 'Age60_64', 'Age65_74', 'Age75_84', 'Over85', 
    'TotHHs', 'HHInc0', 'HHInc10', 'HHInc15', 'HHInc25', 'HHInc35', 'HHInc50', 
    'HHInc75', 'HHInc100', 'HHInc150', 'HHInc200', 'MedianHHInc', 'AvgHHInc', 
    'InKindergarten', 'InElementary', 'InHighSchool', 'InCollege', 'Disabled', 
    'DisabledUnder18', 'NonInst18_64', 'Disabled18_64', 'NonInstOver65', 'DisabledElder', 
    'TotHUs', 'OccHUs', 'OwnerOcc', 'RenterOcc', 'AvgOwnerHHSize', 'AvgRenterHHSize', 
    'VacHUs', 'VacantForSale', 'VacantForRent', 'VacantSeasonal', 'TotalOwnerUnits', 
    'OwnerVacRate', 'TotalRentalUnits', 'RenterVacRate', 'PersonsInOwnerUnits', 
    'PersonsInRenterUnits', 'MobileHomes', 'MobileHomesPerK', 'HvalUnder50', 'Hval50', 
    'Hval100', 'Hval150', 'Hval200', 'Hval300', 'Hval500', 'HvalOverMillion', 
    'HvalOver2Million', 'MedianHValue', 'MedianGrossRent'
]

# Generate all column names with radii
ALL_KEEP_COLUMNS = []
for base_col in KEEP_COLUMNS:
    for radius in [5, 10, 15, 20, 25]:
        ALL_KEEP_COLUMNS.append(f"{base_col}_{radius}")

def log(message, always_print=False):
    """Print message only if verbose mode is on or if always_print is True"""
    if VERBOSE or always_print:
        print(message)

def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)

def read_master_csv():
    """
    Read the master CSV file.
    
    Returns:
        DataFrame containing the master CSV data, or None if the file doesn't exist or can't be read
    """
    master_csv_path = os.path.join("database", "master.csv")
    try:
        if os.path.exists(master_csv_path):
            return pd.read_csv(master_csv_path)
        else:
            print(f"Master CSV file not found at {master_csv_path}")
            return None
    except Exception as e:
        print(f"Error reading master CSV file: {e}")
        return None

def find_existing_csv(latitude, longitude):
    """Find an existing CSV file for the given coordinates."""
    # Create the pattern for matching files
    pattern = os.path.join(MCDC_DIR, f"{latitude}-{longitude}-*.csv")
    
    # Find all matching files
    matching_files = glob.glob(pattern)
    
    if matching_files:
        # If multiple files exist, return the most recent one
        return max(matching_files, key=os.path.getctime)
    
    return None

def extract_data_from_csv(csv_path, verbose=False):
    """
    Extract data from a CSV file downloaded from MCDC.
    
    Args:
        csv_path (str): Path to the CSV file
        verbose (bool): Print verbose output
        
    Returns:
        dict: Dictionary with census data
    """
    if verbose:
        print(f"Extracting data from {csv_path}")
    
    try:
        # Try utf-8 encoding first
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            if verbose:
                print("Successfully read CSV with utf-8 encoding")
        except UnicodeDecodeError:
            # If utf-8 fails, try latin1
            df = pd.read_csv(csv_path, encoding='latin1')
            if verbose:
                print("Successfully read CSV with latin1 encoding")
        
        if verbose:
            print(f"CSV file has {df.shape[0]} rows and {df.shape[1]} columns")
        
        # Extract data for all radii
        data = {}
        
        # The MCDC CSV typically has columns for each radius
        # Find all unique radius values
        radii = []
        for col in df.columns:
            # Look for columns with radius suffixes like "_5mile"
            for radius in [5, 10, 15, 20, 25]:
                if f"_{radius}mile" in col:
                    if radius not in radii:
                        radii.append(radius)
        
        if verbose:
            print(f"Found data for {len(radii)} radii: {radii}")
        
        # If no radius-specific columns found, check if all data is in a flat format
        if not radii and df.shape[0] > 0:
            # Assume this is a single-radius file
            if verbose:
                print("No radius-specific columns found, assuming flat data format")
            
            # Extract all data from the first row
            for col in df.columns:
                data[col] = df[col].iloc[0]
            
            return data
        
        # Extract data for each radius
        for radius in radii:
            radius_data = {}
            
            # Find all columns for this radius
            for col in df.columns:
                if f"_{radius}mile" in col:
                    # Extract the base column name by removing the radius suffix
                    base_col = col.replace(f"_{radius}mile", "")
                    # Store the data with a radius suffix in the key
                    if df.shape[0] > 0:  # Make sure there's at least one row
                        radius_data[f"{base_col}_{radius}"] = df[col].iloc[0]
            
            # Add this radius's data to the main data dictionary
            data.update(radius_data)
        
        # Look for non-radius specific columns like coordinates
        for col in ['Latitude', 'Longitude', 'sitename', 'period', 'intptlat', 'intptlon']:
            if col in df.columns and df.shape[0] > 0:
                data[col] = df[col].iloc[0]
        
        return data
    
    except Exception as e:
        print(f"Error extracting data from CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_csv(driver, coord, verbose=False):
    """
    Download the CSV file from the results page.
    
    Args:
        driver (WebDriver): The WebDriver instance.
        coord (tuple): The (latitude, longitude) tuple.
        verbose (bool): Whether to print verbose output.
        
    Returns:
        str: The path to the downloaded CSV file, or None if download failed.
    """
    # Find all capsACS files in the Downloads directory
    downloads_dir = os.path.expanduser("~/Downloads")
    existing_files = [f for f in os.listdir(downloads_dir) if f.startswith("capsACS") and f.endswith(".csv")]
    
    if verbose:
        print(f"Found {len(existing_files)} existing capsACS files before download")
    
    # Find CSV links
    max_retries = 3
    csv_links = []
    
    for attempt in range(max_retries):
        try:
            print(f"Looking for CSV links (attempt {attempt+1}/{max_retries})...")
            # Wait for links to be available
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.csv')]"))
            )
            
            csv_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.csv')]")
            if csv_links:
                print(f"Found {len(csv_links)} CSV links")
                break
            else:
                print("No CSV links found, retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"Error finding CSV links (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print("Failed to find any CSV links after all retries")
                return None
            time.sleep(2)
    
    if not csv_links:
        print("No CSV links found")
        return None
    
    # Get unique CSV links
    unique_csv_urls = set()
    for link in csv_links:
        try:
            url = link.get_attribute("href")
            if url and url.endswith(".csv"):
                unique_csv_urls.add(url)
        except Exception as e:
            print(f"Error getting URL from link: {e}")
    
    if verbose:
        print(f"Found {len(csv_links)} total links ({len(unique_csv_urls)} unique CSV links)")
    
    if not unique_csv_urls:
        print("No valid CSV URLs found")
        return None
    
    # Download the first CSV file
    csv_url = list(unique_csv_urls)[0]
    print(f"Downloading CSV from: {csv_url}")
    
    # Use requests to download the file
    download_success = False
    download_attempts = 0
    max_download_attempts = 3
    downloaded_file_path = None
    
    while not download_success and download_attempts < max_download_attempts:
        download_attempts += 1
        try:
            response = requests.get(csv_url, timeout=30)
            if response.status_code == 200:
                # Extract filename from URL
                filename = os.path.basename(csv_url)
                downloaded_file_path = os.path.join(downloads_dir, filename)
                
                # Save the file
                with open(downloaded_file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"Downloaded CSV to: {downloaded_file_path}")
                download_success = True
            else:
                print(f"Failed to download CSV (HTTP {response.status_code}), attempt {download_attempts}/{max_download_attempts}")
                time.sleep(2)
        except Exception as e:
            print(f"Error downloading CSV (attempt {download_attempts}/{max_download_attempts}): {e}")
            time.sleep(2)
    
    if not download_success:
        print("Failed to download CSV after multiple attempts")
        return None
    
    # Wait for the file to be downloaded
    wait_time = 0
    max_wait_time = 30
    while wait_time < max_wait_time:
        if os.path.exists(downloaded_file_path) and os.path.getsize(downloaded_file_path) > 0:
            break
        time.sleep(1)
        wait_time += 1
    
    if wait_time >= max_wait_time:
        print(f"Timed out waiting for CSV file to download")
        return None
    
    # Copy the file to our database directory
    os.makedirs(os.path.join("database", "MCDC"), exist_ok=True)
    dest_path = os.path.join("database", "MCDC", f"mcdc_{coord[0]}_{coord[1]}.csv")
    
    try:
        shutil.copy2(downloaded_file_path, dest_path)
        print(f"Copied CSV to: {dest_path}")
        return dest_path
    except Exception as e:
        print(f"Error copying CSV file: {e}")
        return None

def fetch_data(lat, lng, force=False, verbose=False):
    """
    Fetch data from MCDC website.
    
    Args:
        lat (float): Latitude.
        lng (float): Longitude.
        force (bool): Whether to force fetch data even if it already exists.
        verbose (bool): Whether to print verbose output.
        
    Returns:
        str: Path to the downloaded CSV file, or None if download failed.
    """
    # Check if we already have data for these coordinates
    target_file = os.path.join("database", "MCDC", f"mcdc_{lat}_{lng}.csv")
    
    if os.path.exists(target_file) and not force:
        print(f"Data already exists for coordinates: ({lat}, {lng})")
        return target_file
    
    # Initialize WebDriver
    driver = initialize_webdriver()
    if not driver:
        print("Failed to initialize WebDriver")
        return None
    
    try:
        # Navigate to MCDC website
        print("Navigating to MCDC website...")
        driver.get("https://mcdc.missouri.edu/applications/capsACS.html")
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "latitude"))
        )
        
        print("Page loaded, filling out the form...")
        
        # Fill out the form with separate latitude and longitude fields
        lat_input = driver.find_element(By.ID, "latitude")
        lat_input.clear()
        lat_input.send_keys(f"{lat}")
        
        lng_input = driver.find_element(By.ID, "longitude")
        lng_input.clear()
        lng_input.send_keys(f"{lng}")
        
        # Set all radii
        radii = [5, 10, 15, 20, 25]
        radii_str = " ".join(str(r) for r in radii)
        
        radii_input = driver.find_element(By.ID, "radii")
        radii_input.clear()
        radii_input.send_keys(radii_str)
        
        print(f"Form filled with lat={lat}, lng={lng}, radii={radii_str}")
        
        # Submit the form
        print("Submitting form...")
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Generate report']")
        submit_button.click()
        print("Form submitted")
        
        # Wait for the results page to load
        print("Waiting for results page to load...")
        try:
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.csv')]"))
            )
            print("Results page loaded successfully - found CSV links")
        except Exception as e:
            print(f"Error waiting for results page: {e}")
            # Take a screenshot to debug what's happening
            try:
                screenshot_path = os.path.join(os.path.expanduser("~"), "Downloads", f"error_page_{lat}_{lng}.png")
                driver.save_screenshot(screenshot_path)
                print(f"Saved error screenshot to {screenshot_path}")
                # Print the current page source for debugging
                print("Current page HTML:")
                print(driver.page_source[:500] + "...")  # Print first 500 chars of page source
            except Exception as ss_error:
                print(f"Failed to take screenshot: {ss_error}")
            raise
        
        print("Results page loaded")
        
        # Save a screenshot of the results page
        screenshot_path = os.path.join(os.path.expanduser("~"), "Downloads", f"results_page_{lat}_{lng}.png")
        driver.save_screenshot(screenshot_path)
        print(f"Saved screenshot to {screenshot_path}")
        
        # Download the CSV file
        csv_file = download_csv(driver, (lat, lng), verbose=verbose)
        if not csv_file:
            print("Failed to download CSV file")
            return None
        
        return csv_file
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        traceback.print_exc()
        return None
    
    finally:
        # Close the WebDriver
        print("Closing WebDriver")
        driver.quit()

def update_master_csv(coord, data, verbose=False):
    """
    Update the master CSV file with the census data for the given coordinates.
    
    Args:
        coord (tuple): The (latitude, longitude) tuple.
        data (dict or pd.DataFrame): The census data to add.
        verbose (bool): Whether to print verbose output.
    """
    # Define the master CSV path
    master_csv_path = os.path.join("database", "master.csv")
    master_dir = os.path.dirname(master_csv_path)
    
    # Create directory if it doesn't exist
    os.makedirs(master_dir, exist_ok=True)
    
    # Convert data to DataFrame if it's a dictionary
    if isinstance(data, dict):
        data_df = pd.DataFrame([data])
    else:
        data_df = data
    
    # Check if master CSV exists
    if os.path.exists(master_csv_path):
        # Read existing master CSV
        master_df = pd.read_csv(master_csv_path)
        if verbose:
            print(f"Read existing master CSV with {len(master_df)} rows and {len(master_df.columns)} columns")
        
        # Ensure master_df has Latitude and Longitude columns
        if "Latitude" not in master_df.columns:
            master_df["Latitude"] = None
        if "Longitude" not in master_df.columns:
            master_df["Longitude"] = None
        
        # Find the row with matching coordinates
        lat_col = "Latitude"
        lon_col = "Longitude"
        
        # Find the row with matching coordinates
        row_idx = None
        for idx, row in master_df.iterrows():
            if (pd.notna(row[lat_col]) and pd.notna(row[lon_col]) and 
                abs(float(row[lat_col]) - float(coord[0])) < 0.0001 and 
                abs(float(row[lon_col]) - float(coord[1])) < 0.0001):
                row_idx = idx
                break
        
        # Update existing row or add new row to master CSV
        if row_idx is not None:
            print(f"Found existing row at index {row_idx} for coordinates: {coord}")
            
            # Update the existing row with new data
            for col in data_df.columns:
                if col in master_df.columns:
                    try:
                        # Explicitly convert the value to a compatible type
                        value = data_df[col].iloc[0]
                        # If target column is numeric, ensure proper conversion
                        if pd.api.types.is_numeric_dtype(master_df[col]):
                            if pd.notnull(value):
                                value = pd.to_numeric(value, errors='coerce')
                        master_df.at[row_idx, col] = value
                    except Exception as e:
                        print(f"Warning: Could not update column '{col}': {e}")
        else:
            if verbose:
                print(f"No existing row found for coordinates: {coord}")
            
            # Create a new row with the same columns as master_df
            new_row = pd.Series(index=master_df.columns)
            
            # Set coordinates
            new_row[lat_col] = coord[0]
            new_row[lon_col] = coord[1]
            
            # Set data values
            for col in data_df.columns:
                if col in master_df.columns and col not in [lat_col, lon_col]:
                    new_row[col] = data_df[col].iloc[0]
            
            # Append the new row
            master_df = pd.concat([master_df, pd.DataFrame([new_row])], ignore_index=True)
            if verbose:
                print(f"Added new row for coordinates: {coord}")
    else:
        # Create new master CSV
        if verbose:
            print("Creating new master CSV")
        
        # Initialize with Latitude and Longitude columns
        master_df = pd.DataFrame(columns=["Latitude", "Longitude"])
        
        # Add the data
        new_row = pd.Series()
        new_row["Latitude"] = coord[0]
        new_row["Longitude"] = coord[1]
        
        # Add data values
        for col in data_df.columns:
            if col not in ["Latitude", "Longitude"]:
                new_row[col] = data_df[col].iloc[0]
        
        # Append the new row
        master_df = pd.concat([master_df, pd.DataFrame([new_row])], ignore_index=True)
        if verbose:
            print(f"Added new row for coordinates: {coord}")
    
    # Save the updated master CSV
    master_df.to_csv(master_csv_path, index=False)
    if verbose:
        print(f"Saved master CSV with {len(master_df)} rows and {len(master_df.columns)} columns")

def process_batch(coordinates, force=False, verbose=False, use_mock_data=False):
    """
    Process a batch of coordinates.
    
    Args:
        coordinates (list): List of (latitude, longitude) tuples to process
        force (bool): Whether to force re-fetching data even if it already exists
        verbose (bool): Whether to print verbose output
        use_mock_data (bool): Whether to use mock data instead of fetching real data
    
    Returns:
        int: Number of coordinates successfully processed
    """
    if verbose:
        print(f"Processing batch of {len(coordinates)} coordinates")
    
    processed = 0
    
    for coord in coordinates:
        if verbose:
            print(f"Processing coordinates: {coord}")
        
        # Check if we already have data for these coordinates
        existing_csv = find_existing_csv(coord[0], coord[1])
        
        if existing_csv and not force:
            if verbose:
                print(f"Using existing data for {coord[0]}, {coord[1]} from {existing_csv}")
            
            # Extract data from existing CSV and update master CSV
            # data = extract_data_from_csv(existing_csv, verbose=verbose)
            # update_master_csv(coord, data, verbose=verbose)
            
            # Use the new function to update master CSV with radius-specific data
            update_master_csv_with_radius_data(coord, existing_csv, verbose=verbose)
            
            processed += 1
            continue
        
        if use_mock_data:
            if verbose:
                print(f"Using mock data for {coord[0]}, {coord[1]}")
            
            # Generate mock data and update master CSV
            mock_data = generate_mock_census_data(coord, verbose=verbose)
            csv_path = save_mock_data_to_csv(coord, mock_data, verbose=verbose)
            
            # Update master CSV with mock data
            # update_master_csv(coord, mock_data, verbose=verbose)
            
            # Use the new function to update master CSV with radius-specific data
            update_master_csv_with_radius_data(coord, csv_path, verbose=verbose)
            
            processed += 1
            continue
        
        # If we get here, we need to fetch new data
        if verbose:
            print(f"Fetching new data for {coord[0]}, {coord[1]}")
        
        # Initialize WebDriver
        driver = initialize_webdriver()
        if not driver:
            print("Failed to initialize WebDriver")
            continue
        
        try:
            # Navigate to MCDC website with retry logic and exponential backoff
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    backoff_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                    print(f"Navigating to MCDC website (attempt {attempt+1}/{max_retries}, backoff: {backoff_time}s)...")
                    driver.get("https://mcdc.missouri.edu/applications/capsACS.html")
                    
                    # Wait for the page to load
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.ID, "latitude"))
                    )
                    print("Page loaded successfully")
                    break
                except Exception as e:
                    print(f"Error loading page (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        # If all retries failed, use mock data as fallback
                        print("All retries failed. Falling back to mock data.")
                        driver.quit()
                        mock_data = generate_mock_census_data(coord, verbose=verbose)
                        csv_path = save_mock_data_to_csv(coord, mock_data, verbose=verbose)
                        
                        # Update master CSV with mock data
                        # update_master_csv(coord, mock_data, verbose=verbose)
                        
                        # Use the new function to update master CSV with radius-specific data
                        update_master_csv_with_radius_data(coord, csv_path, verbose=verbose)
                        
                        processed += 1
                        raise Exception("Website unavailable, used mock data instead")
                    time.sleep(backoff_time)  # Wait with exponential backoff before retrying
            
            print("Page loaded, filling out the form...")
            
            # Fill out the form with separate latitude and longitude fields
            lat_input = driver.find_element(By.ID, "latitude")
            lat_input.clear()
            lat_input.send_keys(f"{coord[0]}")
            
            lng_input = driver.find_element(By.ID, "longitude")
            lng_input.clear()
            lng_input.send_keys(f"{coord[1]}")
            
            # Set all radii
            radii = [5, 10, 15, 20, 25]
            radii_str = " ".join(str(r) for r in radii)
            
            radii_input = driver.find_element(By.ID, "radii")
            radii_input.clear()
            radii_input.send_keys(radii_str)
            
            print(f"Form filled with lat={coord[0]}, lng={coord[1]}, radii={radii_str}")
            
            # Submit the form
            print("Submitting form...")
            submit_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Generate report']")
            submit_button.click()
            print("Form submitted")
            
            # Wait for the results page to load
            print("Waiting for results page to load...")
            try:
                WebDriverWait(driver, 45).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.csv')]"))
                )
                print("Results page loaded successfully - found CSV links")
            except Exception as e:
                print(f"Error waiting for results page: {e}")
                # Take a screenshot to debug what's happening
                try:
                    screenshot_path = os.path.join(os.path.expanduser("~"), "Downloads", f"error_page_{coord[0]}_{coord[1]}.png")
                    driver.save_screenshot(screenshot_path)
                    print(f"Saved error screenshot to {screenshot_path}")
                    # Print the current page source for debugging
                    print("Current page HTML:")
                    print(driver.page_source[:500] + "...")  # Print first 500 chars of page source
                except Exception as ss_error:
                    print(f"Failed to take screenshot: {ss_error}")
                raise
            
            print("Results page loaded")
            
            # Save a screenshot of the results page
            screenshot_path = os.path.join(os.path.expanduser("~"), "Downloads", f"results_page_{coord[0]}_{coord[1]}.png")
            driver.save_screenshot(screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")
            
            # Download the CSV file
            csv_path = download_csv(driver, coord, verbose=verbose)
            
            if csv_path:
                # Extract data from the CSV and update master CSV
                # census_data = extract_data_from_csv(csv_path, verbose=verbose)
                # update_master_csv(coord, census_data, verbose=verbose)
                
                # Use the new function to update master CSV with radius-specific data
                update_master_csv_with_radius_data(coord, csv_path, verbose=verbose)
                
                print(f"Successfully processed data for coordinates: {coord}")
                processed += 1
            else:
                print(f"Failed to download CSV for coordinates: {coord}")
        
        except Exception as e:
            print(f"Error processing coordinates {coord}: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Close the WebDriver
            print("Closing WebDriver")
            driver.quit()
    
    return processed

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch census data for coordinates.")
    parser.add_argument("--force", action="store_true", help="Force fetch data even if it already exists.")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of coordinates to process.")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of coordinates to process in each batch.")
    parser.add_argument("--verify", action="store_true", help="Verify existing data.")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed coordinates.")
    parser.add_argument("--start-index", type=int, default=0, help="Index to start processing from.")
    parser.add_argument("--use-mock-data", action="store_true", help="Use mock data instead of fetching from the website.")
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Initialize listings and coordinates
    coordinates = initialize_coordinates()
    
    print(f"Found {len(coordinates)} listings with valid coordinates")
    
    # Apply start index and limit
    if args.start_index > 0:
        coordinates = coordinates[args.start_index:]
        print(f"Starting from index {args.start_index}")
    
    if args.limit:
        coordinates = coordinates[:args.limit]
        print(f"Limiting to {args.limit} listings starting from index {args.start_index}")
    
    print(f"Processing {len(coordinates)} listings")
    
    # Process in batches
    batch_size = args.batch_size
    print(f"Processing in batches of {batch_size}")
    
    # Split coordinates into batches
    batches = [coordinates[i:i + batch_size] for i in range(0, len(coordinates), batch_size)]
    
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)} with {len(batch)} coordinates")
        process_batch(batch, force=args.force, verbose=args.verbose, use_mock_data=args.use_mock_data)

def update_master_census_data(master_df, verbose=False):
    """
    Update the master DataFrame with census data.
    
    Args:
        master_df: Master DataFrame
        verbose: Whether to print verbose output
    
    Returns:
        Updated master DataFrame
    """
    if verbose:
        print("Updating master DataFrame with census data")
    
    # Filter out rows without coordinates
    valid_df = master_df[
        master_df['Latitude'].notna() & 
        master_df['Longitude'].notna()
    ]
    
    if len(valid_df) == 0:
        if verbose:
            print("No valid coordinates found in master DataFrame")
        return master_df
    
    if verbose:
        print(f"Found {len(valid_df)} rows with valid coordinates")
    
    # Initialize WebDriver
    if verbose:
        print("Initializing WebDriver")
    driver = initialize_webdriver()
    if not driver:
        if verbose:
            print("Failed to initialize WebDriver")
        return master_df
    
    try:
        # Process each row
        for idx, row in valid_df.iterrows():
            lat = row['Latitude']
            lng = row['Longitude']
            
            if verbose:
                print(f"Processing coordinates ({lat}, {lng}) at row {idx}")
            
            # Fetch census data
            try:
                csv_path = fetch_data(lat, lng, verbose=verbose)
                
                if csv_path:
                    # Read data from CSV
                    data_df = pd.read_csv(csv_path)
                    
                    # Update master DataFrame with census data
                    for col in data_df.columns:
                        if col not in ['Latitude', 'Longitude']:
                            master_df.loc[idx, col] = data_df.iloc[0][col]
                    
                    if verbose:
                        print(f"Updated row {idx} with census data")
                else:
                    if verbose:
                        print(f"Failed to fetch census data for coordinates ({lat}, {lng})")
            
            except Exception as e:
                if verbose:
                    print(f"Error processing coordinates ({lat}, {lng}): {e}")
                    traceback.print_exc()
    
    finally:
        # Close WebDriver
        if driver:
            driver.quit()
            if verbose:
                print("Closed WebDriver")
    
    return master_df

def process_existing_or_fetch_new(latitude, longitude, row_index, force_fetch=False, verbose=False):
    """
    Process a single coordinate, either loading existing data or fetching new data.
    
    Args:
        latitude: Latitude of the coordinate
        longitude: Longitude of the coordinate
        row_index: Row index in the master CSV
        force_fetch: Whether to force fetching new data even if it already exists
        verbose: Whether to print verbose output
    
    Returns:
        True if successful, False otherwise
    """
    results = process_batch([(latitude, longitude, row_index)], force_fetch, verbose)
    return len(results) > 0 and results[0][2]

def verify_census_data_completeness(master_df, verbose=False):
    """
    Verify that all listings have complete census data.
    
    Args:
        master_df (pandas.DataFrame): Master DataFrame with census data
        verbose (bool): Print verbose output
        
    Returns:
        pandas.DataFrame: DataFrame with listings that have missing census data
    """
    if verbose:
        print("Verifying census data completeness...")
    
    # Filter out rows with missing coordinates
    master_df = master_df.dropna(subset=['Latitude', 'Longitude'])
    
    if verbose:
        print(f"Found {len(master_df)} listings with valid coordinates")
    
    # Define the target radii
    target_radii = [5, 10, 15, 20, 25]
    
    # Define the required columns for each radius
    required_columns = [
        'TotPop', 'MedianAge', 'MedianHHInc', 'AvgHHInc', 'PCI',
        'White1', 'pctWhite1', 'Black1', 'pctBlack1', 'Hispanic',
        'pctHispanic', 'Asian1', 'pctAsian1', 'MedianHValue', 'AvgHValue'
    ]
    
    # Create a list of all required columns with radius suffixes
    all_required_columns = []
    for radius in target_radii:
        for col in required_columns:
            all_required_columns.append(f"{col}_{radius}")
    
    # Check which listings have missing data
    missing_data = []
    
    for _, row in master_df.iterrows():
        missing_columns = []
        
        for col in all_required_columns:
            if col not in master_df.columns or pd.isna(row[col]):
                missing_columns.append(col)
        
        if missing_columns:
            missing_data.append({
                'Latitude': row['Latitude'],
                'Longitude': row['Longitude'],
                'missing_columns': missing_columns
            })
    
    if verbose:
        if missing_data:
            print(f"Found {len(missing_data)} listings with missing census data")
            for item in missing_data[:5]:  # Show first 5 for brevity
                print(f"  Coordinates: ({item['Latitude']}, {item['Longitude']})")
                print(f"  Missing columns: {', '.join(item['missing_columns'][:5])}...")
            if len(missing_data) > 5:
                print(f"  ... and {len(missing_data) - 5} more")
        else:
            print("All listings have complete census data")
    
    # Convert missing_data to DataFrame
    if missing_data:
        return pd.DataFrame(missing_data)
    
    return None

def initialize_webdriver():
    """
    Initialize the WebDriver for browser automation.
    
    Returns:
        webdriver: The initialized WebDriver instance, or None if initialization failed.
    """
    # Try Safari first
    try:
        print("Initializing Safari WebDriver...")
        driver = webdriver.Safari()
        driver.set_page_load_timeout(30)  # Increase timeout to 30 seconds
        print("Safari WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"Failed to initialize Safari WebDriver: {e}")
    
    # Fall back to Chrome if Safari fails
    try:
        print("Falling back to Chrome WebDriver...")
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(30)  # Increase timeout to 30 seconds
        print("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"Failed to initialize Chrome WebDriver: {e}")
    
    # Fall back to Firefox if Chrome fails
    try:
        print("Falling back to Firefox WebDriver...")
        driver = webdriver.Firefox()
        driver.set_page_load_timeout(30)  # Increase timeout to 30 seconds
        print("Firefox WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"Failed to initialize Firefox WebDriver: {e}")
    
    print("Failed to initialize any WebDriver")
    return None

def initialize_listings():
    """
    Initialize the listings data from the master CSV file.
    
    Returns:
        pandas.DataFrame: The listings data.
    """
    master_csv = os.path.join("database", "master.csv")
    if not os.path.exists(master_csv):
        print("Master CSV file not found")
        return pd.DataFrame(columns=["Latitude", "Longitude"])
    
    return pd.read_csv(master_csv)

def initialize_coordinates():
    """
    Initialize the coordinates data from the master CSV file.
    
    Returns:
        list: A list of (latitude, longitude) tuples.
    """
    listings = initialize_listings()
    coordinates = []
    
    for _, row in listings.iterrows():
        if pd.notna(row.get("Latitude")) and pd.notna(row.get("Longitude")):
            coordinates.append((row["Latitude"], row["Longitude"]))
    
    return coordinates

# Add a mock data generation function for testing when the website is down
def generate_mock_census_data(coord, verbose=False):
    """
    Generate mock census data for testing when the website is down.
    
    Args:
        coord (tuple): The (latitude, longitude) tuple.
        verbose (bool): Whether to print verbose output.
        
    Returns:
        dict: Dictionary with mock census data.
    """
    if verbose:
        print(f"Generating mock census data for coordinates: {coord}")
    
    # Create a mock data dictionary with some realistic column names
    mock_data = {
        "Latitude": coord[0],
        "Longitude": coord[1],
        "Total_Population": random.randint(1000, 50000),
        "Median_Age": random.uniform(25, 45),
        "Median_Household_Income": random.randint(30000, 120000),
        "Percent_Bachelor_Degree": random.uniform(10, 60),
        "Percent_Homeowner": random.uniform(40, 80),
        "Percent_Below_Poverty": random.uniform(5, 30),
        "Unemployment_Rate": random.uniform(2, 15),
        "Population_Density": random.uniform(100, 10000),
    }
    
    # Add some radius-specific data
    for radius in [5, 10, 15, 20, 25]:
        population_factor = 1 + (radius / 5)
        mock_data[f"Total_Population_{radius}mi"] = int(mock_data["Total_Population"] * population_factor)
        mock_data[f"Median_Household_Income_{radius}mi"] = int(mock_data["Median_Household_Income"] * (1 + random.uniform(-0.2, 0.2)))
        mock_data[f"Percent_Bachelor_Degree_{radius}mi"] = mock_data["Percent_Bachelor_Degree"] * (1 + random.uniform(-0.2, 0.2))
    
    if verbose:
        print(f"Generated {len(mock_data)} mock data points")
    
    return mock_data

# Add a function to save mock data to CSV
def save_mock_data_to_csv(coord, mock_data, verbose=False):
    """
    Save mock census data to a CSV file.
    
    Args:
        coord (tuple): The (latitude, longitude) tuple.
        mock_data (dict): Dictionary with mock census data.
        verbose (bool): Whether to print verbose output.
        
    Returns:
        str: Path to the saved CSV file.
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.join("database", "MCDC"), exist_ok=True)
    
    # Create the file path
    file_path = os.path.join("database", "MCDC", f"mcdc_{coord[0]}_{coord[1]}.csv")
    
    # Convert dictionary to DataFrame
    df = pd.DataFrame([mock_data])
    
    # Save to CSV
    df.to_csv(file_path, index=False)
    
    if verbose:
        print(f"Saved mock data to {file_path}")
    
    return file_path

def extract_radius_data(csv_filepath, column_names):
    """
    Extract specific columns from the CSV generated by MCDC for different radii.
    
    Args:
        csv_filepath (str): Path to the CSV file
        column_names (list): List of column names to extract
        
    Returns:
        dict: Dictionary with keys being 'column_radius' and values being the value
    """
    try:
        # Read the CSV file
        csv_df = pd.read_csv(csv_filepath)
        
        print(f"CSV file has {len(csv_df)} rows and {len(csv_df.columns)} columns")
        
        # Define the radii and their corresponding rows in the CSV
        radii_rows = {
            5: 0,   # 5mi radius is on row 1 (index 0)
            10: 1,  # 10mi radius is on row 2 (index 1)
            15: 2,  # 15mi radius is on row 3 (index 2)
            20: 3,  # 20mi radius is on row 4 (index 3)
            25: 4   # 25mi radius is on row 5 (index 4)
        }
        
        # Initialize results dictionary
        results = {}
        
        # Get the exact columns present in the CSV
        csv_columns = csv_df.columns.tolist()
        
        # Print the first few columns for debugging
        print(f"First 10 columns in CSV: {csv_columns[:10]}")
        
        # Print the TotPop values for each row
        print("TotPop values by row:")
        if 'TotPop' in csv_columns:
            for i in range(min(5, len(csv_df))):
                print(f"  Row {i}: {csv_df.loc[i, 'TotPop']}")
        else:
            print("  'TotPop' column not found in CSV")
        
        # Print the TotalOwnerUnits values for each row
        print("TotalOwnerUnits values by row:")
        if 'TotalOwnerUnits' in csv_columns:
            for i in range(min(5, len(csv_df))):
                print(f"  Row {i}: {csv_df.loc[i, 'TotalOwnerUnits']}")
        else:
            print("  'TotalOwnerUnits' column not found in CSV")
        
        # Extract data for each radius
        for radius, row_idx in radii_rows.items():
            if row_idx < len(csv_df):
                radius_data_count = 0
                for col in column_names:
                    if col in csv_columns:
                        # Create a new column name with radius suffix
                        new_col = f"{col}_{radius}"
                        
                        # Extract the value and clean it
                        value = csv_df.loc[row_idx, col]
                        
                        # Clean the value if it's a string (remove commas, quotes, and convert to numeric if possible)
                        if isinstance(value, str):
                            # Remove quotes and commas
                            cleaned_value = value.replace('"', '').replace(',', '')
                            
                            # Handle 'N' or other non-numeric values
                            if cleaned_value.strip() == 'N' or cleaned_value.strip() == '':
                                value = np.nan
                            else:
                                # Try to convert to numeric
                                try:
                                    # Remove dollar signs for currency values
                                    cleaned_value = cleaned_value.replace('$', '')
                                    
                                    if '.' in cleaned_value:
                                        value = float(cleaned_value)
                                    else:
                                        value = int(cleaned_value)
                                except (ValueError, TypeError):
                                    # Keep as string if conversion fails
                                    value = cleaned_value
                        
                        # Store the cleaned value
                        results[new_col] = value
                        radius_data_count += 1
                    else:
                        print(f"Warning: Column '{col}' not found in the CSV file")
                
                print(f"Extracted {radius_data_count} columns for radius {radius}mi")
        
        # Print some of the extracted data for verification
        print("\nExtracted data:")
        sample_cols = ["TotalOwnerUnits", "TotPop"]
        for col in sample_cols:
            for radius in radii_rows.keys():
                col_name = f"{col}_{radius}"
                if col_name in results:
                    print(f"{col_name}: {results[col_name]}")
        
        return results
    except Exception as e:
        print(f"Error extracting radius data from {csv_filepath}: {e}")
        import traceback
        traceback.print_exc()
        return {}

def update_master_csv_with_radius_data(coord, csv_path, verbose=False):
    """
    Update the master CSV with radius-specific data from the MCDC CSV.
    
    Args:
        coord (tuple): Latitude, longitude tuple
        csv_path (str): Path to the MCDC CSV file
        verbose (bool): Print verbose output
    """
    if verbose:
        print(f"Updating master CSV with radius data from {csv_path}")
    
    # Define the columns to extract (as specified by the user)
    columns_to_extract = [
        "TotPop", "Age0_4", "Age5_9", "Age10_14", "Age15_19", "Age20_24", 
        "Age25_34", "Age35_44", "Age45_54", "Age55_59", "Age60_64", "Age65_74", 
        "Age75_84", "Over85", "TotHHs", "HHInc0", "HHInc10", "HHInc15", "HHInc25", 
        "HHInc35", "HHInc50", "HHInc75", "HHInc100", "HHInc150", "HHInc200", 
        "MedianHHInc", "AvgHHInc", "InKindergarten", "InElementary", "InHighSchool", 
        "InCollege", "Disabled", "DisabledUnder18", "NonInst18_64", "Disabled18_64", 
        "NonInstOver65", "DisabledElder", "TotHUs", "OccHUs", "OwnerOcc", "RenterOcc", 
        "AvgOwnerHHSize", "AvgRenterHHSize", "VacHUs", "VacantForSale", "VacantForRent", 
        "VacantSeasonal", "TotalOwnerUnits", "OwnerVacRate", "TotalRentalUnits", 
        "RenterVacRate", "PersonsInOwnerUnits", "PersonsInRenterUnits", "MobileHomes", 
        "MobileHomesPerK", "HvalUnder50", "Hval50", "Hval100", "Hval150", "Hval200", 
        "Hval300", "Hval500", "HvalOverMillion", "HvalOver2Million", "MedianHValue",
        "MedianGrossRent", "AvgGrossRent"
    ]
    
    # Extract the radius data
    radius_data = extract_radius_data(csv_path, columns_to_extract)
    
    if not radius_data:
        print(f"No radius data extracted from {csv_path}")
        return
    
    # Initialize or load the master CSV
    master_df = initialize_listings()
    
    # Check if these coordinates already exist in the master CSV
    lat, lng = coord
    existing_rows = master_df[(master_df['Latitude'] == lat) & (master_df['Longitude'] == lng)]
    
    if len(existing_rows) > 0:
        # Update existing row
        index = existing_rows.index[0]
        
        # Add new columns if they don't exist
        for col in radius_data.keys():
            if col not in master_df.columns:
                if verbose:
                    print(f"Added new column: {col}")
                master_df[col] = None
        
        # Update the radius data
        for col, value in radius_data.items():
            master_df.at[index, col] = value
        
        if verbose:
            print(f"Updated row with {len(radius_data)} radius-specific data points")
    else:
        # Create a new row (this should be rare, as coordinates should already exist)
        new_row = {'Latitude': lat, 'Longitude': lng}
        
        # Add the radius data
        for col, value in radius_data.items():
            if col not in master_df.columns:
                if verbose:
                    print(f"Added new column: {col}")
                master_df[col] = None
            new_row[col] = value
        
        # Append the new row
        master_df = pd.concat([master_df, pd.DataFrame([new_row])], ignore_index=True)
        if verbose:
            print(f"Added new row with {len(radius_data)} radius-specific data points")
    
    # Save the updated master CSV
    master_df.to_csv('database/master.csv', index=False)
    if verbose:
        print(f"Saved master CSV with {master_df.shape[0]} rows and {master_df.shape[1]} columns")

if __name__ == "__main__":
    main()

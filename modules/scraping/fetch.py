from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
import os
from datetime import datetime
import requests
import glob

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def read_master_csv():
    """Read the master CSV file."""
    try:
        return pd.read_csv('database/master.csv')
    except Exception as e:
        print(f"Error reading master CSV: {e}")
        return None

def find_existing_csv(latitude, longitude):
    """Find existing CSV file for given coordinates."""
    mcdc_dir = os.path.join('database', 'MCDC')
    if not os.path.exists(mcdc_dir):
        return None
    
    # Look for files matching the pattern latitude-longitude-*.csv
    pattern = os.path.join(mcdc_dir, f"{latitude}-{longitude}-*.csv")
    matching_files = glob.glob(pattern)
    
    if matching_files:
        # Return the most recent file if multiple exist
        return max(matching_files, key=os.path.getctime)
    return None

def extract_data_from_csv(csv_path):
    """Extract specific columns from the downloaded CSV file."""
    try:
        print(f"\nReading CSV file: {csv_path}")
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Helper function to clean values
        def clean_numeric_value(value):
            """Clean values by removing $, commas, and other non-numeric characters"""
            if pd.isna(value):
                return None
            
            # Convert to string first
            value_str = str(value)
            
            # For debugging
            if '$' in value_str:
                print(f"Found dollar sign in value: {value_str}")
                
            # Remove dollar signs and commas
            value_str = value_str.replace('$', '').replace(',', '')
            
            # Strip any other non-numeric characters except decimal point
            value_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
            
            # Convert to float
            return float(value_str) if value_str else None
        
        # Columns to extract - in the order specified by the user
        columns_to_extract = [
            'TotPop',
            'Age0_4',
            'Age5_9',
            'Age10_14',
            'Age15_19',
            'Age20_24',
            'Age25_34',
            'Age35_44',
            'Age45_54',
            'Age55_59',
            'Age60_64',
            'Age65_74',
            'Age75_84',
            'Over85',
            'TotHUs',
            'OccHUs',
            'OwnerOcc',
            'RenterOcc',
            'MobileHomesPerK',
            'MedianGrossRent',
            'AvgGrossRent',
            'CashRentOver30Pct'
        ]
        
        # Map our column names to possible CSV column names
        column_mapping = {
            'TotPop': ['TotPop', 'Total population'],
            'Age0_4': ['Age0_4', 'Age 0-4'],
            'Age5_9': ['Age5_9', 'Age 5-9'],
            'Age10_14': ['Age10_14', 'Age 10-14'],
            'Age15_19': ['Age15_19', 'Age 15-19'],
            'Age20_24': ['Age20_24', 'Age 20-24'],
            'Age25_34': ['Age25_34', 'Age 25-34'],
            'Age35_44': ['Age35_44', 'Age 35-44'],
            'Age45_54': ['Age45_54', 'Age 45-54'],
            'Age55_59': ['Age55_59', 'Age 55-59'],
            'Age60_64': ['Age60_64', 'Age 60-64'],
            'Age65_74': ['Age65_74', 'Age 65-74'],
            'Age75_84': ['Age75_84', 'Age 75-84'],
            'Over85': ['Over85', 'Age 85+', 'Age 85 and over'],
            'TotHUs': ['TotHUs', 'Total housing units'],
            'OccHUs': ['OccHUs', 'Occupied housing units'],
            'OwnerOcc': ['OwnerOcc', 'Owner occupied'],
            'RenterOcc': ['RenterOcc', 'Renter occupied'],
            'MobileHomesPerK': ['MobileHomesPerK', 'Mobile Homes per 1000 Housing Units'],
            'MedianGrossRent': ['MedianGrossRent', 'Median gross rent'],
            'AvgGrossRent': ['AvgGrossRent', 'Average gross rent', 'Mean gross rent'],
            'CashRentOver30Pct': ['CashRentOver30Pct', 'Cash rent over 30 pct of income', 'Cash rent over 30% of income']
        }
        
        # Radii values (mapping row index to radius value)
        # In the CSV, first row is 5mi, second is 10mi, etc.
        radii_mapping = {
            0: 5,   # First row = 5 mile radius
            1: 10,  # Second row = 10 mile radius
            2: 15,  # Third row = 15 mile radius
            3: 20,  # Fourth row = 20 mile radius
            4: 25   # Fifth row = 25 mile radius
        }
        
        # Initialize data dictionary
        data = {}
        
        # Process each column
        for col_name in columns_to_extract:
            # Get possible CSV column names for this metric
            possible_names = column_mapping.get(col_name, [col_name])
            
            # Find the matching column in the CSV
            csv_col = None
            for possible_name in possible_names:
                if possible_name in df.columns:
                    csv_col = possible_name
                    break
            
            if csv_col:
                # Special case for MobileHomesPerK - only need the first value
                if col_name == 'MobileHomesPerK':
                    value = df.iloc[0, df.columns.get_loc(csv_col)]
                    clean_value = clean_numeric_value(value)
                    if clean_value is not None:
                        data['Mobile homes per 1000 HU'] = clean_value
                else:
                    # Extract values for each radius
                    for row_idx, radius in radii_mapping.items():
                        if row_idx < len(df):
                            value = df.iloc[row_idx, df.columns.get_loc(csv_col)]
                            radius_col_name = f"{col_name}_{radius}"
                            
                            if pd.notna(value):
                                try:
                                    # Use the clean_numeric_value helper
                                    clean_value = clean_numeric_value(value)
                                    if clean_value is not None:
                                        data[radius_col_name] = clean_value
                                    else:
                                        data[radius_col_name] = None
                                except Exception as e:
                                    print(f"Error converting {radius_col_name}: {e}, raw value: {value}")
                                    data[radius_col_name] = None
                            else:
                                data[radius_col_name] = None
            else:
                print(f"Could not find column for {col_name} in CSV")
        
        return data if data else None
            
    except Exception as e:
        print(f"Error processing CSV: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return None

def download_csv(driver, latitude, longitude):
    """Download the CSV file from the results page."""
    try:
        # Wait for CSV link to be present
        csv_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'CSV file')]"))
        )
        
        # Get the href attribute
        csv_url = csv_link.get_attribute('href')
        if not csv_url.startswith('http'):
            # Convert relative URL to absolute URL
            base_url = "https://mcdc.missouri.edu"
            csv_url = base_url + csv_url
        
        # Create filename with latitude, longitude, and current date
        current_date = datetime.now().strftime('%Y%m%d')
        filename = f"{latitude}-{longitude}-{current_date}.csv"
        
        # Ensure MCDC directory exists
        mcdc_dir = os.path.join('database', 'MCDC')
        ensure_directory_exists(mcdc_dir)
        
        # Full path for the file
        file_path = os.path.join(mcdc_dir, filename)
        
        # Download the file using requests
        response = requests.get(csv_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Successfully downloaded CSV to {file_path}")
        return file_path
        
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def fetch_census_data(latitude, longitude):
    """Fetch census data from MCDC CAPS ACS website."""
    driver = None
    try:
        # Initialize Safari WebDriver
        driver = webdriver.Safari()
        driver.set_window_size(1200, 800)
        
        # Navigate to the website
        print("\nNavigating to MCDC CAPS ACS website...")
        driver.get("https://mcdc.missouri.edu/applications/capsACS.html")
        
        try:
            # Wait for page to be fully loaded
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Input longitude (use absolute value)
            print("Entering longitude...")
            long_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "longitude"))
            )
            long_input.clear()
            long_value = abs(float(longitude))
            long_input.send_keys(str(long_value))
            time.sleep(0.5)  # Short wait for stability
            
            # Input latitude
            print("Entering latitude...")
            lat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "latitude"))
            )
            lat_input.clear()
            lat_input.send_keys(str(latitude))
            time.sleep(0.5)  # Short wait for stability
            
            # Input radius "5 10 15 20 25"
            print("Entering radius values...")
            radius_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "radii"))
            )
            radius_input.clear()
            radius_input.send_keys("5 10 15 20 25")
            time.sleep(0.5)  # Short wait for stability
            
            # Click generate report button
            print("Clicking generate report button...")
            generate_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][value="Generate report"]'))
            )
            
            # Scroll the button into view and click
            driver.execute_script("arguments[0].scrollIntoView(true);", generate_button)
            time.sleep(1)  # Wait for scroll
            generate_button.click()
            print("Generate report button clicked")
            
            # Wait for results page to load
            print("Waiting for results to load...")
            try:
                # Wait for any table to appear
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                time.sleep(5)  # Give extra time for table to fully load
                
                # Download the CSV file
                csv_path = download_csv(driver, latitude, longitude)
                
                if csv_path:
                    # Extract data from the CSV
                    data = extract_data_from_csv(csv_path)
                    if data:
                        data['latitude'] = latitude
                        data['longitude'] = longitude
                        return data
                
                return None
                
            except Exception as e:
                print(f"Error waiting for results: {e}")
                return None
            
        except Exception as e:
            print(f"Error with form inputs: {e}")
            return None
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                print("Error closing driver")

def update_master_csv(data, row_index):
    """Update the master CSV with the new data."""
    try:
        df = pd.read_csv('database/master.csv')
        
        # Update all columns from the data dictionary
        for col_name, value in data.items():
            if col_name not in ['latitude', 'longitude']:  # Skip these as they're already in master.csv
                if col_name not in df.columns:
                    # Add new column if it doesn't exist
                    df[col_name] = None
                df.loc[row_index, col_name] = value
        
        # Save the updated CSV
        df.to_csv('database/master.csv', index=False)
        print(f"Successfully updated row {row_index}")
    except Exception as e:
        print(f"Error updating master CSV: {e}")

async def main():
    """Main function to process all rows in the CSV."""
    # Get all rows from the CSV
    df = read_master_csv()
    if df is None:
        print("Error reading CSV file")
        return
    
    print(f"Processing {len(df)} rows")
    
    # Process each row
    for index, row in df.iterrows():
        print(f"\nProcessing row {index}: {row['Property Address']}, {row['City']}, {row['State']}")
        
        # First check for existing CSV
        existing_csv = find_existing_csv(row['Latitude'], row['Longitude'])
        
        if existing_csv:
            print(f"Found existing CSV for coordinates {row['Latitude']}, {row['Longitude']}")
            data = extract_data_from_csv(existing_csv)
            if data:
                data['latitude'] = row['Latitude']
                data['longitude'] = row['Longitude']
                update_master_csv(data, index)
                continue
            else:
                print("Failed to extract data from existing CSV, will fetch new data")
        
        # If no existing CSV or failed to extract data, fetch new data
        print(f"Fetching new data for coordinates {row['Latitude']}, {row['Longitude']}")
        data = fetch_census_data(row['Latitude'], row['Longitude'])
        
        if data:
            # Update master CSV
            update_master_csv(data, index)
        else:
            print(f"Failed to fetch data for row {index}")
        
        # Wait between requests to avoid overwhelming the server
        time.sleep(2)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

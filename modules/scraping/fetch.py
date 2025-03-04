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

# Initialize Rich console for output
console = Console()

# Path to the directory for storing MCDC files
MCDC_DIR = "database/MCDC"

def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)

def read_master_csv():
    try:
        return pd.read_csv("database/master.csv")
    except Exception as e:
        print(f"Error reading master CSV: {e}")
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

def extract_data_from_csv(csv_path):
    """Extract specific columns from the downloaded CSV file."""
    try:
        # Read the CSV file (quietly)
        df = pd.read_csv(csv_path)
        
        # Helper function to clean values
        def clean_numeric_value(value):
            """Clean values by removing $, commas, and other non-numeric characters"""
            if pd.isna(value):
                return None
            
            # Convert to string first
            value_str = str(value)
            
            # Remove dollar signs and commas
            value_str = value_str.replace('$', '').replace(',', '')
            
            # Strip any other non-numeric characters except decimal point
            value_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
            
            # Convert to float
            return float(value_str) if value_str else None
        
        # Columns to extract - in the order specified by the user
        columns_to_extract = [
            'TotPop', 'Age0_4', 'Age5_9', 'Age10_14', 'Age15_19', 'Age20_24', 'Age25_34', 
            'Age35_44', 'Age45_54', 'Age55_59', 'Age60_64', 'Age65_74', 'Age75_84', 'Over85', 
            'TotHUs', 'OccHUs', 'OwnerOcc', 'RenterOcc', 'MedianGrossRent', 'AvgGrossRent', 
            'CashRenterOver30Pct', 'MobileHomesPerK', 'MedianHHInc'
        ]
        
        # Mapping for alternative column names
        column_mapping = {
            'TotPop': ['TotPop', 'Total Population'],
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
            'TotHUs': ['TotHUs', 'Total Housing Units'],
            'OccHUs': ['OccHUs', 'Occupied Housing Units'],
            'OwnerOcc': ['OwnerOcc', 'Owner Occupied'],
            'RenterOcc': ['RenterOcc', 'Renter Occupied'],
            'MedianGrossRent': ['MedianGrossRent', 'Median Gross Rent'],
            'AvgGrossRent': ['AvgGrossRent', 'Average Gross Rent'],
            'CashRenterOver30Pct': ['CashRenterOver30Pct', 'pctCashRenterOver30Pct', 'Percent cash renters paying >30% of income toward rent'],
            'MobileHomesPerK': ['MobileHomesPerK', 'Mobile Homes per 1000 Housing Units', 'Mobile homes per 1000 housing units'],
            'MedianHHInc': ['MedianHHInc', 'Median Household Income', 'Median HH Income']
        }
        
        # Radii from the file (5, 10, 15, 20, 25 miles)
        radii_mapping = {0: 5, 1: 10, 2: 15, 3: 20, 4: 25}
        
        # Initialize data dictionary
        data = {}
        
        # Extract data for each column
        for col_name in columns_to_extract:
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
                                except Exception:
                                    # Silently handle conversion errors
                                    pass
                            else:
                                data[radius_col_name] = None
        
        return data
    except Exception as e:
        # Keep error logging for significant issues
        print(f"Error processing CSV: {e}")
        # Only print full traceback for debugging
        if os.environ.get('DEBUG_MODE') == '1':
            print("Full traceback:")
            print(traceback.format_exc())
        return None

def download_csv(driver, latitude, longitude):
    """Download the CSV file and extract data."""
    try:
        # Click the download CSV button
        download_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'CSV')]"))
        )
        download_button.click()
        
        # Wait for the download to complete (assuming it goes to a downloads folder)
        time.sleep(2)
        
        # Move the file to a known location
        today = datetime.now().strftime("%Y-%m-%d")
        file_name = f"{latitude}-{longitude}-{today}.csv"
        
        # Ensure directory exists
        ensure_directory_exists(MCDC_DIR)
        
        # Get the most recent file from downloads directory
        downloads_dir = str(Path.home() / "Downloads")
        list_of_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
        if not list_of_files:
            raise Exception("No CSV file found in downloads directory")
        
        # Get the most recent CSV file from downloads
        latest_file = max(list_of_files, key=os.path.getctime)
        
        # Copy to our directory
        file_path = os.path.join(MCDC_DIR, file_name)
        # Use os.rename to move the file
        os.rename(latest_file, file_path)
        
        # Extract data from the CSV
        data = extract_data_from_csv(file_path)
        
        return data
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def fetch_census_data(latitude, longitude):
    """Fetch census data for the given coordinates."""
    driver = None
    try:
        # Reduced verbosity during web scraping
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        # Add headless option for less visual distraction
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the MCDC CAPS ACS website
        driver.get("https://mcdc.missouri.edu/applications/capsACS.html")
        
        # Enter values in the form
        longitude_input = driver.find_element(By.ID, "longd")
        longitude_input.clear()
        longitude_input.send_keys(str(longitude))
        
        latitude_input = driver.find_element(By.ID, "latd")
        latitude_input.clear()
        latitude_input.send_keys(str(latitude))
        
        # Enter radius values
        radius_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'][size='3']")
        for i, radius in enumerate([5, 10, 15, 20, 25]):
            if i < len(radius_inputs):
                radius_inputs[i].clear()
                radius_inputs[i].send_keys(str(radius))
        
        # Click the generate report button
        generate_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Generate Report']")
        generate_button.click()
        
        # Wait for the results page to load
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.data"))
            )
            
            # Download the CSV and extract data
            return download_csv(driver, latitude, longitude)
            
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return None
            
    except Exception as e:
        if "form inputs" in str(e).lower():
            print(f"Error with form inputs: {e}")
        else:
            print(f"An error occurred: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                # Silently handle driver close errors
                pass

def update_master_csv(data, row_index):
    """Update the master CSV with the extracted data."""
    try:
        # Read the master CSV
        df = pd.read_csv("database/master.csv")
        
        # Update the row with extracted data
        for col, value in data.items():
            # Check if the column exists, if not, add it
            if col not in df.columns:
                df[col] = None
            
            # Update the value, but never overwrite the StockNumber
            if col != 'StockNumber':
                df.at[row_index, col] = value
        
        # If this is a row without a StockNumber, make sure StockNumber is always the first column
        if 'StockNumber' in df.columns and pd.isna(df.at[row_index, 'StockNumber']):
            # Generate a state code
            state_code = "XX"  # Default
            
            if 'State' in df.columns and pd.notna(df.at[row_index, 'State']):
                state_code = df.at[row_index, 'State']
            elif 'Market' in df.columns and pd.notna(df.at[row_index, 'Market']):
                # Extract state code from market name
                market = df.at[row_index, 'Market']
                if "Upstate NY" in market:
                    state_code = "NY"
                elif "I85 Corridor" in market:
                    state_code = "I85"
                elif "Florida" in market:
                    state_code = "FL"
            
            # This is a helper function imported from process_listings
            # If it's not available, we'll just leave the StockNumber as null
            try:
                from modules.datasubmition.process_listings import generate_stock_number
                df.at[row_index, 'StockNumber'] = generate_stock_number(df, state_code)
            except ImportError:
                pass  # Skip if the function is not available
        
        # Ensure StockNumber is the first column if it exists
        if 'StockNumber' in df.columns:
            cols = df.columns.tolist()
            if cols[0] != 'StockNumber':
                cols.remove('StockNumber')
                cols = ['StockNumber'] + cols
                df = df[cols]
        
        # Save the updated CSV
        df.to_csv("database/master.csv", index=False)
        
        # Minimal success feedback
        return True
    except Exception as e:
        print(f"Error updating master CSV: {e}")
        return False

def process_existing_or_fetch_new(latitude, longitude, row_index):
    """Process existing CSV or fetch new data."""
    # Check for an existing CSV file
    existing_csv = find_existing_csv(latitude, longitude)
    
    if existing_csv:
        # Minimal output about existing file
        
        # Extract data from the existing CSV
        data = extract_data_from_csv(existing_csv)
        
        if data and len(data) > 0:
            # Update the master CSV with the extracted data
            update_master_csv(data, row_index)
            return True
        else:
            # Quietly proceed to fetch new data
            pass
    
    # Fetch new data
    data = fetch_census_data(latitude, longitude)
    
    if data and len(data) > 0:
        # Update the master CSV with the extracted data
        update_master_csv(data, row_index)
        return True
    else:
        # Quiet failure
        return False

def verify_census_data_completeness():
    """Check if all listings have complete census data and report what's missing."""
    try:
        # Read the master CSV
        df = pd.read_csv("database/master.csv")
        
        # Check for listings with coordinates
        has_coords = df['Latitude'].notna() & df['Longitude'].notna()
        df_with_coords = df[has_coords]
        
        # Key columns that should be present if census data was fetched
        key_columns = [
            'TotPop_5', 'TotHUs_5', 'MedianGrossRent_5', 
            'Age0_4_5', 'Age5_9_5', 'Age10_14_5', 'Age15_19_5', 'MedianHHInc_5'
        ]
        
        # Optional columns that we don't want to trigger a retry if missing
        optional_columns = ['MobileHomesPerK_5']
        
        # Find rows that are missing any key columns
        missing_rows = []
        # Keep track of which columns are missing for diagnostics
        missing_data_details = {}
        # Count how many listings are missing each column
        missing_column_counts = {col: 0 for col in key_columns}
        # Also track optional columns for reporting purposes, but don't include in missing_rows
        for col in optional_columns:
            missing_column_counts[col] = 0
        
        for index, row in df_with_coords.iterrows():
            missing_columns = []
            optional_missing_columns = []
            
            # Check which key columns are missing
            for col in key_columns:
                if col not in df.columns or pd.isna(row[col]):
                    missing_columns.append(col)
                    missing_column_counts[col] += 1
            
            # Also check optional columns for reporting
            for col in optional_columns:
                if col not in df.columns or pd.isna(row[col]):
                    optional_missing_columns.append(col)
                    missing_column_counts[col] += 1
            
            # Only add to missing_rows if required columns are missing (not just optional)
            if missing_columns:
                missing_rows.append(index)
                missing_data_details[index] = {
                    'coords': (row['Latitude'], row['Longitude']),
                    'missing_columns': missing_columns + optional_missing_columns
                }
            # If only optional columns are missing, still add to details but don't trigger retry
            elif optional_missing_columns:
                missing_data_details[index] = {
                    'coords': (row['Latitude'], row['Longitude']),
                    'missing_columns': optional_missing_columns
                }
        
        return missing_rows, missing_data_details, missing_column_counts
    except Exception as e:
        print(f"Error verifying data completeness: {e}")
        return [], {}, {}

def main():
    """Main function to process all listings."""
    # Ensure the MCDC directory exists
    ensure_directory_exists(MCDC_DIR)
    
    # Read the master CSV
    df = read_master_csv()
    if df is None:
        console.print("[red]Error: Could not read master CSV file.[/red]")
        return
    
    # Check for listings with coordinates
    has_coords = df['Latitude'].notna() & df['Longitude'].notna()
    rows_to_process = df[has_coords].index.tolist()
    
    if not rows_to_process:
        console.print("[red]No listings with coordinates found[/red]")
        return
    
    # Initial messaging
    total = len(rows_to_process)
    console.print(f"[cyan]Fetching additional census data for all listings...[/cyan]")
    console.print(f"[cyan]Processing {total} listings...[/cyan]")
    
    # Use a set to track successfully processed listings
    successful_listings = set()
    
    # Process all rows initially with a progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("[cyan]Processing listings...[/cyan]", total=total)
        
        for index in rows_to_process:
            latitude = df.loc[index, 'Latitude']
            longitude = df.loc[index, 'Longitude']
            
            # Process existing or fetch new data
            success = process_existing_or_fetch_new(latitude, longitude, index)
            
            if success:
                successful_listings.add(index)
                
            # Update progress
            progress.update(task, advance=1, description=f"[cyan]Processing listing {progress.tasks[task].completed + 1}/{total}[/cyan]")
    
    # Maximum of 2 retry attempts
    max_retries = 2
    
    for retry_attempt in range(1, max_retries + 1):
        # Verify data completeness with detailed reports
        missing_rows, missing_details, missing_column_counts = verify_census_data_completeness()
        
        if not missing_rows:
            # All data is complete
            console.print("[bold green]All census data is complete![/bold green]")
            break
        
        # Process rows with missing data
        console.print(f"\n[bold cyan]--- Retry Attempt {retry_attempt} of {max_retries} ---[/bold cyan]")
        console.print(f"[yellow]Found {len(missing_rows)} listings with missing data. Retrying...[/yellow]")
        
        # Show summary of which columns are missing
        console.print("\n[bold]Missing data summary:[/bold]")
        for col, count in missing_column_counts.items():
            if count > 0:
                console.print(f"  {col}: missing in {count} listings")
        
        # Display a sample of listings with missing data (limit to 5 for readability)
        sample_size = min(5, len(missing_details))
        if sample_size > 0:
            console.print("\n[bold]Sample of listings with missing data:[/bold]")
            sample_listings = list(missing_details.items())[:sample_size]
            for idx, details in sample_listings:
                lat = details['coords'][0]
                lon = details['coords'][1]
                missing_cols = ', '.join(details['missing_columns'])
                console.print(f"  Row {idx}: ({lat}, {lon}) - Missing: {missing_cols}")
            
            if len(missing_details) > sample_size:
                console.print(f"  ... and {len(missing_details) - sample_size} more listings")
        
        # Retry processing with a progress bar
        if missing_rows:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn()
            ) as progress:
                retry_task = progress.add_task(
                    f"[yellow]Retry attempt {retry_attempt}/{max_retries}[/yellow]", 
                    total=len(missing_rows)
                )
                
                for i, index in enumerate(missing_rows):
                    if index not in rows_to_process:
                        progress.update(retry_task, advance=1)
                        continue  # Skip if not in our original list
                        
                    latitude = df.loc[index, 'Latitude']
                    longitude = df.loc[index, 'Longitude']
                    
                    # Process existing or fetch new data
                    success = process_existing_or_fetch_new(latitude, longitude, index)
                    
                    if success:
                        successful_listings.add(index)
                    
                    # Update progress with more detailed description
                    progress.update(
                        retry_task, 
                        advance=1, 
                        description=f"[yellow]Retry {retry_attempt}/{max_retries}: {i+1}/{len(missing_rows)}[/yellow]"
                    )
    
    # Final verification to see what's still missing
    final_missing_rows, final_missing_details, final_missing_counts = verify_census_data_completeness()
    
    # Final summary
    successfully_processed = len(successful_listings)
    console.print(f"\n[bold green]Successfully processed {successfully_processed} out of {total} listings with coordinates[/bold green]")
    
    if final_missing_rows:
        console.print(f"[yellow]Could not retrieve complete data for {len(final_missing_rows)} listings[/yellow]")
        
        # Show what columns are still missing
        console.print("\n[bold]Still missing data for these columns:[/bold]")
        for col, count in final_missing_counts.items():
            if count > 0:
                console.print(f"  {col}: missing in {count} listings")
    
    console.print("[bold green]Census data fetching completed[/bold green]")

if __name__ == "__main__":
    main()

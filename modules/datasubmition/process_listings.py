import pandas as pd
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import tkinter as tk
from tkinter import filedialog
import re

# Initialize Rich console
console = Console()

def create_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs("database/log", exist_ok=True)
    os.makedirs("database", exist_ok=True)

def get_multiple_input_files():
    """Get multiple input file paths from the user."""
    try:
        # Try to use tkinter file dialog
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        file_paths = filedialog.askopenfilenames(
            title="Please select your property listings files (CSV format)",
            filetypes=[("CSV files", "*.csv")]
        )
        file_paths = list(file_paths)  # Convert from tuple to list
    except ImportError:
        # Fallback to command line input if tkinter is not available
        console.print(Panel.fit(
            "[yellow]Please type or paste the paths to your CSV files containing the property listings (separate with commas):[/yellow]"
        ))
        file_paths_input = console.input("[cyan]File paths (comma-separated): [/cyan]").strip()
        
        # Split by comma and strip whitespace
        file_paths = [path.strip().strip("'\"") for path in file_paths_input.split(",")]
        
        # Validate each file exists and is a CSV
        valid_paths = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                console.print(f"[red]Couldn't find file: {file_path}. Skipping.[/red]")
                continue
            if not file_path.lower().endswith('.csv'):
                console.print(f"[red]File must be a CSV: {file_path}. Skipping.[/red]")
                continue
            valid_paths.append(file_path)
        
        file_paths = valid_paths
    
    if not file_paths:
        return []
    
    return file_paths

def generate_timestamp_filename(market_code):
    """Generate a filename with current timestamp for the specific market."""
    current_time = datetime.now().strftime("%m-%d-%Y-%H-%M")
    return f"{current_time}-{market_code}.csv"

def generate_stock_number(df, state_code):
    """Generate a unique stock number in the format STATE-XXXXX."""
    # Extract existing stock numbers for this state
    if 'StockNumber' in df.columns:
        # Get existing stock numbers for this state
        pattern = f"^{state_code}-\\d{{5}}$"
        state_stock_numbers = df[df['StockNumber'].str.match(pattern, na=False)]
        
        if len(state_stock_numbers) > 0:
            # Extract the numeric parts and find the maximum
            max_number = 0
            for stock_num in state_stock_numbers['StockNumber']:
                if pd.notna(stock_num):
                    num_part = int(stock_num.split('-')[1])
                    max_number = max(max_number, num_part)
            
            # Increment for the new number
            next_number = max_number + 1
        else:
            # Start with 1 if no existing numbers for this state
            next_number = 1
    else:
        # No StockNumber column yet, start with 1
        next_number = 1
    
    # Format with leading zeros to 5 digits
    return f"{state_code}-{next_number:05d}"

def validate_stock_numbers(df):
    """Validate that all stock numbers are unique."""
    if 'StockNumber' not in df.columns or df['StockNumber'].isna().all():
        return True
    
    # Check for duplicates
    duplicates = df[df['StockNumber'].notna()]['StockNumber'].duplicated()
    if duplicates.any():
        duplicate_values = df[df['StockNumber'].notna()]['StockNumber'][duplicates].tolist()
        console.print(f"[red]Error: Duplicate stock numbers found: {duplicate_values}[/red]")
        return False
    
    return True

def process_listings(market):
    """Process multiple input CSV files and update the master file."""
    # Ensure directories exist
    create_directories()
    
    # Get multiple input files from user
    input_files = get_multiple_input_files()
    if not input_files:
        console.print("\n[red]No files were selected. Please try again when you have your listings files ready.[/red]")
        return False

    console.print(f"\n[green]You've selected {len(input_files)} file(s) to process.[/green]")
    
    # Initialize a summary table for all processed files
    overall_summary = {
        "total_processed": 0,
        "total_new_added": 0,
        "total_duplicates": 0,
        "files_processed": []
    }
    
    # Read the master file if it exists
    master_path = os.path.join("database", "master.csv")
    if os.path.exists(master_path):
        master_df = pd.read_csv(master_path)
        console.print("\n[blue]Found existing master database.[/blue]")
    else:
        master_df = pd.DataFrame()
        console.print("\n[blue]Creating new master database.[/blue]")
    
    # Process each file
    for file_index, input_file in enumerate(input_files):
        console.print(f"\n[blue]Processing file {file_index + 1}/{len(input_files)}: {os.path.basename(input_file)}[/blue]")
        
        # Read the current input CSV
        try:
            input_df = pd.read_csv(input_file)
            file_listings = len(input_df)
            console.print(f"[green]This file contains {file_listings} property listings.[/green]")
        except Exception as e:
            console.print(f"[red]Problem reading file {input_file}: {e}[/red]")
            console.print("[red]Skipping this file and continuing with the next.[/red]")
            continue
            
        # Verify required columns exist
        required_columns = ['Latitude', 'Longitude']
        if not all(col in input_df.columns for col in required_columns):
            console.print(f"[red]File {input_file} is missing 'Latitude' and/or 'Longitude' columns. Skipping.[/red]")
            continue

        # Add timestamp and market to input data
        current_date = datetime.now().strftime("%Y-%m-%d")
        input_df['date'] = current_date
        input_df['Market'] = market['name']

        # Save raw input file to log
        log_filename = generate_timestamp_filename(market['code'])
        log_path = os.path.join("database", "log", log_filename)
        input_df.to_csv(log_path, index=False)
        console.print(f"[blue]Original file saved as: {log_filename}[/blue]")

        # Identify unique listings based on Latitude and Longitude
        new_listings = input_df.copy()
        if not master_df.empty:
            # Create a unique identifier from Latitude and Longitude
            def create_location_id(row):
                return f"{row['Latitude']}_{row['Longitude']}"
            
            master_df['location_id'] = master_df.apply(create_location_id, axis=1)
            new_listings['location_id'] = new_listings.apply(create_location_id, axis=1)
            
            # Filter out listings that already exist in master
            existing_locations = set(master_df['location_id'])
            new_listings = new_listings[~new_listings['location_id'].isin(existing_locations)]
            
            # Remove the temporary location_id column
            new_listings = new_listings.drop('location_id', axis=1)
            master_df = master_df.drop('location_id', axis=1)

        # Append new listings to master
        file_new_listings = len(new_listings)
        file_duplicates = file_listings - file_new_listings
        
        if not new_listings.empty:
            # Create a temporary combined dataframe to account for new stock numbers
            temp_df = master_df.copy()
            
            # Initialize state code counters dictionary
            state_counters = {}
            
            # Add stock numbers to new listings
            if 'State' in new_listings.columns:
                # Use the actual state code from the data
                for index, row in new_listings.iterrows():
                    state_code = row['State'] if pd.notna(row['State']) else market['code']
                    
                    # Initialize counter for this state if not exists
                    if state_code not in state_counters:
                        # Find the max number for this state in master_df
                        max_number = 0
                        if 'StockNumber' in temp_df.columns:
                            pattern = f"^{state_code}-\\d{{5}}$"
                            state_stock_numbers = temp_df[temp_df['StockNumber'].str.match(pattern, na=False)]
                            
                            if len(state_stock_numbers) > 0:
                                for stock_num in state_stock_numbers['StockNumber']:
                                    if pd.notna(stock_num):
                                        try:
                                            num_part = int(stock_num.split('-')[1])
                                            max_number = max(max_number, num_part)
                                        except (IndexError, ValueError):
                                            # Skip invalid stock numbers
                                            pass
                        
                        state_counters[state_code] = max_number + 1
                    
                    # Generate stock number with the current counter
                    stock_number = f"{state_code}-{state_counters[state_code]:05d}"
                    new_listings.at[index, 'StockNumber'] = stock_number
                    
                    # Update temporary dataframe with this new stock number
                    new_row = pd.Series({'StockNumber': stock_number})
                    temp_df = pd.concat([temp_df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Increment counter for this state
                    state_counters[state_code] += 1
            else:
                # Use market code as the state code
                state_code = market['code']
                
                # Initialize counter for this state
                if state_code not in state_counters:
                    # Find the max number for this state in master_df
                    max_number = 0
                    if 'StockNumber' in temp_df.columns:
                        pattern = f"^{state_code}-\\d{{5}}$"
                        state_stock_numbers = temp_df[temp_df['StockNumber'].str.match(pattern, na=False)]
                        
                        if len(state_stock_numbers) > 0:
                            for stock_num in state_stock_numbers['StockNumber']:
                                if pd.notna(stock_num):
                                    try:
                                        num_part = int(stock_num.split('-')[1])
                                        max_number = max(max_number, num_part)
                                    except (IndexError, ValueError):
                                        # Skip invalid stock numbers
                                        pass
                    
                    state_counters[state_code] = max_number + 1
                
                for index, row in new_listings.iterrows():
                    # Generate stock number with the current counter
                    stock_number = f"{state_code}-{state_counters[state_code]:05d}"
                    new_listings.at[index, 'StockNumber'] = stock_number
                    
                    # Update temporary dataframe with this new stock number
                    new_row = pd.Series({'StockNumber': stock_number})
                    temp_df = pd.concat([temp_df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Increment counter for this state
                    state_counters[state_code] += 1

            # Make sure StockNumber is the first column
            if 'StockNumber' in new_listings.columns:
                cols = new_listings.columns.tolist()
                cols.remove('StockNumber')
                cols = ['StockNumber'] + cols
                new_listings = new_listings[cols]
            
            # Update the master dataframe with new listings
            if 'StockNumber' not in master_df.columns and 'StockNumber' in new_listings.columns:
                # If master doesn't have StockNumber but new listings do,
                # we need to reorder master columns as well
                master_df['StockNumber'] = None  # Add empty column
                cols = master_df.columns.tolist()
                cols.remove('StockNumber')
                cols = ['StockNumber'] + cols
                master_df = master_df[cols]
            
            # Concatenate and validate
            updated_df = pd.concat([master_df, new_listings], ignore_index=True)
            
            # Ensure all stock numbers are unique
            if not validate_stock_numbers(updated_df):
                console.print("[red]Error: Duplicate stock numbers detected. Processing stopped.[/red]")
                return False
                
            # Save the updated master file
            updated_df.to_csv(master_path, index=False)
            
            # Update overall summary
            overall_summary["total_processed"] += file_listings
            overall_summary["total_new_added"] += file_new_listings
            overall_summary["total_duplicates"] += file_duplicates
            overall_summary["files_processed"].append(os.path.basename(input_file))
            
            # Create a summary table for this file
            table = Table(title=f"File {file_index + 1} Summary: {os.path.basename(input_file)}", show_header=False)
            table.add_column("Description", style="cyan")
            table.add_column("Count", style="green", justify="right")
            table.add_row("Total listings in file", str(file_listings))
            table.add_row("New unique properties added", str(file_new_listings))
            table.add_row("Already in database", str(file_duplicates))
            
            console.print("\n", table)
        else:
            console.print(Panel.fit(
                f"[yellow]We found {file_listings} listings in this file, but all of them are already in your database.[/yellow]",
                border_style="yellow"
            ))
            # Update overall summary for duplicates
            overall_summary["total_processed"] += file_listings
            overall_summary["total_duplicates"] += file_listings
            overall_summary["files_processed"].append(os.path.basename(input_file))
    
    # Display overall summary after processing all files
    if overall_summary["files_processed"]:
        overall_table = Table(title="Overall Processing Summary", show_header=False, title_style="bold green")
        overall_table.add_column("Description", style="cyan")
        overall_table.add_column("Count", style="green", justify="right")
        overall_table.add_row("Total files processed", str(len(overall_summary["files_processed"])))
        overall_table.add_row("Total listings processed", str(overall_summary["total_processed"]))
        overall_table.add_row("Total new unique properties added", str(overall_summary["total_new_added"]))
        overall_table.add_row("Total duplicates skipped", str(overall_summary["total_duplicates"]))
        
        console.print("\n", overall_table)
        
        # Print file list
        console.print("\n[blue]Files processed:[/blue]")
        for i, file_name in enumerate(overall_summary["files_processed"]):
            console.print(f"  {i+1}. {file_name}")
    
    return True 
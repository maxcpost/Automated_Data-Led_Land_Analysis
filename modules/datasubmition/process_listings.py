import pandas as pd
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize Rich console
console = Console()

def create_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs("database/log", exist_ok=True)
    os.makedirs("database", exist_ok=True)

def get_input_file():
    """Get the input file path from the user."""
    try:
        # Try to use tkinter file dialog
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        file_path = filedialog.askopenfilename(
            title="Please select your property listings file (CSV format)",
            filetypes=[("CSV files", "*.csv")]
        )
    except ImportError:
        # Fallback to command line input if tkinter is not available
        console.print(Panel.fit(
            "[yellow]Please type or paste the path to your CSV file containing the property listings:[/yellow]"
        ))
        file_path = console.input("[cyan]File path: [/cyan]").strip()
        
        # Remove quotes if present
        file_path = file_path.strip("'\"")
        
        # Validate file exists and is a CSV
        if not os.path.exists(file_path):
            console.print("[red]Sorry, we couldn't find that file. Please check the file path and try again.[/red]")
            return None
        if not file_path.lower().endswith('.csv'):
            console.print("[red]The file must be a CSV file. Please select a file that ends with .csv[/red]")
            return None
    
    return file_path

def generate_timestamp_filename(market_code):
    """Generate a filename with current timestamp for the specific market."""
    current_time = datetime.now().strftime("%m-%d-%Y-%H-%M")
    return f"{current_time}-{market_code}.csv"

def process_listings(market):
    """Process the input CSV file and update the master file."""
    # Ensure directories exist
    create_directories()
    
    # Get input file from user
    input_file = get_input_file()
    if not input_file:
        console.print("\n[red]No file was selected. Please try again when you have your listings file ready.[/red]")
        return False

    # Read the input CSV
    try:
        input_df = pd.read_csv(input_file)
        total_listings = len(input_df)
        console.print(f"\n[green]Your file contains {total_listings} property listings.[/green]")
    except Exception as e:
        console.print(f"\n[red]Sorry, there was a problem reading your file: {e}[/red]")
        console.print("[red]Please make sure it's a valid CSV file and try again.[/red]")
        return False

    # Verify required columns exist
    required_columns = ['Latitude', 'Longitude']
    if not all(col in input_df.columns for col in required_columns):
        console.print("\n[red]Your CSV file needs to have both 'Latitude' and 'Longitude' columns.[/red]")
        console.print("[red]Please check your file and make sure these columns are included.[/red]")
        return False

    # Add timestamp and market to input data
    current_date = datetime.now().strftime("%Y-%m-%d")
    input_df['date'] = current_date
    input_df['Market'] = market['name']

    # Save raw input file to log
    log_filename = generate_timestamp_filename(market['code'])
    log_path = os.path.join("database", "log", log_filename)
    input_df.to_csv(log_path, index=False)
    console.print(f"\n[blue]Your original file has been saved for reference as: {log_filename}[/blue]")

    # Process master file
    master_path = os.path.join("database", "master.csv")
    
    if os.path.exists(master_path):
        master_df = pd.read_csv(master_path)
        console.print("\n[blue]Checking for new unique listings...[/blue]")
    else:
        master_df = pd.DataFrame(columns=input_df.columns)
        console.print("\n[blue]Creating new master database...[/blue]")

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
    if not new_listings.empty:
        master_df = pd.concat([master_df, new_listings], ignore_index=True)
        master_df.to_csv(master_path, index=False)
        
        # Create a summary table
        table = Table(title="Processing Summary", show_header=False, title_style="bold green")
        table.add_column("Description", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_row("Total listings in file", str(total_listings))
        table.add_row("New unique properties added", str(len(new_listings)))
        table.add_row("Already in database", str(total_listings - len(new_listings)))
        
        console.print("\n", table)
    else:
        console.print(Panel.fit(
            f"[yellow]We found {total_listings} listings in your file, but all of them are already in your database.[/yellow]",
            border_style="yellow"
        ))

    return True 
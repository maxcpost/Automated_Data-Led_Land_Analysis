#!/usr/bin/env python3
"""
Automated Data-Led Land Analysis (ADLA)
Main entry point for the ADLA system
"""

import sys
import time
import pandas as pd
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import modules at the top level
from modules.datasubmition.process_listings import process_listings, generate_stock_number, validate_stock_numbers
from modules.analytics.analytics import generate_analytics_report
from modules.googledistance.walmart_distance import main as walmart_distance_main
from modules.scraping.fetch import main as fetch_main
from modules.webui.dashboard import launch_dashboard

# Initialize Rich console
console = Console()

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

def clear_screen():
    """Clear the terminal screen."""
    console.clear()

def display_header():
    """Display the ADLA header."""
    header_text = """
[bold blue]Automated Data-Led Land Analysis[/bold blue]
[italic]Your intelligent real estate analysis companion[/italic]
"""
    console.print(Panel(header_text, expand=False, border_style="blue"))

def display_menu():
    """Display the main menu options."""
    table = Table(box=None, expand=True)
    table.add_column("", justify="right", style="cyan", no_wrap=True)
    table.add_column("", style="white")
    
    table.add_row("1", "Process Upstate NY Listings")
    table.add_row("2", "Process I85 Corridor Listings")
    table.add_row("3", "Process Florida Listings")
    table.add_row("4", "Fetch Additional Data")
    table.add_row("5", "Get Distance Data from Google")
    table.add_row("6", "Calculate Analytics Metrics")
    table.add_row("7", "Launch UI Dashboard")
    table.add_row("8", "Exit")
    
    console.print(Panel(table, title="Available Options", border_style="blue", expand=False))

def get_market_info(choice):
    """Convert menu choice to market information."""
    market_info = {
        "1": {"name": "Upstate NY", "code": "NY", "color": "green"},
        "2": {"name": "I85 Corridor", "code": "I85", "color": "blue"},
        "3": {"name": "Florida", "code": "FL", "color": "yellow"}
    }
    return market_info.get(choice)

def display_processing_status(market):
    """Display a spinner while processing."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[{market['color']}]Processing {market['name']} listings...[/{market['color']}]",
            total=None
        )
        process_listings(market=market)

def generate_all_stock_numbers():
    """Generate stock numbers for all listings in the master CSV that don't have one."""
    try:
        # Check if master CSV exists
        master_path = os.path.join("database", "master.csv")
        if not os.path.exists(master_path):
            console.print("[red]Error: Master CSV file not found.[/red]")
            return False
        
        # Read the master CSV
        df = pd.read_csv(master_path)
        console.print(f"[green]Found {len(df)} listings in the master CSV.[/green]")
        
        # Check if StockNumber column exists
        if 'StockNumber' not in df.columns:
            df['StockNumber'] = None
            console.print("[blue]Added StockNumber column to master CSV.[/blue]")
        
        # Count listings without stock numbers
        missing_stock_number_count = df['StockNumber'].isna().sum()
        console.print(f"[blue]Found {missing_stock_number_count} listings without stock numbers.[/blue]")
        
        if missing_stock_number_count == 0:
            console.print("[green]All listings already have stock numbers![/green]")
            return True
        
        # Process each row without a stock number
        rows_updated = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Generating stock numbers...[/cyan]",
                total=missing_stock_number_count
            )
            
            for index, row in df.iterrows():
                if pd.isna(row.get('StockNumber')):
                    # Determine the state code
                    if 'State' in df.columns and pd.notna(row.get('State')):
                        state_code = row['State']
                    elif 'Market' in df.columns and pd.notna(row.get('Market')):
                        # Extract state code from market name
                        if "Upstate NY" in row['Market']:
                            state_code = "NY"
                        elif "I85 Corridor" in row['Market']:
                            state_code = "I85"
                        elif "Florida" in row['Market']:
                            state_code = "FL"
                        else:
                            state_code = "XX"  # Default if unknown
                    else:
                        state_code = "XX"  # Default if no state or market info
                    
                    # Generate stock number
                    df.at[index, 'StockNumber'] = generate_stock_number(df, state_code)
                    rows_updated += 1
                    progress.update(task, advance=1)
        
        # Make sure StockNumber is the first column
        cols = df.columns.tolist()
        cols.remove('StockNumber')
        cols = ['StockNumber'] + cols
        df = df[cols]
        
        # Ensure all stock numbers are unique
        if not validate_stock_numbers(df):
            console.print("[red]Error: Duplicate stock numbers detected. Processing stopped.[/red]")
            return False
            
        # Save the updated CSV
        df.to_csv(master_path, index=False)
        console.print(f"[green]Successfully updated {rows_updated} listings with stock numbers![/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]Error generating stock numbers: {str(e)}[/red]")
        return False

def main():
    """Main entry point for the ADLA system."""
    try:
        while True:
            clear_screen()
            display_header()
            display_menu()
            
            choice = Prompt.ask(
                "\nPlease select an option",
                choices=["1", "2", "3", "4", "5", "6", "7", "8"],
                show_choices=False
            )
            
            if choice in ["1", "2", "3"]:
                market = get_market_info(choice)
                clear_screen()
                display_header()
                display_processing_status(market)
                
                # Pause before returning to menu
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
            
            elif choice == "4":
                clear_screen()
                display_header()
                
                try:
                    # The fetch_main function now handles its own printing with Rich
                    fetch_main()
                    # No need for additional message since fetch_main already shows completion
                except Exception as e:
                    console.print(f"\n[red]Error fetching census data: {str(e)}[/red]")
                
                # Pause before returning to menu
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
            
            elif choice == "5":
                clear_screen()
                display_header()
                console.print("[cyan]Getting distance data from Google for all listings...[/cyan]")
                
                try:
                    walmart_distance_main()
                    console.print("\n[bold green]Distance data fetching completed![/bold green]")
                except Exception as e:
                    console.print(f"\n[red]Error fetching distance data: {str(e)}[/red]")
                
                # Pause before returning to menu
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
                
            elif choice == "6":
                clear_screen()
                display_header()
                console.print("[cyan]Calculating analytics metrics...[/cyan]")
                
                try:
                    generate_analytics_report()
                except Exception as e:
                    console.print(f"\n[red]Error calculating analytics metrics: {str(e)}[/red]")
                
                # Pause before returning to menu
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
            
            elif choice == "7":
                clear_screen()
                display_header()
                console.print("[cyan]Launching UI Dashboard...[/cyan]")
                
                try:
                    launch_dashboard()
                except Exception as e:
                    console.print(f"\n[red]Error launching dashboard: {str(e)}[/red]")
                
                # Return to menu after dashboard is closed
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
            
            elif choice == "8":
                clear_screen()
                print("Thank you for using ADLA. Goodbye!")
                break

    except ImportError as e:
        console.print("[red]Error: Required modules could not be imported.[/red]")
        console.print("[yellow]Please make sure all dependencies are installed correctly.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print("[red]An unexpected error occurred.[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automated Data-Led Land Analysis (ADLA)
Main entry point for the ADLA system
"""

import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
import os

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
    # Create a table for the menu
    table = Table(show_header=False, show_edge=False, box=None)
    table.add_column("Option", style="cyan", width=6)
    table.add_column("Description", style="white")

    # Add menu items
    table.add_row("1", "Process Upstate NY Listings")
    table.add_row("2", "Process I85 Corridor Listings")
    table.add_row("3", "Process Florida Listings")
    table.add_row("4", "Fetch Additional Data")
    table.add_row("5", "Get Distance Data from Google")
    table.add_row("6", "[yellow]Exit[/yellow]")

    # Display the menu in a panel
    console.print(Panel(table, title="[bold]Available Options[/bold]", border_style="cyan"))

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

async def main():
    """Main entry point for the ADLA system."""
    try:
        from modules.datasubmition.process_listings import process_listings
        from modules.scraping.fetch import main as fetch_main
        from modules.googledistance.walmart_distance import main as walmart_distance_main
        
        while True:
            clear_screen()
            display_header()
            display_menu()
            
            choice = Prompt.ask(
                "\nPlease select an option",
                choices=["1", "2", "3", "4", "5", "6"],
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
                console.print("[cyan]Fetching additional census data for all listings...[/cyan]")
                
                try:
                    await fetch_main()
                    console.print("\n[bold green]Census data fetching completed![/bold green]")
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
                    await walmart_distance_main()
                    console.print("\n[bold green]Distance data fetching completed![/bold green]")
                except Exception as e:
                    console.print(f"\n[red]Error fetching distance data: {str(e)}[/red]")
                
                # Pause before returning to menu
                console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
                input()
            
            elif choice == "6":
                clear_screen()
                console.print(Panel.fit(
                    "[bold green]Thank you for using ADLA![/bold green]\n[italic]Have a great day![/italic]",
                    border_style="green"
                ))
                time.sleep(1)
                sys.exit(0)
    
    except ImportError as e:
        console.print("[red]Error: Required modules could not be imported.[/red]")
        console.print("[yellow]Please make sure all dependencies are installed correctly.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print("[red]An unexpected error occurred.[/red]")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

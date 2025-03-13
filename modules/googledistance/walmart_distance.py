"""
Walmart Distance Calculator
Finds the nearest Walmart to each property and calculates travel time
"""

import os
import pandas as pd
import requests
import time
from datetime import datetime
import json
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
import random

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

# Initialize Rich console
console = Console()

# URLs for Google Maps API
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DISTANCE_API_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# Maximum retry attempts for API calls
MAX_RETRIES = 3

def ensure_api_key():
    """Return the Google Maps API key from environment variable."""
    # Get API key from environment variable
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    
    if not api_key:
        console.print("[yellow]Warning: GOOGLE_MAPS_API_KEY environment variable not set.[/yellow]")
        console.print("Please set the GOOGLE_MAPS_API_KEY environment variable to enable Walmart distance calculations.")
        return None
    
    console.print("[green]Using Google Maps API key from environment variable[/green]")
    return api_key

def read_master_csv():
    """Read the master CSV file."""
    try:
        return pd.read_csv('database/master.csv')
    except Exception as e:
        console.print(f"[red]Error reading master CSV: {e}[/red]")
        return None

def make_api_request(url, params, retry_count=0):
    """
    Make an API request with retry logic and exponential backoff.
    
    Args:
        url (str): The API endpoint URL
        params (dict): Request parameters
        retry_count (int): Current retry attempt count
        
    Returns:
        dict: JSON response data or None if failed
    """
    try:
        # Increase timeout for potentially slow connections
        response = requests.get(url, params=params, timeout=30)
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        if retry_count < MAX_RETRIES:
            # Exponential backoff with jitter
            # Wait 2^retry_count + random jitter seconds
            backoff_time = (2 ** retry_count) + random.uniform(0.1, 1.0)
            console.print(f"[yellow]API request failed. Retrying in {backoff_time:.2f} seconds... (Attempt {retry_count + 1}/{MAX_RETRIES})[/yellow]")
            time.sleep(backoff_time)
            return make_api_request(url, params, retry_count + 1)
        else:
            console.print(f"[red]API request failed after {MAX_RETRIES} attempts: {e}[/red]")
            return None

def find_nearest_walmart(latitude, longitude, api_key):
    """Find the nearest Walmart using Google Places API."""
    params = {
        "location": f"{latitude},{longitude}",
        "radius": "50000",  # 50km radius (about 31 miles)
        "keyword": "walmart",
        "type": "store",
        "key": api_key
    }
    
    data = make_api_request(PLACES_API_URL, params)
    
    if data and data['status'] == 'OK' and len(data['results']) > 0:
        nearest_walmart = data['results'][0]
        return {
            'name': nearest_walmart['name'],
            'place_id': nearest_walmart['place_id'],
            'lat': nearest_walmart['geometry']['location']['lat'],
            'lng': nearest_walmart['geometry']['location']['lng'],
            'vicinity': nearest_walmart.get('vicinity', 'Unknown address')
        }
    elif data:
        console.print(f"[yellow]No Walmart found near {latitude}, {longitude}. Status: {data['status']}[/yellow]")
    else:
        console.print(f"[red]Failed to get place data for {latitude}, {longitude}[/red]")
    return None

def get_travel_details(origin_lat, origin_lng, dest_lat, dest_lng, api_key):
    """Get travel time and distance using Google Distance Matrix API."""
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "mode": "driving",
        "units": "imperial",
        "key": api_key
    }
    
    data = make_api_request(DISTANCE_API_URL, params)
    
    if data and data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
        element = data['rows'][0]['elements'][0]
        return {
            'distance_text': element['distance']['text'],
            'distance_value': element['distance']['value'],  # in meters
            'duration_text': element['duration']['text'],
            'duration_value': element['duration']['value']   # in seconds
        }
    elif data:
        console.print(f"[yellow]Failed to get travel details. Status: {data.get('status', 'Unknown')}[/yellow]")
    else:
        console.print(f"[red]Failed to get distance data for {origin_lat}, {origin_lng} to {dest_lat}, {dest_lng}[/red]")
    return None

def update_master_csv(df, row_index, walmart_data, travel_data):
    """Update the master CSV with Walmart and travel data."""
    try:
        # Only add the address and travel details (not name or coordinates)
        if 'Nearest_Walmart_Address' not in df.columns:
            df['Nearest_Walmart_Address'] = None
        if 'Nearest_Walmart_Distance_Miles' not in df.columns:
            df['Nearest_Walmart_Distance_Miles'] = None
        if 'Nearest_Walmart_Travel_Time_Minutes' not in df.columns:
            df['Nearest_Walmart_Travel_Time_Minutes'] = None
        
        # Update Walmart address
        df.loc[row_index, 'Nearest_Walmart_Address'] = walmart_data['vicinity']
        
        # Update travel data
        distance_miles = travel_data['distance_value'] / 1609.34  # Convert meters to miles
        travel_time_minutes = travel_data['duration_value'] / 60  # Convert seconds to minutes
        
        df.loc[row_index, 'Nearest_Walmart_Distance_Miles'] = round(distance_miles, 2)
        df.loc[row_index, 'Nearest_Walmart_Travel_Time_Minutes'] = round(travel_time_minutes, 2)
        
        # Save the updated CSV
        df.to_csv('database/master.csv', index=False)
        return True
    except Exception as e:
        console.print(f"[red]Error updating master CSV: {e}[/red]")
        return False

def main():
    """Main function to process all rows in the CSV."""
    console.clear()
    console.print("[bold blue]Walmart Distance Finder[/bold blue]")
    console.print("[italic]Finding the nearest Walmart and travel time for each property[/italic]\n")
    
    # Get API key
    api_key = ensure_api_key()
    if not api_key:
        console.print("[red]Error: Google Maps API key not set. Cannot proceed.[/red]")
        console.print("Please set the GOOGLE_MAPS_API_KEY environment variable and try again.")
        return
    
    # Get all rows from the CSV
    df = read_master_csv()
    if df is None:
        console.print("[red]Error reading CSV file[/red]")
        return
    
    # Determine which rows need processing (those without Walmart data)
    rows_to_process = []
    for index, row in df.iterrows():
        if pd.isna(row.get('Nearest_Walmart_Address', None)) or pd.isna(row.get('Nearest_Walmart_Travel_Time_Minutes', None)):
            if not pd.isna(row.get('Latitude', None)) and not pd.isna(row.get('Longitude', None)):
                rows_to_process.append((index, row))
    
    if not rows_to_process:
        console.print("[green]All listings already have Walmart distance data![/green]")
        return
    
    console.print(f"[cyan]Found {len(rows_to_process)} listings that need Walmart distance data[/cyan]")
    
    # Process each row with progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Processing listings...", total=len(rows_to_process))
        
        for i, (index, row) in enumerate(rows_to_process):
            latitude = row['Latitude']
            longitude = row['Longitude']
            
            progress.update(task, description=f"[cyan]Processing listing {i+1}/{len(rows_to_process)}...")
            
            # Find nearest Walmart
            walmart_data = find_nearest_walmart(latitude, longitude, api_key)
            
            if walmart_data:
                # Get travel details
                travel_data = get_travel_details(
                    latitude, longitude, 
                    walmart_data['lat'], walmart_data['lng'], 
                    api_key
                )
                
                if travel_data:
                    # Update master CSV
                    if update_master_csv(df, index, walmart_data, travel_data):
                        progress.update(task, advance=1)
                    else:
                        progress.update(task, advance=1, description=f"[red]Failed to update listing {i+1}/{len(rows_to_process)}")
                else:
                    progress.update(task, advance=1, description=f"[yellow]No travel data for listing {i+1}/{len(rows_to_process)}")
            else:
                progress.update(task, advance=1, description=f"[yellow]No Walmart found for listing {i+1}/{len(rows_to_process)}")
            
            # Add a larger delay between API calls to avoid rate limiting
            # Google Maps API has a limit of 50 requests per second, but best practice is to be conservative
            time.sleep(1.5)  # Increased from 0.5 to 1.5 seconds
    
    console.print("\n[green]Walmart distance data processing completed![/green]")

if __name__ == "__main__":
    main() 
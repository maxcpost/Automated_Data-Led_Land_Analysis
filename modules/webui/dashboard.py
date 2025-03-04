"""
Dashboard module for the web UI.
Handles web server, routes, and data processing for the dashboard.
"""

import os
import pandas as pd
import threading
import webbrowser
from flask import Flask, render_template, jsonify, request
from rich.console import Console

# Initialize console for output
console = Console()

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

def load_data():
    """Load data from master.csv for the dashboard."""
    try:
        master_path = os.path.join("database", "master.csv")
        if not os.path.exists(master_path):
            console.print(f"[red]Error: Master CSV file not found at {master_path}[/red]")
            return None
        
        console.print(f"[green]Loading data from {master_path}...[/green]")
        df = pd.read_csv(master_path)
        console.print(f"[green]Successfully loaded data: {len(df)} rows[/green]")
        return df
    except Exception as e:
        console.print(f"[red]Error loading data: {str(e)}[/red]")
        return None

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/listings')
def get_listings():
    """API endpoint to get listings data."""
    try:
        df = load_data()
        
        if df is None:
            return jsonify({"error": "Failed to load data"}), 500
        
        # Get filter parameter (all, priced, nonpriced)
        filter_type = request.args.get('filter', 'all')
        console.print(f"[blue]Filtering listings by: {filter_type}[/blue]")
        
        # Clone DataFrame to avoid modifying the original
        filtered_df = df.copy()
        
        # Apply filters
        if filter_type == 'priced':
            if 'Price Per Acre' not in filtered_df.columns:
                console.print("[yellow]Warning: 'Price Per Acre' column not found in DataFrame[/yellow]")
                return jsonify({"error": "Price Per Acre column not found"}), 500
            filtered_df = filtered_df[filtered_df['Price Per Acre'].notna()]
            console.print(f"[blue]Found {len(filtered_df)} priced listings[/blue]")
        elif filter_type == 'nonpriced':
            if 'Price Per Acre' not in filtered_df.columns:
                console.print("[yellow]Warning: 'Price Per Acre' column not found in DataFrame[/yellow]")
                return jsonify({"error": "Price Per Acre column not found"}), 500
            filtered_df = filtered_df[filtered_df['Price Per Acre'].isna()]
            console.print(f"[blue]Found {len(filtered_df)} non-priced listings[/blue]")
        else:
            console.print(f"[blue]Showing all {len(filtered_df)} listings[/blue]")
        
        # Ensure all required columns exist
        required_columns = [
            'StockNumber', 
            'For Sale Price', 
            'Land Area (AC)',
            'Price Per Acre', 
            'Demand for Attainable Rent', 
            'Housing Gap', 
            'Home Affordability Gap', 
            'Weighted Demand and Convenience',
            'Composite Score'
        ]
        
        # Check and log missing columns
        missing_columns = [col for col in required_columns if col not in filtered_df.columns]
        if missing_columns:
            console.print(f"[yellow]Warning: Missing columns in DataFrame: {missing_columns}[/yellow]")
            console.print(f"[blue]Available columns: {list(filtered_df.columns)}[/blue]")
            
        # Create a dictionary to map actual column names to display names
        display_names = {
            'For Sale Price': 'Sale Price',
            'Land Area (AC)': 'Acres',
            'Price Per Acre': 'Price/Acre',
            'Demand for Attainable Rent': 'Demand',
            'Housing Gap': 'Housing Gap',
            'Home Affordability Gap': 'Affordability',
            'Weighted Demand and Convenience': 'Convenience',
            'Composite Score': 'Score'
        }
        
        # For missing columns, add placeholders
        for col in required_columns:
            if col not in filtered_df.columns:
                filtered_df[col] = None
                console.print(f"[yellow]Added placeholder for missing column: {col}[/yellow]")
        
        # Sort by Composite Score (descending)
        if 'Composite Score' in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by='Composite Score', ascending=False)
            console.print("[blue]Sorted listings by Composite Score (descending)[/blue]")
        
        # Select and rename columns for the response
        columns_to_show = {col: display_names.get(col, col) for col in required_columns if col in filtered_df.columns}
        result_df = filtered_df[list(columns_to_show.keys())].copy()
        
        # Format numeric values
        try:
            # Helper function to safely format numeric values
            def safe_format_numeric(value, format_type='number', precision=2):
                if pd.isna(value):
                    return "N/A"
                try:
                    # Try to convert to numeric
                    num_value = pd.to_numeric(value, errors='coerce')
                    if pd.isna(num_value):  # If conversion failed
                        return str(value)
                    
                    # Format based on type
                    if format_type == 'currency':
                        if num_value == 0:
                            return "N/A"
                        return f"${num_value:,.0f}"
                    elif format_type == 'percent':
                        return f"{num_value:.2%}"
                    else:  # regular number
                        if num_value == 0:
                            return "0.00"
                        format_str = f"{{:,.{precision}f}}"
                        return format_str.format(num_value)
                except:
                    # Return as string if anything fails
                    return str(value) if value is not None else "N/A"
            
            # Format currency fields
            if 'For Sale Price' in result_df.columns:
                result_df['For Sale Price'] = result_df['For Sale Price'].apply(
                    lambda x: safe_format_numeric(x, 'currency')
                )
                
            if 'Price Per Acre' in result_df.columns:
                result_df['Price Per Acre'] = result_df['Price Per Acre'].apply(
                    lambda x: safe_format_numeric(x, 'currency')
                )
            
            # Format Composite Score (special handling for 0-1 range)
            if 'Composite Score' in result_df.columns:
                result_df['Composite Score'] = result_df['Composite Score'].apply(
                    lambda x: safe_format_numeric(x, precision=2)
                )
            
            # Format other numeric columns
            for col in result_df.columns:
                if col not in ['For Sale Price', 'Price Per Acre', 'Composite Score', 'StockNumber']:
                    result_df[col] = result_df[col].apply(
                        lambda x: safe_format_numeric(x)
                    )
            
            # Rename columns for display
            result_df = result_df.rename(columns=columns_to_show)
            
            # Convert to dictionary for JSON response
            results = result_df.to_dict(orient='records')
            console.print(f"[green]Successfully prepared {len(results)} listings for display[/green]")
            
            return jsonify({"listings": results})
        except Exception as e:
            console.print(f"[red]Error formatting data: {str(e)}[/red]")
            return jsonify({"error": f"Error formatting data: {str(e)}"}), 500
            
    except Exception as e:
        console.print(f"[red]Error processing listings: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/property/<stock_number>')
def get_property_details(stock_number):
    """API endpoint to get detailed information for a specific property."""
    try:
        df = load_data()
        
        if df is None:
            return jsonify({"error": "Failed to load data"}), 500
        
        # Find the property with the given stock number
        if 'StockNumber' not in df.columns:
            return jsonify({"error": "StockNumber column not found in data"}), 500
        
        # Convert to strings for comparison to handle potential numeric values
        property_data = df[df['StockNumber'].astype(str) == str(stock_number)]
        
        if property_data.empty:
            console.print(f"[yellow]Property with stock number {stock_number} not found[/yellow]")
            return jsonify({"error": f"Property with stock number {stock_number} not found"}), 404
        
        # Get the first matching property (should be only one)
        property_row = property_data.iloc[0]
        
        # Convert to dictionary with proper formatting
        result = {}
        
        # Helper function to safely format numeric values (reusing from get_listings)
        def safe_format_numeric(value, format_type='number', precision=2):
            if pd.isna(value):
                return "N/A"
            try:
                # Try to convert to numeric
                num_value = pd.to_numeric(value, errors='coerce')
                if pd.isna(num_value):  # If conversion failed
                    return str(value)
                
                # Format based on type
                if format_type == 'currency':
                    if num_value == 0:
                        return "N/A"
                    return f"${num_value:,.0f}"
                elif format_type == 'percent':
                    return f"{num_value:.2%}"
                else:  # regular number
                    if num_value == 0:
                        return "0.00"
                    format_str = f"{{:,.{precision}f}}"
                    return format_str.format(num_value)
            except:
                # Return as string if anything fails
                return str(value) if value is not None else "N/A"
                
        # Organize data into categories for better display
        categories = {
            "Property Information": [
                "StockNumber", "Property Address", "City", "State", "Zip", 
                "For Sale Price", "Land Area (AC)", "Zoning", "Improvements",
                "Price Per Acre", "County"
            ],
            "Location Details": [
                "Latitude", "Longitude", "Market", "Sub-Market", "Nearest Town", 
                "Nearest_Walmart_Distance_Miles", "Nearest_Walmart_Travel_Time_Minutes"
            ],
            "Demographics Data (5 min)": [
                "TotPop_5", "TotHUs_5", "MedianGrossRent_5", "Age0_4_5", "Age5_9_5", 
                "Age10_14_5", "Age15_19_5", "MedianHHInc_5", "MobileHomesPerK_5"
            ],
            "Demographics Data (10 min)": [
                "TotPop_10", "TotHUs_10", "MedianGrossRent_10", "Age0_4_10", "Age5_9_10", 
                "Age10_14_10", "Age15_19_10", "MedianHHInc_10", "MobileHomesPerK_10"
            ],
            "Demographics Data (15 min)": [
                "TotPop_15", "TotHUs_15", "MedianGrossRent_15", "Age0_4_15", "Age5_9_15", 
                "Age10_14_15", "Age15_19_15", "MedianHHInc_15", "MobileHomesPerK_15"
            ],
            "Demographics Data (20 min)": [
                "TotPop_20", "TotHUs_20", "MedianGrossRent_20", "Age0_4_20", "Age5_9_20", 
                "Age10_14_20", "Age15_19_20", "MedianHHInc_20", "MobileHomesPerK_20"
            ],
            "Demographics Data (25 min)": [
                "TotPop_25", "TotHUs_25", "MedianGrossRent_25", "Age0_4_25", "Age5_9_25", 
                "Age10_14_25", "Age15_19_25", "MedianHHInc_25", "MobileHomesPerK_25"
            ],
            "Analytics Metrics": [
                "Demand for Attainable Rent", "Housing Gap", "Home Affordability Gap", 
                "Weighted Demand and Convenience", "Composite Score"
            ]
        }
        
        # Display names mapping for better readability
        display_names = {
            "For Sale Price": "Sale Price",
            "Land Area (AC)": "Acres",
            "Price Per Acre": "Price per Acre",
            "Demand for Attainable Rent": "Demand for Attainable Rent",
            "Housing Gap": "Housing Gap (units per person)",
            "Home Affordability Gap": "Home Affordability Gap",
            "Weighted Demand and Convenience": "Weighted Demand & Convenience",
            "Composite Score": "Composite Score",
            "Latitude": "Latitude",
            "Longitude": "Longitude",
            "TotPop_5": "Total Population",
            "TotHUs_5": "Total Housing Units",
            "MedianGrossRent_5": "Median Gross Rent",
            "MedianHHInc_5": "Median Household Income",
            "MobileHomesPerK_5": "Mobile Homes per 1000",
            "Nearest_Walmart_Distance_Miles": "Distance to Walmart (miles)",
            "Nearest_Walmart_Travel_Time_Minutes": "Travel Time to Walmart (minutes)"
        }
        
        # Format currency fields specially
        currency_fields = [
            "For Sale Price", "Price Per Acre", "MedianGrossRent_5", "MedianGrossRent_10", 
            "MedianGrossRent_15", "MedianGrossRent_20", "MedianGrossRent_25",
            "MedianHHInc_5", "MedianHHInc_10", "MedianHHInc_15", "MedianHHInc_20", "MedianHHInc_25",
            "Home Affordability Gap"
        ]
        
        # Precision settings for different metrics
        precision_settings = {
            "Housing Gap": 4,
            "Composite Score": 2,
            "Nearest_Walmart_Distance_Miles": 1,
            "Nearest_Walmart_Travel_Time_Minutes": 1
        }
        
        # Create the categorized result
        result["categories"] = {}
        for category, fields in categories.items():
            result["categories"][category] = []
            for field in fields:
                if field in property_row.index:
                    # Get display name (or use field name if no mapping exists)
                    display_name = display_names.get(field, field.replace('_', ' '))
                    
                    # Format the value based on field type
                    if field in currency_fields:
                        value = safe_format_numeric(property_row[field], 'currency')
                    else:
                        # Use specific precision settings for certain fields
                        precision = precision_settings.get(field, 2)
                        value = safe_format_numeric(property_row[field], precision=precision)
                    
                    result["categories"][category].append({
                        "field": field,
                        "name": display_name,
                        "value": value
                    })
        
        # Add raw latitude and longitude for the map
        try:
            lat = float(property_row['Latitude'])
            lng = float(property_row['Longitude'])
            result["map"] = {"latitude": lat, "longitude": lng}
        except:
            result["map"] = None
            console.print("[yellow]Warning: Could not parse coordinates for map[/yellow]")
        
        # Add property summary for heading
        result["summary"] = {
            "stockNumber": str(property_row['StockNumber']),
            "location": f"{property_row['City'] if 'City' in property_row and pd.notna(property_row['City']) else 'Unknown'}, {property_row['State'] if 'State' in property_row and pd.notna(property_row['State']) else 'Unknown'}",
            "price": safe_format_numeric(property_row['For Sale Price'], 'currency') if 'For Sale Price' in property_row else "N/A",
            "acres": safe_format_numeric(property_row['Land Area (AC)']) if 'Land Area (AC)' in property_row else "N/A",
            "score": safe_format_numeric(property_row['Composite Score'], precision=2) if 'Composite Score' in property_row else "N/A"
        }
        
        console.print(f"[green]Successfully retrieved property details for {stock_number}[/green]")
        return jsonify(result)
    
    except Exception as e:
        console.print(f"[red]Error retrieving property details: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/property/<stock_number>')
def property_detail(stock_number):
    """Property detail page."""
    return render_template('property.html', stock_number=stock_number)

def open_browser():
    """Open web browser to the dashboard."""
    webbrowser.open('http://127.0.0.1:5000/')

def launch_dashboard():
    """Launch the dashboard web server."""
    try:
        # Check if data is available
        df = load_data()
        if df is None:
            console.print("[red]Error: Could not load master.csv file. Please make sure it exists and run analytics first.[/red]")
            return False
        
        console.print("[cyan]Launching web dashboard...[/cyan]")
        
        # Start browser in a separate thread
        threading.Timer(1.0, open_browser).start()
        
        # Start Flask server
        app.run(debug=False, host='127.0.0.1', port=5000)
        
        return True
    except Exception as e:
        console.print(f"[red]Error launching dashboard: {str(e)}[/red]")
        return False

if __name__ == '__main__':
    launch_dashboard() 
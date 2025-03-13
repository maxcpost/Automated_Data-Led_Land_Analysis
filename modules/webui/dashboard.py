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
import json
import sys
import importlib.util
from pathlib import Path
import plotly.utils
import plotly.graph_objects as go
import requests  # Add this import for making API requests to OpenAI

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

# Initialize console for output
console = Console()

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Define path to the opportunity_viz module and simple_viz module
opportunity_viz_path = Path(__file__).parent.parent / "analytics" / "opportunity_viz.py"
simple_viz_path = Path(__file__).parent.parent / "analytics" / "simple_viz.py"

# Dynamically import the opportunity_viz module
spec = importlib.util.spec_from_file_location("opportunity_viz", opportunity_viz_path)
opportunity_viz = importlib.util.module_from_spec(spec)
sys.modules["opportunity_viz"] = opportunity_viz
spec.loader.exec_module(opportunity_viz)

# Dynamically import the simple_viz module
spec_simple = importlib.util.spec_from_file_location("simple_viz", simple_viz_path)
simple_viz = importlib.util.module_from_spec(spec_simple)
sys.modules["simple_viz"] = simple_viz
spec_simple.loader.exec_module(simple_viz)

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
            "Contact Information": [
                "Sale Company Name", "Sale Company Contact", "Sale Company Phone"
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
            "Sale Company Name": "Listing Company",
            "Sale Company Contact": "Contact Person",
            "Sale Company Phone": "Contact Phone",
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
                if field in property_row:
                    display_name = display_names.get(field, field)
                    
                    # Get the value
                    value = property_row[field]
                    
                    # Format value if needed
                    if field in ["For Sale Price", "Last Sale Price"]:
                        value = safe_format_numeric(value, format_type='currency')
                    elif "Percent" in field or "%" in field:
                        value = safe_format_numeric(value, format_type='percent')
                    else:
                        # Use specific precision settings for certain fields
                        precision = precision_settings.get(field, 2)
                        value = safe_format_numeric(property_row[field], precision=precision)
                    
                    result["categories"][category].append({
                        "field": field,
                        "name": display_name,
                        "value": value
                    })
        
        # Directly add Contact Information category
        result["categories"]["Contact Information"] = [
            {
                "field": "Sale Company Name",
                "name": "Listing Company",
                "value": str(property_row.get("Sale Company Name", "N/A"))
            },
            {
                "field": "Sale Company Contact",
                "name": "Contact Person",
                "value": str(property_row.get("Sale Company Contact", "N/A"))
            },
            {
                "field": "Sale Company Phone",
                "name": "Contact Phone",
                "value": str(property_row.get("Sale Company Phone", "N/A"))
            }
        ]
        
        # Add raw latitude and longitude for the map
        try:
            lat = float(property_row['Latitude'])
            lng = float(property_row['Longitude'])
            result["map"] = {"latitude": lat, "longitude": lng}
        except:
            result["map"] = None
            console.print("[yellow]Warning: Could not parse coordinates for map[/yellow]")
        
        # Create summary data for the header
        summary = {
            "stockNumber": property_row.get("StockNumber", ""),
            "location": f"{property_row.get('City', '')}, {property_row.get('State', '')}",
            "price": safe_format_numeric(property_row.get("For Sale Price"), format_type='currency'),
            "acres": safe_format_numeric(property_row.get("Land Area (AC)")),
            "score": safe_format_numeric(property_row.get("Composite Score")),
            "company": str(property_row.get("Sale Company Name", "N/A")),
            "phone": str(property_row.get("Sale Company Phone", "N/A"))
        }
        
        # Debug the summary
        console.print(f"[blue]Summary data: {summary}[/blue]")
        
        # Assign summary to result
        result["summary"] = summary
        
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
    # Get Google Maps API key from environment variable
    google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return render_template('property.html', stock_number=stock_number, google_maps_api_key=google_maps_api_key)

@app.route('/opportunity')
def opportunity_dashboard():
    """Opportunity assessment dashboard page."""
    return render_template('opportunity.html')

@app.route('/api/opportunity/visualizations')
def opportunity_visualizations():
    """
    Retrieve all opportunity visualizations.
    """
    try:
        console.print("[blue]Retrieving opportunity visualizations...[/blue]")
        visualizations = opportunity_viz.create_all_visualizations()
        
        # Check if visualizations dictionary is empty
        if not visualizations:
            console.print("[yellow]Warning: No visualizations were created[/yellow]")
            return jsonify({"error": "No visualizations could be created"}), 500
        
        # Convert Plotly figures to JSON
        result = {}
        for name, fig in visualizations.items():
            if fig is not None:
                try:
                    console.print(f"[blue]Converting {name} visualization to JSON...[/blue]")
                    result[name] = json.loads(fig.to_json())
                    console.print(f"[green]Successfully converted {name} visualization[/green]")
                except Exception as e:
                    console.print(f"[red]Error converting {name} visualization to JSON: {str(e)}[/red]")
                    import traceback
                    traceback.print_exc()
            else:
                console.print(f"[yellow]Skipping {name} visualization as it is None[/yellow]")
        
        console.print(f"[green]Returning {len(result)} visualizations[/green]")
        return jsonify(result)
    except Exception as e:
        console.print(f"[red]Error in opportunity_visualizations route: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/opportunity/properties')
def get_opportunity_properties():
    """API endpoint to get list of properties for the radar chart selector."""
    try:
        df = load_data()
        
        if df is None:
            return jsonify({"error": "Failed to load data"}), 500
        
        # Get property information for the selector
        properties = []
        
        for idx, row in df.iterrows():
            name = row.get('StockNumber', f'Property {idx}')
            if 'Property Address' in df.columns:
                name += f" - {row.get('Property Address', '')}"
            
            properties.append({
                'id': idx,  # Use index as ID
                'name': name
            })
        
        return jsonify({"properties": properties})
    except Exception as e:
        console.print(f"[red]Error getting properties: {str(e)}[/red]")
        return jsonify({"error": str(e)}), 500

@app.route('/api/opportunity/radar-chart/<int:property_id>')
def opportunity_radar_chart(property_id):
    """
    Generate a radar chart for a specific property.
    """
    try:
        console.print(f"[blue]Generating radar chart for property ID {property_id}...[/blue]")
        # Load master data
        df = opportunity_viz.load_master_data()
        if df is None:
            console.print("[red]Failed to load master data[/red]")
            return jsonify({"error": "Failed to load property data"}), 500
        
        # Check if property_id exists in the dataframe
        if property_id >= len(df):
            console.print(f"[red]Property ID {property_id} not found in dataset[/red]")
            return jsonify({"error": f"Property ID {property_id} not found"}), 404
        
        # Generate radar chart
        fig = opportunity_viz.create_radar_chart(df, property_id)
        if fig is None:
            console.print(f"[red]Failed to create radar chart for property ID {property_id}[/red]")
            return jsonify({"error": "Failed to create radar chart"}), 500
        
        # Convert to JSON
        try:
            chart_json = json.loads(fig.to_json())
            console.print(f"[green]Successfully created radar chart for property ID {property_id}[/green]")
            return jsonify(chart_json)
        except Exception as e:
            console.print(f"[red]Error converting radar chart to JSON: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error converting chart to JSON: {str(e)}"}), 500
    except Exception as e:
        console.print(f"[red]Error in opportunity_radar_chart route: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/property/<stock_number>/opportunity')
def get_property_opportunity(stock_number):
    """API endpoint to get opportunity visualizations for a specific property."""
    try:
        console.print(f"[blue]Generating opportunity visualizations for property {stock_number}...[/blue]")
        
        # Using the new simple_viz module instead of complex processing
        visualizations = simple_viz.create_property_visualizations(stock_number)
        
        if not visualizations:
            console.print(f"[yellow]No visualizations created for property {stock_number}, falling back to basic visuals[/yellow]")
            # Try to load the property data directly to create basic visuals
            df = load_data()
            if df is None:
                return jsonify({"error": "Failed to load data"}), 500
                
            # Find the property with the given stock number
            if 'StockNumber' not in df.columns:
                return jsonify({"error": "StockNumber column not found in data"}), 500
                
            property_data = df[df['StockNumber'].astype(str) == str(stock_number)]
            if property_data.empty:
                return jsonify({"error": f"Property with stock number {stock_number} not found"}), 404
                
            # Create very basic visualizations as a last resort
            property_row = property_data.iloc[0]
            
            # Create a simple pie chart for opportunity score components
            try:
                # Basic opportunity breakdown
                opportunity_components = {
                    "Location": 0.3,
                    "Demand": 0.25,
                    "Value": 0.2,
                    "Growth": 0.15,
                    "Risk": 0.1
                }
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(opportunity_components.keys()),
                    values=list(opportunity_components.values()),
                    hole=.3
                )])
                
                fig_pie.update_layout(
                    title_text=f"Opportunity Components for Property {stock_number}"
                )
                
                visualizations['radar_chart'] = fig_pie
                
                # Basic bar chart of property attributes
                key_metrics = {
                    "Size (acres)": property_row.get("Land Area (AC)", 0),
                    "Price ($M)": property_row.get("For Sale Price", 0) / 1000000 if "For Sale Price" in property_row else 0,
                    "Score": property_row.get("Composite Score", 0) * 10  # Scale to be visible alongside other metrics
                }
                
                fig_bar = go.Figure([go.Bar(
                    x=list(key_metrics.keys()),
                    y=list(key_metrics.values()),
                    marker_color=['blue', 'green', 'red']
                )])
                
                fig_bar.update_layout(
                    title_text=f"Key Metrics for Property {stock_number}"
                )
                
                visualizations['quadrant_chart'] = fig_bar
                
                # Create empty placeholder visualizations for the remaining charts
                fig_placeholder1 = go.Figure()
                fig_placeholder1.add_annotation(
                    x=0.5, y=0.5,
                    text="Data analysis visualization could not be generated",
                    showarrow=False,
                    font=dict(size=14)
                )
                fig_placeholder1.update_layout(
                    title_text="Growth vs. Housing Gap Analysis",
                    xaxis=dict(showticklabels=False),
                    yaxis=dict(showticklabels=False)
                )
                visualizations['growth_gap_chart'] = fig_placeholder1
                
                fig_placeholder2 = go.Figure()
                fig_placeholder2.add_annotation(
                    x=0.5, y=0.5,
                    text="Development potential visualization could not be generated",
                    showarrow=False,
                    font=dict(size=14)
                )
                fig_placeholder2.update_layout(
                    title_text="Competitive Advantage Matrix",
                    xaxis=dict(showticklabels=False),
                    yaxis=dict(showticklabels=False)
                )
                visualizations['advantage_chart'] = fig_placeholder2
                
            except Exception as e:
                console.print(f"[red]Error creating fallback visualizations: {str(e)}[/red]")
                import traceback
                traceback.print_exc()
        
        # Convert Plotly figures to JSON
        result = {}
        for name, fig in visualizations.items():
            if fig is not None:
                try:
                    console.print(f"[blue]Converting {name} visualization to JSON...[/blue]")
                    result[name] = json.loads(fig.to_json())
                    console.print(f"[green]Successfully converted {name} visualization[/green]")
                except Exception as e:
                    console.print(f"[red]Error converting {name} visualization to JSON: {str(e)}[/red]")
                    # Create simple error visualization
                    error_fig = go.Figure()
                    error_fig.add_annotation(
                        x=0.5, y=0.5,
                        text=f"Error converting visualization: {str(e)}",
                        showarrow=False,
                        font=dict(size=14, color="red")
                    )
                    error_fig.update_layout(
                        title_text=f"Error in {name}",
                        xaxis=dict(showticklabels=False),
                        yaxis=dict(showticklabels=False)
                    )
                    try:
                        result[name] = json.loads(error_fig.to_json())
                    except:
                        console.print(f"[red]Could not create error visualization for {name}[/red]")
            else:
                console.print(f"[yellow]Skipping {name} visualization as it is None[/yellow]")
                # Create empty visualization
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    x=0.5, y=0.5,
                    text="No data available for this visualization",
                    showarrow=False,
                    font=dict(size=14)
                )
                empty_fig.update_layout(
                    title_text=f"No Data - {name}",
                    xaxis=dict(showticklabels=False),
                    yaxis=dict(showticklabels=False)
                )
                try:
                    result[name] = json.loads(empty_fig.to_json())
                except:
                    console.print(f"[red]Could not create empty visualization for {name}[/red]")
        
        console.print(f"[green]Returning {len(result)} visualizations for property {stock_number}[/green]")
        return jsonify(result)
    
    except Exception as e:
        console.print(f"[red]Error in property opportunity endpoint: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        
        # Return error visualizations instead of an error response
        error_visualizations = {}
        
        # Create simple error visualizations for each expected chart
        for name in ['radar_chart', 'quadrant_chart', 'growth_gap_chart', 'advantage_chart']:
            error_fig = go.Figure()
            error_fig.add_annotation(
                x=0.5, y=0.5,
                text=f"Error generating visualization: {str(e)}",
                showarrow=False,
                font=dict(size=14, color="red")
            )
            error_fig.update_layout(
                title_text=f"Error in {name}",
                xaxis=dict(showticklabels=False),
                yaxis=dict(showticklabels=False)
            )
            try:
                error_visualizations[name] = json.loads(error_fig.to_json())
            except:
                # If even this fails, we'll have to skip it
                pass
        
        return jsonify(error_visualizations)

@app.route('/api/property/<stock_number>/ai-report', methods=['GET'])
def generate_property_ai_report(stock_number):
    """Generate an AI analysis report for a property using OpenAI API."""
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
        property_row = property_data.iloc[0].to_dict()
        
        # Define the prompt for OpenAI
        prompt = build_ai_report_prompt(property_row)
        
        # Call OpenAI API
        report = call_openai_api(prompt)
        
        # Return the generated report
        return jsonify({
            "report": report,
            "stockNumber": stock_number
        })
    except Exception as e:
        console.print(f"[red]Error generating AI report: {str(e)}[/red]")
        return jsonify({"error": f"Error generating AI report: {str(e)}"}), 500

def build_ai_report_prompt(property_data):
    """Build a prompt for the OpenAI API to generate a property report."""
    # Start with context about communities we're trying to build
    prompt = """
You are an expert real estate analyst specializing in affordable community development. 
Analyze the following property data to determine its suitability for building a community.
We are focused on creating affordable housing communities in areas with:
1. Growing population or steady demographics
2. Good access to amenities (like Walmart within reasonable distance)
3. Areas where there is a demand for affordable housing
4. Favorable price per acre for development

Based ONLY on the provided data, create a comprehensive analysis covering:
- Overall suitability score (1-10) with explanation
- Key strengths and weaknesses of the property
- Demographic analysis and what it means for community development
- Development potential based on size, price, and location
- Recommended next steps for further evaluation

Property Data:
"""
    
    # Add the property data to the prompt
    for key, value in property_data.items():
        # Skip NaN values
        if pd.notna(value):
            prompt += f"{key}: {value}\n"
    
    return prompt

def call_openai_api(prompt):
    """Call the OpenAI API to generate a report based on the prompt."""
    # OpenAI API endpoint
    url = "https://api.openai.com/v1/chat/completions"
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[yellow]Warning: OPENAI_API_KEY environment variable not set.[/yellow]")
        console.print("Please set the OPENAI_API_KEY environment variable to enable AI reports.")
        return "API key not configured. Please set the OPENAI_API_KEY environment variable to enable AI reports."
    
    # Prepare the request payload
    payload = {
        "model": "gpt-4",  # Using GPT-4 for comprehensive analysis
        "messages": [
            {
                "role": "system",
                "content": "You are a real estate analysis assistant that provides detailed, professional property evaluations for community development potential."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        result = response.json()
        # Extract the response text
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            console.print("[red]Error: Unexpected API response format[/red]")
            return "Error: Unable to generate report due to API response format."
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]API request error: {str(e)}[/red]")
        return f"Error calling OpenAI API: {str(e)}"

def run_dashboard():
    """Run the web dashboard."""
    console.print("[green]Launching web dashboard...[/green]")
    # Use port 5001 instead of the default 5000 to avoid conflicts with AirPlay on macOS
    app.run(host='0.0.0.0', port=5001)

def launch_dashboard():
    """Launch the dashboard in a browser."""
    # Load data first
    df = load_data()
    if df is None:
        console.print("[red]Failed to load data. Dashboard will not be launched.[/red]")
        return False
    
    console.print("[green]Launching web dashboard...[/green]")
    
    # Start the server in a separate thread
    threading.Thread(target=run_dashboard, daemon=True).start()
    
    # Open browser after a short delay
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5001')).start()
    
    return True

if __name__ == '__main__':
    launch_dashboard() 
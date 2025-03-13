"""
Simple Visualization module for generating basic visualizations
when more complex visualizations are not available.
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console

# Initialize rich console for output
console = Console()

def load_master_data():
    """Load the master CSV file."""
    try:
        master_path = os.path.join("database", "master.csv")
        if not os.path.exists(master_path):
            console.print(f"[red]Error: Master CSV file not found at {master_path}[/red]")
            return None
        
        console.print(f"[green]Loading data from {master_path}...[/green]")
        df = pd.read_csv(master_path)
        console.print(f"[green]Successfully loaded data with {len(df)} rows[/green]")
        return df
    except Exception as e:
        console.print(f"[red]Error loading data: {str(e)}[/red]")
        return None

def create_simple_radar_chart(property_data):
    """
    Create a simple radar chart for a property showing its key metrics.
    
    Parameters:
    - property_data: DataFrame row containing property data
    """
    # Define metrics to display if available
    potential_metrics = {
        'Population': 'TotPop_15',
        'Housing Units': 'TotHUs_15', 
        'Income Level': 'MedianHHInc_15',
        'Land Size': 'Land Area (AC)',
        'Opportunity Score': 'Composite Score'
    }
    
    # Collect available metrics
    metrics = []
    values = []
    
    for label, field in potential_metrics.items():
        if field in property_data and pd.notna(property_data[field]):
            metrics.append(label)
            # Scale values to be between 0 and 1 for radar chart
            if field == 'Composite Score':
                # Score is already between 0-1
                values.append(float(property_data[field]))
            elif field == 'Land Area (AC)':
                # Scale acres to 0-1 range assuming most properties < 200 acres
                acres = float(property_data[field])
                values.append(min(acres / 200, 1.0))
            elif field == 'MedianHHInc_15':
                # Scale income assuming $150k is high
                income = float(property_data[field])
                values.append(min(income / 150000, 1.0))
            elif field == 'TotPop_15':
                # Scale population assuming 500k is high
                pop = float(property_data[field])
                values.append(min(pop / 500000, 1.0))
            elif field == 'TotHUs_15':
                # Scale housing units assuming 200k is high
                units = float(property_data[field])
                values.append(min(units / 200000, 1.0))
            else:
                # Generic scaling for other values
                values.append(0.5)
    
    if not metrics:
        console.print(f"[yellow]No metrics available for radar chart[/yellow]")
        return None
    
    # Create radar chart
    fig = go.Figure()
    
    # Close the radar by repeating the first value
    metrics.append(metrics[0])
    values.append(values[0])
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=metrics,
        fill='toself',
        name='Property Metrics',
        line=dict(color='blue')
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title="Property Opportunity Profile",
        showlegend=False
    )
    
    return fig

def create_simple_quadrant_chart(df, property_data):
    """
    Create a simple quadrant chart showing property value vs opportunity.
    
    Parameters:
    - df: DataFrame containing all property data
    - property_data: The specific property to highlight
    """
    # Create a simple scatter plot
    fig = go.Figure()
    
    # Try to get price and score data
    try:
        # Process all properties
        all_x = []
        all_y = []
        all_text = []
        
        # Get price data
        if 'Price Per Acre' in df.columns:
            df_filtered = df[df['Price Per Acre'].notna()]
            all_x = df_filtered['Price Per Acre'].values
            price_field = 'Price Per Acre'
        elif 'For Sale Price' in df.columns:
            df_filtered = df[df['For Sale Price'].notna()]
            all_x = df_filtered['For Sale Price'].values
            price_field = 'For Sale Price'
        else:
            all_x = np.arange(len(df))
            price_field = 'Index'
        
        # Get score data
        if 'Composite Score' in df.columns:
            all_y = df_filtered['Composite Score'].values if 'df_filtered' in locals() else df['Composite Score'].values
            score_field = 'Composite Score'
        elif 'Weighted Demand and Convenience' in df.columns:
            all_y = df_filtered['Weighted Demand and Convenience'].values if 'df_filtered' in locals() else df['Weighted Demand and Convenience'].values
            score_field = 'Weighted Demand and Convenience'
        else:
            all_y = np.random.random(len(all_x)) * 0.5 + 0.25  # Random values between 0.25 and 0.75
            score_field = 'Value'
        
        # Add all properties
        fig.add_trace(go.Scatter(
            x=all_x,
            y=all_y,
            mode='markers',
            marker=dict(
                size=8,
                color='lightblue',
                opacity=0.6
            ),
            name='All Properties',
            text=df_filtered['StockNumber'].values if 'df_filtered' in locals() else df['StockNumber'].values,
            hovertemplate='%{text}<br>' + price_field + ': %{x}<br>' + score_field + ': %{y}'
        ))
        
        # Add the specific property
        stock_number = property_data['StockNumber']
        
        property_x = property_data[price_field] if price_field in property_data else 0
        property_y = property_data[score_field] if score_field in property_data else 0
        
        fig.add_trace(go.Scatter(
            x=[property_x],
            y=[property_y],
            mode='markers',
            marker=dict(
                size=15,
                color='red',
                symbol='star',
                line=dict(width=2, color='black')
            ),
            name=f'Property {stock_number}',
            hovertemplate=f'Property {stock_number}<br>' + price_field + ': %{x}<br>' + score_field + ': %{y}'
        ))
        
        # Add quadrant lines
        x_values = all_x
        if len(x_values) > 0:
            median_x = np.median(x_values)
            median_y = 0.5  # For Composite Score which is between 0-1
            
            fig.add_shape(
                type="line", line=dict(dash="dash", width=1, color="gray"),
                x0=median_x, y0=0, x1=median_x, y1=1
            )
            fig.add_shape(
                type="line", line=dict(dash="dash", width=1, color="gray"),
                x0=min(all_x), y0=median_y, x1=max(all_x), y1=median_y
            )
        
        # Label quadrants
        if len(x_values) > 0:
            fig.add_annotation(
                x=min(all_x) + (median_x - min(all_x))/2, 
                y=0.75,
                text="Low Price<br>High Opportunity",
                showarrow=False,
                font=dict(size=10, color="green")
            )
            fig.add_annotation(
                x=median_x + (max(all_x) - median_x)/2, 
                y=0.75,
                text="High Price<br>High Opportunity",
                showarrow=False,
                font=dict(size=10, color="blue")
            )
            fig.add_annotation(
                x=min(all_x) + (median_x - min(all_x))/2, 
                y=0.25,
                text="Low Price<br>Low Opportunity",
                showarrow=False,
                font=dict(size=10, color="gray")
            )
            fig.add_annotation(
                x=median_x + (max(all_x) - median_x)/2, 
                y=0.25,
                text="High Price<br>Low Opportunity",
                showarrow=False,
                font=dict(size=10, color="red")
            )
    except Exception as e:
        console.print(f"[red]Error creating quadrant chart: {str(e)}[/red]")
        # Create empty chart with error message
        fig.add_annotation(
            x=0.5, y=0.5,
            text=f"Error creating chart: {str(e)}",
            showarrow=False,
            font=dict(size=14, color="red")
        )
    
    fig.update_layout(
        title=f"Opportunity Quadrant Analysis",
        xaxis_title="Price",
        yaxis_title="Opportunity Score",
        showlegend=True
    )
    
    return fig

def create_simple_bar_chart(property_data):
    """
    Create a simple bar chart of key metrics.
    
    Parameters:
    - property_data: DataFrame row containing property data
    """
    # Define metrics to display if available
    potential_metrics = {
        'Population Density': 'TotPop_15',
        'Housing Units': 'TotHUs_15',
        'Median Income': 'MedianHHInc_15',
        'Property Size': 'Land Area (AC)',
        'Opportunity Score': 'Composite Score',
        'Housing Gap': 'Housing Gap',
        'Affordability': 'Home Affordability Gap',
        'Rental Demand': 'Demand for Attainable Rent'
    }
    
    # Collect available metrics
    metrics = []
    values = []
    
    for label, field in potential_metrics.items():
        if field in property_data and pd.notna(property_data[field]):
            metrics.append(label)
            values.append(float(property_data[field]))
    
    if not metrics:
        console.print(f"[yellow]No metrics available for bar chart[/yellow]")
        return None
    
    # Create bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=metrics,
        y=values,
        marker_color='royalblue'
    ))
    
    fig.update_layout(
        title="Key Property Metrics",
        xaxis_title="Metric",
        yaxis_title="Value",
        showlegend=False
    )
    
    return fig

def create_simple_heatmap(property_data):
    """
    Create a simple heatmap showing development potential.
    
    Parameters:
    - property_data: DataFrame row containing property data
    """
    # Define development types and evaluation factors
    development_types = ["Single Family", "Multi-Family", "Mixed Use", "Commercial", "Industrial"]
    factors = ["Population", "Income Level", "Housing Demand", "Affordability", "Location"]
    
    # Create sample data based on property attributes
    # This is synthetic but tied to real property data where available
    try:
        # Create matrix of scores
        scores = np.zeros((len(factors), len(development_types)))
        
        # Fill with synthetic but reasonable values
        for i, factor in enumerate(factors):
            for j, dev_type in enumerate(development_types):
                # Base score
                score = 0.5
                
                # Adjust based on available property data
                if factor == "Population" and 'TotPop_15' in property_data:
                    pop = float(property_data['TotPop_15'])
                    pop_score = min(pop / 500000, 1.0)  # Scale, max at 500k
                    
                    # Different development types value population differently
                    if dev_type == "Single Family":
                        score = pop_score * 0.7 + 0.3  # People like suburban
                    elif dev_type == "Multi-Family":
                        score = pop_score * 0.8 + 0.2  # Density is good
                    elif dev_type == "Mixed Use":
                        score = pop_score * 0.9 + 0.1  # Higher density is better
                    elif dev_type == "Commercial":
                        score = pop_score * 0.9 + 0.1  # Foot traffic is key
                    elif dev_type == "Industrial":
                        score = 0.4 if pop_score > 0.5 else 0.6  # Prefer less population
                
                elif factor == "Income Level" and 'MedianHHInc_15' in property_data:
                    income = float(property_data['MedianHHInc_15'])
                    income_score = min(income / 150000, 1.0)  # Scale, max at $150k
                    
                    if dev_type == "Single Family":
                        score = income_score * 0.8 + 0.2  # Higher income is better
                    elif dev_type == "Multi-Family":
                        score = 0.7 - (income_score * 0.4)  # Lower income needs more rentals
                    elif dev_type == "Mixed Use":
                        score = income_score * 0.6 + 0.4  # Somewhat income sensitive
                    elif dev_type == "Commercial":
                        score = income_score * 0.9 + 0.1  # Spending power matters
                    elif dev_type == "Industrial":
                        score = 0.5  # Not as income sensitive
                
                elif factor == "Housing Demand" and 'Housing Gap' in property_data:
                    gap = float(property_data['Housing Gap'])
                    gap_score = min(max(gap, 0), 1.0)  # Between 0-1
                    
                    if dev_type == "Single Family":
                        score = (1 - gap_score) * 0.8 + 0.2  # Lower gap (more houses) is worse
                    elif dev_type == "Multi-Family":
                        score = gap_score * 0.9 + 0.1  # Higher gap is better for multi-family
                    elif dev_type == "Mixed Use":
                        score = gap_score * 0.7 + 0.3  # Gap helps but not critical
                    else:
                        score = 0.5  # Not as relevant
                
                elif factor == "Affordability" and 'Home Affordability Gap' in property_data:
                    gap = float(property_data['Home Affordability Gap'])
                    gap_score = min(max(gap/50000, 0), 1.0)  # Scale to 0-1, max at $50k gap
                    
                    if dev_type == "Single Family":
                        score = (1 - gap_score) * 0.7 + 0.3  # Lower gap is better
                    elif dev_type == "Multi-Family":
                        score = gap_score * 0.8 + 0.2  # Higher gap means more rental demand
                    elif dev_type == "Mixed Use":
                        score = 0.6  # Somewhat relevant
                    else:
                        score = 0.5  # Not as relevant
                
                elif factor == "Location" and 'Nearest_Walmart_Distance_Miles' in property_data:
                    distance = float(property_data['Nearest_Walmart_Distance_Miles'])
                    dist_score = max(1 - (distance / 10), 0)  # Closer is better, up to 10 miles
                    
                    if dev_type == "Single Family":
                        score = dist_score * 0.6 + 0.4  # Proximity helps but not critical
                    elif dev_type == "Multi-Family":
                        score = dist_score * 0.7 + 0.3  # Closer is better
                    elif dev_type == "Mixed Use":
                        score = dist_score * 0.8 + 0.2  # Closer is much better
                    elif dev_type == "Commercial":
                        score = dist_score * 0.9 + 0.1  # Very proximity sensitive
                    elif dev_type == "Industrial":
                        score = 0.5  # Not as location sensitive
                
                scores[i, j] = max(0, min(score, 1))  # Ensure between 0-1
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=scores,
            x=development_types,
            y=factors,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Score")
        ))
        
        fig.update_layout(
            title="Development Potential Analysis",
            xaxis_title="Development Type",
            yaxis_title="Factor",
            height=500
        )
        
        return fig
    
    except Exception as e:
        console.print(f"[red]Error creating heatmap: {str(e)}[/red]")
        # Create empty figure with error message
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text=f"Error creating development potential chart: {str(e)}",
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            title="Development Potential Analysis",
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False),
            height=400
        )
        return fig

def create_property_visualizations(stock_number):
    """
    Create a set of property-specific visualizations.
    
    Parameters:
    - stock_number: Stock number of the property to visualize
    
    Returns:
    Dictionary of visualization figures
    """
    visualizations = {}
    
    # Load data
    df = load_master_data()
    if df is None:
        return visualizations
    
    # Find the property
    if 'StockNumber' not in df.columns:
        console.print(f"[red]StockNumber column not found in data[/red]")
        return visualizations
    
    property_data = df[df['StockNumber'].astype(str) == str(stock_number)]
    if property_data.empty:
        console.print(f"[red]Property with stock number {stock_number} not found[/red]")
        return visualizations
    
    property_row = property_data.iloc[0]
    
    # Create each visualization
    try:
        # 1. Radar chart
        radar_chart = create_simple_radar_chart(property_row)
        if radar_chart:
            visualizations['radar_chart'] = radar_chart
            console.print(f"[green]Created radar chart for property {stock_number}[/green]")
        
        # 2. Quadrant chart
        quadrant_chart = create_simple_quadrant_chart(df, property_row)
        if quadrant_chart:
            visualizations['quadrant_chart'] = quadrant_chart
            console.print(f"[green]Created quadrant chart for property {stock_number}[/green]")
        
        # 3. Bar chart of key metrics
        bar_chart = create_simple_bar_chart(property_row)
        if bar_chart:
            visualizations['growth_gap_chart'] = bar_chart
            console.print(f"[green]Created bar chart for property {stock_number}[/green]")
        
        # 4. Development potential heatmap
        heatmap = create_simple_heatmap(property_row)
        if heatmap:
            visualizations['advantage_chart'] = heatmap
            console.print(f"[green]Created development potential heatmap for property {stock_number}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error creating property visualizations: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
    
    return visualizations

if __name__ == "__main__":
    # Test the visualizations
    console.print("[bold blue]Testing simple visualizations...[/bold blue]")
    df = load_master_data()
    if df is not None and len(df) > 0:
        stock_number = df.iloc[0]['StockNumber']
        visualizations = create_property_visualizations(stock_number)
        console.print(f"[green]Created {len(visualizations)} visualizations[/green]")
    else:
        console.print("[red]Failed to load data or no properties found[/red]") 
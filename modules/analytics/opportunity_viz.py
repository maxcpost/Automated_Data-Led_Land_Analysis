"""
Opportunity Visualization module for generating advanced visualizations
to identify high-opportunity properties.
"""

import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.preprocessing import MinMaxScaler
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
        
        # Ensure Price Per Acre is calculated
        if 'For Sale Price' in df.columns and 'Land Area (AC)' in df.columns:
            df['Price Per Acre'] = df['For Sale Price'] / df['Land Area (AC)']
        
        return df
    except Exception as e:
        console.print(f"[red]Error loading data: {str(e)}[/red]")
        return None

def normalize_column(df, column, min_val=None, max_val=None):
    """Normalize a column to the range [0, 1]."""
    if column not in df.columns:
        return df
    
    # Handle missing values
    df[column] = pd.to_numeric(df[column], errors='coerce')
    
    # If min/max not provided, calculate from data
    if min_val is None:
        min_val = df[column].min()
    if max_val is None:
        max_val = df[column].max()
    
    # Prevent division by zero
    if min_val == max_val:
        df[f"Normalized_{column}"] = 0.5
    else:
        df[f"Normalized_{column}"] = (df[column] - min_val) / (max_val - min_val)
    
    return df

def create_opportunity_quadrant(df):
    """
    Create the Opportunity Quadrant visualization.
    
    X-axis: Price per Acre (normalized)
    Y-axis: Composite Score
    Size: Land Area
    Color: Population Growth
    """
    if df is None or len(df) == 0:
        return None
    
    # Prepare data
    viz_df = df.copy()
    
    # Calculate population growth if not already in the dataframe
    if 'Population Growth' not in viz_df.columns and 'TotPop_15' in viz_df.columns:
        # Using TotPop_15 as a proxy for population growth potential
        viz_df = normalize_column(viz_df, 'TotPop_15')
        viz_df['Population Growth'] = viz_df['Normalized_TotPop_15']
    
    # Normalize Price Per Acre
    viz_df = normalize_column(viz_df, 'Price Per Acre')
    
    # Normalize Composite Score if it exists
    if 'Composite Score' in viz_df.columns:
        viz_df = normalize_column(viz_df, 'Composite Score')
    else:
        # If no composite score, create a simple one based on available metrics
        available_metrics = [col for col in ['Home Affordability Gap', 'Demand for Attainable Rent', 
                                           'Housing Gap', 'Weighted Demand and Convenience'] 
                            if col in viz_df.columns]
        
        if available_metrics:
            # Normalize and combine available metrics
            for metric in available_metrics:
                viz_df = normalize_column(viz_df, metric)
            
            normalized_cols = [f"Normalized_{metric}" for metric in available_metrics]
            viz_df['Composite Score'] = viz_df[normalized_cols].mean(axis=1)
        else:
            # Fallback if no metrics available
            viz_df['Composite Score'] = 0.5
    
    # Create quadrant labels
    viz_df['Quadrant'] = 'Unknown'
    viz_df.loc[(viz_df['Normalized_Price Per Acre'] <= 0.5) & (viz_df['Composite Score'] > 0.5), 'Quadrant'] = 'Prime Opportunities'
    viz_df.loc[(viz_df['Normalized_Price Per Acre'] > 0.5) & (viz_df['Composite Score'] > 0.5), 'Quadrant'] = 'Premium Investments'
    viz_df.loc[(viz_df['Normalized_Price Per Acre'] <= 0.5) & (viz_df['Composite Score'] <= 0.5), 'Quadrant'] = 'Speculative Properties'
    viz_df.loc[(viz_df['Normalized_Price Per Acre'] > 0.5) & (viz_df['Composite Score'] <= 0.5), 'Quadrant'] = 'Avoid'
    
    # Create hover text
    viz_df['Hover Text'] = viz_df.apply(
        lambda row: f"Stock #: {row.get('StockNumber', 'N/A')}<br>" +
                   f"Address: {row.get('Property Address', 'N/A')}<br>" +
                   f"Price: ${row.get('For Sale Price', 0):,.2f}<br>" +
                   f"Acres: {row.get('Land Area (AC)', 0):,.2f}<br>" +
                   f"Price/Acre: ${row.get('Price Per Acre', 0):,.2f}<br>" +
                   f"Composite Score: {row.get('Composite Score', 0):.2f}",
        axis=1
    )
    
    # Create the plot
    fig = px.scatter(
        viz_df,
        x='Normalized_Price Per Acre',
        y='Composite Score',
        size='Land Area (AC)',
        color='Quadrant',
        hover_name='StockNumber',
        hover_data={
            'Normalized_Price Per Acre': False,
            'Hover Text': True,
            'Quadrant': True,
            'Land Area (AC)': True,
            'Composite Score': True
        },
        color_discrete_map={
            'Prime Opportunities': '#2ca02c',      # Green
            'Premium Investments': '#1f77b4',      # Blue
            'Speculative Properties': '#ff7f0e',   # Orange
            'Avoid': '#d62728'                     # Red
        },
        title='Property Opportunity Quadrant Analysis'
    )
    
    # Add quadrant lines
    fig.add_shape(
        type="line", line=dict(dash="dash", width=1, color="gray"),
        x0=0.5, y0=0, x1=0.5, y1=1
    )
    fig.add_shape(
        type="line", line=dict(dash="dash", width=1, color="gray"),
        x0=0, y0=0.5, x1=1, y1=0.5
    )
    
    # Add quadrant labels
    fig.add_annotation(x=0.25, y=0.75, text="Prime Opportunities", showarrow=False, font=dict(size=14, color="#2ca02c"))
    fig.add_annotation(x=0.75, y=0.75, text="Premium Investments", showarrow=False, font=dict(size=14, color="#1f77b4"))
    fig.add_annotation(x=0.25, y=0.25, text="Speculative Properties", showarrow=False, font=dict(size=14, color="#ff7f0e"))
    fig.add_annotation(x=0.75, y=0.25, text="Avoid", showarrow=False, font=dict(size=14, color="#d62728"))
    
    # Update layout
    fig.update_layout(
        xaxis_title="Price Per Acre (Normalized)",
        yaxis_title="Opportunity Score",
        legend_title="Opportunity Category",
        height=700,
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1])
    )
    
    return fig

def create_radar_chart(df, property_id):
    """
    Create a radar chart for a specific property showing its opportunity factors.
    
    Parameters:
    - df: DataFrame containing property data
    - property_id: StockNumber or index of the property to visualize
    """
    if df is None or len(df) == 0:
        return None
    
    # Filter for the specific property
    if isinstance(property_id, str):
        property_df = df[df['StockNumber'] == property_id]
    else:
        property_df = df.iloc[[property_id]]
    
    if len(property_df) == 0:
        return None
    
    # Define the metrics to include in the radar chart
    metrics = []
    avail_metrics = {}
    
    # Check which metrics are available and normalize them
    potential_metrics = {
        'Population Growth': 'TotPop_15',
        'Affordability Gap': 'Home Affordability Gap',
        'Rental Demand': 'Demand for Attainable Rent',
        'Housing Supply Gap': 'Housing Gap',
        'Location Value': 'MedianHValue_15',
        'Development Potential': 'Land Area (AC)'  # Using land area as proxy for development potential
    }
    
    for display_name, metric_name in potential_metrics.items():
        if metric_name in property_df.columns:
            df_temp = normalize_column(df, metric_name)
            norm_value = df_temp.loc[property_df.index, f'Normalized_{metric_name}'].values[0]
            metrics.append(display_name)
            avail_metrics[display_name] = norm_value
    
    # If we have metrics, create the radar chart
    if metrics:
        # Add the first metric again to close the polygon
        metrics.append(metrics[0])
        values = [avail_metrics[m] if m in avail_metrics else avail_metrics[m[:-1]] for m in metrics]
        
        # Create radar chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=property_df['StockNumber'].values[0]
        ))
        
        property_name = f"{property_df['StockNumber'].values[0]}"
        if 'Property Address' in property_df.columns:
            property_name += f" - {property_df['Property Address'].values[0]}"
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            title=f"Opportunity Profile: {property_name}",
            height=500
        )
        
        return fig
    
    return None

def create_growth_gap_chart(df):
    """
    Create a Growth vs. Gap visualization.
    
    X-axis: Population Growth 
    Y-axis: Housing Gap
    Size: Land Area
    Color: Median Household Income
    """
    if df is None or len(df) == 0:
        return None
    
    # Prepare data
    viz_df = df.copy()
    
    # Check if we have the required columns
    required_columns = ['TotPop_15', 'Housing Gap', 'MedianHHInc_15', 'Land Area (AC)']
    if not all(col in viz_df.columns for col in required_columns):
        # Try to calculate missing columns if possible
        if 'TotPop_15' in viz_df.columns and 'TotHUs_20' in viz_df.columns and 'TotPop_20' in viz_df.columns and 'Housing Gap' not in viz_df.columns:
            viz_df['Housing Gap'] = viz_df['TotHUs_20'] / viz_df['TotPop_20']
    
    # If after attempting calculations we still don't have what we need, return None
    if not all(col in viz_df.columns for col in ['TotPop_15', 'Housing Gap', 'Land Area (AC)']):
        return None
    
    # Normalize all relevant columns
    viz_df = normalize_column(viz_df, 'TotPop_15')
    viz_df = normalize_column(viz_df, 'Housing Gap')
    
    # Check if we have income data, otherwise use a default
    if 'MedianHHInc_15' in viz_df.columns:
        viz_df = normalize_column(viz_df, 'MedianHHInc_15')
        color_column = 'MedianHHInc_15'
        color_label = 'Median Household Income'
    else:
        viz_df['Default_Color'] = 0.5
        color_column = 'Default_Color'
        color_label = 'No Income Data'
    
    # Create hover text
    viz_df['Hover Text'] = viz_df.apply(
        lambda row: f"Stock #: {row.get('StockNumber', 'N/A')}<br>" +
                   f"Address: {row.get('Property Address', 'N/A')}<br>" +
                   f"Population (15mi): {row.get('TotPop_15', 0):,.0f}<br>" +
                   f"Housing Gap: {row.get('Housing Gap', 0):.4f}<br>" +
                   f"Median Income: ${row.get('MedianHHInc_15', 0):,.2f}<br>" +
                   f"Acres: {row.get('Land Area (AC)', 0):,.2f}",
        axis=1
    )
    
    # Create the plot
    fig = px.scatter(
        viz_df,
        x='Normalized_TotPop_15',
        y='Normalized_Housing Gap',
        size='Land Area (AC)',
        color=color_column,
        hover_name='StockNumber',
        hover_data={
            'Normalized_TotPop_15': False,
            'Normalized_Housing Gap': False,
            color_column: False,
            'Hover Text': True
        },
        title='Growth vs. Housing Gap Analysis'
    )
    
    # Add quadrant lines
    fig.add_shape(
        type="line", line=dict(dash="dash", width=1, color="gray"),
        x0=0.5, y0=0, x1=0.5, y1=1
    )
    fig.add_shape(
        type="line", line=dict(dash="dash", width=1, color="gray"),
        x0=0, y0=0.5, x1=1, y1=0.5
    )
    
    # Add quadrant labels
    fig.add_annotation(x=0.75, y=0.75, text="High Growth & Housing Gap", showarrow=False, 
                       font=dict(size=14, color="green"))
    fig.add_annotation(x=0.25, y=0.75, text="Low Growth, High Gap", showarrow=False, 
                       font=dict(size=14, color="blue"))
    fig.add_annotation(x=0.75, y=0.25, text="High Growth, Low Gap", showarrow=False, 
                       font=dict(size=14, color="orange"))
    fig.add_annotation(x=0.25, y=0.25, text="Low Opportunity", showarrow=False, 
                       font=dict(size=14, color="red"))
    
    # Update layout
    fig.update_layout(
        xaxis_title="Population Growth Potential",
        yaxis_title="Housing Gap",
        coloraxis_colorbar_title=color_label,
        height=700,
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1])
    )
    
    return fig

def create_price_to_potential_map(df):
    """
    Create a geographic map showing properties colored by their opportunity-to-price ratio.
    """
    if df is None or len(df) == 0 or 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        return None
    
    # Prepare data
    viz_df = df.copy()
    
    # Create opportunity-to-price ratio if we have composite score and price data
    if 'Composite Score' in viz_df.columns and 'Price Per Acre' in viz_df.columns:
        # Avoid division by zero
        viz_df['Price Per Acre'] = viz_df['Price Per Acre'].replace(0, np.nan)
        viz_df['Opportunity Ratio'] = viz_df['Composite Score'] / viz_df['Price Per Acre']
        viz_df = normalize_column(viz_df, 'Opportunity Ratio')
        color_column = 'Normalized_Opportunity Ratio'
        color_label = 'Opportunity-to-Price Ratio'
    elif 'Composite Score' in viz_df.columns:
        color_column = 'Composite Score'
        color_label = 'Opportunity Score'
    else:
        # Fallback if we don't have composite score
        viz_df['Default_Color'] = 0.5
        color_column = 'Default_Color'
        color_label = 'No Score Data'
    
    # Create hover text
    viz_df['Hover Text'] = viz_df.apply(
        lambda row: f"Stock #: {row.get('StockNumber', 'N/A')}<br>" +
                   f"Address: {row.get('Property Address', 'N/A')}<br>" +
                   f"Price: ${row.get('For Sale Price', 0):,.2f}<br>" +
                   f"Acres: {row.get('Land Area (AC)', 0):,.2f}<br>" +
                   f"Price/Acre: ${row.get('Price Per Acre', 0):,.2f}<br>" +
                   f"Composite Score: {row.get('Composite Score', 0):.2f}",
        axis=1
    )
    
    # Create the plot
    fig = px.scatter_mapbox(
        viz_df,
        lat='Latitude',
        lon='Longitude',
        size='Land Area (AC)',
        color=color_column,
        hover_name='StockNumber',
        hover_data={
            color_column: False,
            'Hover Text': True
        },
        zoom=6,
        height=700,
        title='Property Opportunity Map'
    )
    
    # Update layout
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":50,"l":0,"b":0},
        coloraxis_colorbar_title=color_label
    )
    
    return fig

def create_competitive_advantage_matrix(df):
    """
    Create a heatmap showing properties' competitive advantages for different development types.
    """
    if df is None or len(df) == 0:
        return None
    
    # Define development types and their relevant metrics
    dev_types = {
        'Residential': ['MedianHHInc_15', 'TotPop_15', 'Housing Gap'],
        'Multi-Family': ['Demand for Attainable Rent', 'MedianGrossRent_15', 'RenterOcc_15'],
        'Commercial': ['TotPop_10', 'MedianHHInc_10', 'Weighted Demand and Convenience'],
        'Mixed-Use': ['Composite Score', 'TotPop_5', 'MedianHHInc_5']
    }
    
    # Filter properties that have StockNumber (or use index if not available)
    if 'StockNumber' in df.columns:
        properties = df['StockNumber'].values
    else:
        properties = [f"Property {i}" for i in range(len(df))]
    
    # Limit to top 15 properties by composite score for readability
    if 'Composite Score' in df.columns:
        top_indices = df['Composite Score'].nlargest(15).index
        viz_df = df.loc[top_indices]
        properties = viz_df['StockNumber'].values if 'StockNumber' in viz_df.columns else [f"Property {i}" for i in top_indices]
    else:
        viz_df = df.head(15)
        properties = viz_df['StockNumber'].values if 'StockNumber' in viz_df.columns else [f"Property {i}" for i in range(15)]
    
    # Calculate score for each property-development type combination
    scores = np.zeros((len(properties), len(dev_types)))
    
    for i, property_id in enumerate(properties):
        prop_row = viz_df.iloc[i]
        
        for j, (dev_type, metrics) in enumerate(dev_types.items()):
            # Calculate average normalized score for available metrics
            metric_scores = []
            
            for metric in metrics:
                if metric in viz_df.columns:
                    viz_df = normalize_column(viz_df, metric)
                    metric_scores.append(viz_df.iloc[i][f"Normalized_{metric}"])
            
            if metric_scores:
                scores[i, j] = np.mean(metric_scores)
            else:
                scores[i, j] = 0.5  # Default score if no metrics available
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=scores,
        x=list(dev_types.keys()),
        y=properties,
        colorscale='Viridis',
        zmin=0, 
        zmax=1
    ))
    
    fig.update_layout(
        title='Competitive Advantage Matrix by Development Type',
        xaxis_title='Development Type',
        yaxis_title='Property',
        height=700
    )
    
    return fig

def create_all_visualizations():
    """
    Create all visualizations and return them as a dictionary.
    """
    # Load data
    df = load_master_data()
    if df is None:
        console.print("[red]Failed to load master data[/red]")
        return {}
    
    console.print(f"[green]Successfully loaded data with {len(df)} rows[/green]")
    
    # Create visualizations
    visualizations = {}
    
    # Try to create each visualization independently
    visualization_functions = {
        'opportunity_quadrant': create_opportunity_quadrant,
        'growth_gap_chart': create_growth_gap_chart,
        'price_to_potential_map': create_price_to_potential_map,
        'competitive_advantage_matrix': create_competitive_advantage_matrix
    }
    
    for name, viz_function in visualization_functions.items():
        try:
            console.print(f"[blue]Creating {name} visualization...[/blue]")
            viz = viz_function(df)
            visualizations[name] = viz
            if viz:
                console.print(f"[green]Successfully created {name} visualization[/green]")
            else:
                console.print(f"[yellow]Warning: {name} visualization returned None[/yellow]")
        except Exception as e:
            console.print(f"[red]Error creating {name} visualization: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            visualizations[name] = None
    
    # Try to create a radar chart for the first property as an example
    try:
        if len(df) > 0:
            console.print("[blue]Creating example radar chart...[/blue]")
            visualizations['radar_chart'] = create_radar_chart(df, 0)
            if visualizations['radar_chart']:
                console.print("[green]Successfully created example radar chart[/green]")
            else:
                console.print("[yellow]Warning: example radar chart returned None[/yellow]")
    except Exception as e:
        console.print(f"[red]Error creating radar chart: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        visualizations['radar_chart'] = None
    
    console.print(f"[green]Created {sum(1 for v in visualizations.values() if v is not None)} visualizations[/green]")
    return visualizations

if __name__ == "__main__":
    # Test the visualizations
    console.print("[bold blue]Testing opportunity visualizations...[/bold blue]")
    visualizations = create_all_visualizations()
    for name, viz in visualizations.items():
        if viz:
            console.print(f"[green]Successfully created {name}[/green]")
        else:
            console.print(f"[yellow]Failed to create {name}[/yellow]") 
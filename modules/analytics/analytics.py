"""
Analytics module for generating reports and insights from property data.
"""

import os
import pandas as pd
import numpy as np
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Initialize rich console for output
console = Console()

def ensure_directory_exists(directory):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_analytics_report():
    """
    Generate analytics metrics and add them directly to the master.csv file.
    
    The metrics include:
    - Price Per Acre (For Sale Price / Land Area)
    - Home Affordability Gap (Median Home Value - (Median Household Income * 3))
    - Demand for Attainable Rent (TotPop_15 * (MedianGrossRent_15 / (MedianHHInc_15 / 12)))
    - Housing Gap (TotHUs_20 / TotPop_20)
    - Weighted Demand and Convenience ((0.4*TotPop_10 + 0.3*TotPop_15 + 0.2*TotPop_20 + 0.1*TotPop_25) / ln(1 + Nearest_Walmart_Travel_Time_Minutes))
    - Composite Score (Normalized and weighted combination of the above metrics)
    """
    console.print("[bold blue]Calculating Analytics Metrics...[/bold blue]")
    
    try:
        # Ensure the database directory exists
        ensure_directory_exists("database")
        
        # Read the master.csv file
        master_path = "database/master.csv"
        if not os.path.exists(master_path):
            console.print("[red]Error: Master CSV file not found at database/master.csv[/red]")
            return False
        
        df = pd.read_csv(master_path)
        original_row_count = len(df)
        
        # Calculate metrics
        with Progress(
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Calculating metrics...", total=6)
            
            # Step 1: Calculate Price Per Acre
            console.print("Calculating Price Per Acre...")
            # Ensure columns exist
            if 'For Sale Price' not in df.columns or 'Land Area (AC)' not in df.columns:
                console.print("[yellow]Warning: 'For Sale Price' or 'Land Area (AC)' columns not found. Skipping Price Per Acre calculation.[/yellow]")
            else:
                # Convert For Sale Price to numeric, handling any non-numeric values
                df['For Sale Price'] = pd.to_numeric(df['For Sale Price'], errors='coerce')
                df['Land Area (AC)'] = pd.to_numeric(df['Land Area (AC)'], errors='coerce')
                
                # Calculate Price Per Acre, avoiding division by zero
                df['Price Per Acre'] = df.apply(
                    lambda row: row['For Sale Price'] / row['Land Area (AC)'] 
                    if pd.notna(row['For Sale Price']) and pd.notna(row['Land Area (AC)']) and row['Land Area (AC)'] > 0 
                    else np.nan, 
                    axis=1
                )
                
                # Format for readability
                df['Price Per Acre'] = df['Price Per Acre'].round(2)
            
            progress.update(task, advance=1)
            
            # Step 2: Calculate Home Affordability Gap
            console.print("Calculating Home Affordability Gap...")
            
            # Check if required columns exist
            if '2024 Median Home Value(10m)' not in df.columns or '2024 Med HH Inc(10m)' not in df.columns:
                console.print("[yellow]Warning: Home value or income columns not found. Skipping Home Affordability Gap calculation.[/yellow]")
            else:
                # First, ensure we're working with clean numeric data
                # Handle different formats (with $ and commas or plain numbers)
                try:
                    # Try to clean strings first
                    if df['2024 Median Home Value(10m)'].dtype == 'object':
                        df['2024 Median Home Value(10m)'] = df['2024 Median Home Value(10m)'].astype(str).str.replace('$', '').str.replace(',', '')
                    if df['2024 Med HH Inc(10m)'].dtype == 'object':
                        df['2024 Med HH Inc(10m)'] = df['2024 Med HH Inc(10m)'].astype(str).str.replace('$', '').str.replace(',', '')
                
                    # Convert to numeric
                    df['2024 Median Home Value(10m)'] = pd.to_numeric(df['2024 Median Home Value(10m)'], errors='coerce')
                    df['2024 Med HH Inc(10m)'] = pd.to_numeric(df['2024 Med HH Inc(10m)'], errors='coerce')
                    
                    # Calculate Home Affordability Gap
                    df['Home Affordability Gap'] = df['2024 Median Home Value(10m)'] - (df['2024 Med HH Inc(10m)'] * 3)
                    
                    # Round to 2 decimal places for readability
                    df['Home Affordability Gap'] = df['Home Affordability Gap'].round(2)
                except Exception as e:
                    console.print(f"[yellow]Warning: Error in Home Affordability Gap calculation: {str(e)}[/yellow]")
            
            progress.update(task, advance=1)
            
            # Step 3: Calculate Demand for Attainable Rent
            console.print("Calculating Demand for Attainable Rent...")
            
            # Check if required columns exist
            if 'TotPop_15' not in df.columns or 'MedianGrossRent_15' not in df.columns or 'MedianHHInc_15' not in df.columns:
                console.print("[yellow]Warning: Population, rent, or income columns not found. Skipping Demand for Attainable Rent calculation.[/yellow]")
            else:
                # First, ensure we're working with clean numeric data
                df['TotPop_15'] = pd.to_numeric(df['TotPop_15'], errors='coerce')
                df['MedianGrossRent_15'] = pd.to_numeric(df['MedianGrossRent_15'], errors='coerce')
                df['MedianHHInc_15'] = pd.to_numeric(df['MedianHHInc_15'], errors='coerce')
                
                # Calculate Demand for Attainable Rent
                # Formula: TotPop_15 * (MedianGrossRent_15 / (MedianHHInc_15 / 12))
                df['Demand for Attainable Rent'] = df.apply(
                    lambda row: row['TotPop_15'] * (row['MedianGrossRent_15'] / (row['MedianHHInc_15'] / 12))
                    if pd.notna(row['TotPop_15']) and pd.notna(row['MedianGrossRent_15']) and 
                       pd.notna(row['MedianHHInc_15']) and row['MedianHHInc_15'] > 0
                    else np.nan,
                    axis=1
                )
                
                # Round to 2 decimal places for readability
                df['Demand for Attainable Rent'] = df['Demand for Attainable Rent'].round(2)
            
            progress.update(task, advance=1)
            
            # Step 4: Calculate Housing Gap
            console.print("Calculating Housing Gap...")
            
            # Check if required columns exist
            if 'TotHUs_20' not in df.columns or 'TotPop_20' not in df.columns:
                console.print("[yellow]Warning: Housing units or population columns not found. Skipping Housing Gap calculation.[/yellow]")
            else:
                # First, ensure we're working with clean numeric data
                df['TotHUs_20'] = pd.to_numeric(df['TotHUs_20'], errors='coerce')
                df['TotPop_20'] = pd.to_numeric(df['TotPop_20'], errors='coerce')
                
                # Calculate Housing Gap
                # Formula: TotHUs_20 / TotPop_20
                df['Housing Gap'] = df.apply(
                    lambda row: row['TotHUs_20'] / row['TotPop_20']
                    if pd.notna(row['TotHUs_20']) and pd.notna(row['TotPop_20']) and row['TotPop_20'] > 0
                    else np.nan,
                    axis=1
                )
                
                # Round to 4 decimal places for readability (this will likely be a small number)
                df['Housing Gap'] = df['Housing Gap'].round(4)
            
            progress.update(task, advance=1)
            
            # Step 5: Calculate Weighted Demand and Convenience
            console.print("Calculating Weighted Demand and Convenience...")
            
            # Check if required columns exist
            required_cols = ['TotPop_10', 'TotPop_15', 'TotPop_20', 'TotPop_25', 'Nearest_Walmart_Travel_Time_Minutes']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                console.print(f"[yellow]Warning: Missing columns for Weighted Demand calculation: {', '.join(missing_cols)}. Skipping calculation.[/yellow]")
            else:
                # Ensure all columns are numeric
                for col in required_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Calculate Weighted Demand and Convenience
                # Formula: ((0.4*TotPop_10 + 0.3*TotPop_15 + 0.2*TotPop_20 + 0.1*TotPop_25) / ln(1 + Nearest_Walmart_Travel_Time_Minutes))
                df['Weighted Demand and Convenience'] = df.apply(
                    lambda row: (
                        (0.4 * row['TotPop_10'] + 
                         0.3 * row['TotPop_15'] + 
                         0.2 * row['TotPop_20'] + 
                         0.1 * row['TotPop_25']) / 
                        np.log(1 + row['Nearest_Walmart_Travel_Time_Minutes'])
                    )
                    if (pd.notna(row['TotPop_10']) and 
                        pd.notna(row['TotPop_15']) and 
                        pd.notna(row['TotPop_20']) and 
                        pd.notna(row['TotPop_25']) and 
                        pd.notna(row['Nearest_Walmart_Travel_Time_Minutes']) and 
                        row['Nearest_Walmart_Travel_Time_Minutes'] >= 0)
                    else np.nan,
                    axis=1
                )
                
                # Round to 2 decimal places for readability
                df['Weighted Demand and Convenience'] = df['Weighted Demand and Convenience'].round(2)
            
            progress.update(task, advance=1)
            
            # Step 6: Calculate Composite Score
            console.print("Calculating Composite Score...")
            
            # Check if all required columns exist
            required_metrics = [
                'Demand for Attainable Rent', 
                'Housing Gap', 
                'Home Affordability Gap', 
                'Weighted Demand and Convenience'
            ]
            
            missing_metrics = [metric for metric in required_metrics if metric not in df.columns]
            
            if missing_metrics:
                console.print(f"[yellow]Warning: Missing metrics for Composite Score: {', '.join(missing_metrics)}. Skipping calculation.[/yellow]")
            else:
                # Function to normalize a column to 0-1 scale
                def normalize_column(column):
                    min_val = column.min()
                    max_val = column.max()
                    if max_val == min_val:
                        return pd.Series(0.5, index=column.index)  # If all values are the same, return 0.5
                    return (column - min_val) / (max_val - min_val)
                
                # For Home Affordability Gap, we need to consider that negative values are better
                # (negative gap means homes are more affordable)
                if 'Home Affordability Gap' in df.columns:
                    # Invert the values so that lower (more negative) values become higher scores
                    df['Normalized Home Affordability Gap'] = 1 - normalize_column(df['Home Affordability Gap'])
                else:
                    df['Normalized Home Affordability Gap'] = np.nan
                
                # Normalize the other metrics
                df['Normalized Demand for Attainable Rent'] = normalize_column(df['Demand for Attainable Rent'])
                df['Normalized Housing Gap'] = normalize_column(df['Housing Gap'])
                df['Normalized Weighted Demand and Convenience'] = normalize_column(df['Weighted Demand and Convenience'])
                
                # Calculate composite score with equal weights (0.25 each)
                df['Composite Score'] = (
                    0.25 * df['Normalized Demand for Attainable Rent'] + 
                    0.25 * df['Normalized Housing Gap'] + 
                    0.25 * df['Normalized Home Affordability Gap'] + 
                    0.25 * df['Normalized Weighted Demand and Convenience']
                )
                
                # Round to 2 decimal places
                df['Composite Score'] = df['Composite Score'].round(2)
                
                # Remove the temporary normalization columns
                df = df.drop(columns=[
                    'Normalized Demand for Attainable Rent',
                    'Normalized Housing Gap',
                    'Normalized Home Affordability Gap',
                    'Normalized Weighted Demand and Convenience'
                ])
            
            progress.update(task, advance=1)
        
        # Ensure StockNumber is the first column
        if 'StockNumber' in df.columns:
            cols = df.columns.tolist()
            if cols[0] != 'StockNumber':
                cols.remove('StockNumber')
                cols = ['StockNumber'] + cols
                df = df[cols]
        
        # Save the updated DataFrame back to master.csv
        df.to_csv(master_path, index=False)
        
        console.print(f"[green]Analytics metrics successfully added to master.csv[/green]")
        
        # Print some summary statistics
        console.print("\n[bold]Analytics Summary:[/bold]")
        console.print(f"Total properties analyzed: {original_row_count}")
        
        # Calculate average Price Per Acre (excluding NaN values)
        if 'Price Per Acre' in df.columns:
            avg_price_per_acre = df['Price Per Acre'].mean()
            if not pd.isna(avg_price_per_acre):
                console.print(f"Average Price Per Acre: ${avg_price_per_acre:,.2f}")
            else:
                console.print("Average Price Per Acre: Not available (missing data)")
        
        # Calculate average Home Affordability Gap (excluding NaN values)
        if 'Home Affordability Gap' in df.columns:
            avg_affordability_gap = df['Home Affordability Gap'].mean()
            if not pd.isna(avg_affordability_gap):
                console.print(f"Average Home Affordability Gap: ${avg_affordability_gap:,.2f}")
            else:
                console.print("Average Home Affordability Gap: Not available (missing data)")
            
            # Count properties with positive and negative gaps
            positive_gap_count = (df['Home Affordability Gap'] > 0).sum()
            negative_gap_count = (df['Home Affordability Gap'] < 0).sum()
            
            if positive_gap_count > 0 or negative_gap_count > 0:
                console.print(f"Properties where homes are less affordable (positive gap): {positive_gap_count}")
                console.print(f"Properties where homes are more affordable (negative gap): {negative_gap_count}")
        
        # Calculate average Demand for Attainable Rent (excluding NaN values)
        if 'Demand for Attainable Rent' in df.columns:
            avg_demand = df['Demand for Attainable Rent'].mean()
            if not pd.isna(avg_demand):
                console.print(f"Average Demand for Attainable Rent: {avg_demand:,.2f}")
            else:
                console.print("Average Demand for Attainable Rent: Not available (missing data)")
            
            # Get the min and max values for context
            min_demand = df['Demand for Attainable Rent'].min()
            max_demand = df['Demand for Attainable Rent'].max()
            if not pd.isna(min_demand) and not pd.isna(max_demand):
                console.print(f"Demand for Attainable Rent Range: {min_demand:,.2f} to {max_demand:,.2f}")
        
        # Calculate statistics for Housing Gap
        if 'Housing Gap' in df.columns:
            avg_gap = df['Housing Gap'].mean()
            if not pd.isna(avg_gap):
                console.print(f"Average Housing Gap: {avg_gap:,.4f} housing units per person")
            else:
                console.print("Average Housing Gap: Not available (missing data)")
            
            # Get the min and max values for context
            min_gap = df['Housing Gap'].min()
            max_gap = df['Housing Gap'].max()
            if not pd.isna(min_gap) and not pd.isna(max_gap):
                console.print(f"Housing Gap Range: {min_gap:,.4f} to {max_gap:,.4f}")
        
        # Calculate statistics for Weighted Demand and Convenience
        if 'Weighted Demand and Convenience' in df.columns:
            avg_wdc = df['Weighted Demand and Convenience'].mean()
            if not pd.isna(avg_wdc):
                console.print(f"Average Weighted Demand and Convenience: {avg_wdc:,.2f}")
            else:
                console.print("Average Weighted Demand and Convenience: Not available (missing data)")
            
            # Get the min and max values for context
            min_wdc = df['Weighted Demand and Convenience'].min()
            max_wdc = df['Weighted Demand and Convenience'].max()
            if not pd.isna(min_wdc) and not pd.isna(max_wdc):
                console.print(f"Weighted Demand and Convenience Range: {min_wdc:,.2f} to {max_wdc:,.2f}")
        
        # Calculate statistics for Composite Score
        if 'Composite Score' in df.columns:
            avg_score = df['Composite Score'].mean()
            if not pd.isna(avg_score):
                console.print(f"Average Composite Score: {avg_score:.2f} (scale: 0-1)")
            else:
                console.print("Average Composite Score: Not available (missing data)")
            
            # Get the min and max values for context
            min_score = df['Composite Score'].min()
            max_score = df['Composite Score'].max()
            if not pd.isna(min_score) and not pd.isna(max_score):
                console.print(f"Composite Score Range: {min_score:.2f} to {max_score:.2f}")
            
            # Count top-performing properties
            top_quartile = df['Composite Score'].quantile(0.75)
            top_count = (df['Composite Score'] >= top_quartile).sum()
            console.print(f"Properties in top 25% (score >= {top_quartile:.2f}): {top_count}")
        
        return True
    
    except Exception as e:
        console.print(f"[red]Error calculating analytics metrics: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return False 
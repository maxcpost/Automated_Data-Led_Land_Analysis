// Opportunity Dashboard JavaScript

document.addEventListener('DOMContentLoaded', () => {
    console.log('Opportunity dashboard JS loaded');
    
    // Show loading indicators
    document.querySelectorAll('.visualization-container').forEach(container => {
        container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading visualization...</p></div>';
    });
    
    // Load visualizations
    loadVisualizations();
    
    // Initialize property selector
    initPropertySelector();
});

/**
 * Load all visualizations from the API
 */
function loadVisualizations() {
    console.log('Loading visualizations...');
    
    fetch('/api/opportunity/visualizations')
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load visualizations');
                });
            }
            return response.json();
        })
        .then(visualizations => {
            console.log('Visualizations loaded:', Object.keys(visualizations));
            
            // Display each visualization
            if (visualizations.opportunity_quadrant) {
                displayPlotly('opportunity-quadrant', visualizations.opportunity_quadrant);
            }
            
            if (visualizations.growth_gap_chart) {
                displayPlotly('growth-gap-chart', visualizations.growth_gap_chart);
            }
            
            if (visualizations.price_to_potential_map) {
                displayPlotly('price-potential-map', visualizations.price_to_potential_map);
            }
            
            if (visualizations.competitive_advantage_matrix) {
                displayPlotly('competitive-advantage', visualizations.competitive_advantage_matrix);
            }
            
            // Example radar chart
            if (visualizations.radar_chart) {
                displayPlotly('property-radar', visualizations.radar_chart);
            }
        })
        .catch(error => {
            console.error('Error loading visualizations:', error);
            document.querySelectorAll('.visualization-container').forEach(container => {
                container.innerHTML = `<div class="error-message">
                    <h3>Error Loading Visualization</h3>
                    <p>${error.message}</p>
                    <button onclick="loadVisualizations()">Try Again</button>
                </div>`;
            });
        });
}

/**
 * Display a Plotly visualization in the specified container
 */
function displayPlotly(containerId, figureJson) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container #${containerId} not found`);
        return;
    }
    
    // Clear loading indicator
    container.innerHTML = '';
    
    try {
        Plotly.newPlot(container, figureJson.data, figureJson.layout, {responsive: true});
        console.log(`Plotly chart displayed in #${containerId}`);
    } catch (error) {
        console.error(`Error displaying chart in #${containerId}:`, error);
        container.innerHTML = `<div class="error-message">
            <h3>Visualization Error</h3>
            <p>${error.message}</p>
        </div>`;
    }
}

/**
 * Initialize property selector dropdown
 */
function initPropertySelector() {
    const selector = document.getElementById('property-selector');
    if (!selector) {
        console.error('Property selector not found');
        return;
    }
    
    fetch('/api/opportunity/properties')
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load properties');
                });
            }
            return response.json();
        })
        .then(properties => {
            // Clear loading option
            selector.innerHTML = '<option value="" disabled selected>Select a property</option>';
            
            // Add options for each property
            properties.forEach(property => {
                const option = document.createElement('option');
                option.value = property.id;
                option.textContent = property.name;
                selector.appendChild(option);
            });
            
            // Enable the selector
            selector.disabled = false;
            
            // Add change event listener
            selector.addEventListener('change', function() {
                const propertyId = this.value;
                if (propertyId) {
                    loadPropertyRadarChart(propertyId);
                }
            });
            
            console.log('Property selector initialized with', properties.length, 'properties');
        })
        .catch(error => {
            console.error('Error loading properties:', error);
            selector.innerHTML = '<option value="" disabled selected>Error loading properties</option>';
        });
}

/**
 * Load radar chart for a specific property
 */
function loadPropertyRadarChart(propertyId) {
    console.log('Loading radar chart for property', propertyId);
    
    const container = document.getElementById('property-radar');
    if (!container) {
        console.error('Radar chart container not found');
        return;
    }
    
    // Show loading indicator
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading property analysis...</p></div>';
    
    fetch(`/api/opportunity/radar-chart/${propertyId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load radar chart');
                });
            }
            return response.json();
        })
        .then(chartData => {
            displayPlotly('property-radar', chartData);
        })
        .catch(error => {
            console.error('Error loading radar chart:', error);
            container.innerHTML = `<div class="error-message">
                <h3>Error Loading Property Analysis</h3>
                <p>${error.message}</p>
                <button onclick="loadPropertyRadarChart('${propertyId}')">Try Again</button>
            </div>`;
        });
} 
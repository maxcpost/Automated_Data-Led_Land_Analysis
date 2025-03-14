// Property detail page JavaScript

// Global variables
let propertyMap = null;
let fullPropertyMap = null;
let propertyMarker = null;
let propertyData = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // STOCK_NUMBER is set in the HTML template
    loadPropertyData(STOCK_NUMBER);
    
    // Set up header stock number
    document.getElementById('header-stock-number').textContent = STOCK_NUMBER;
    
    // Set up action buttons
    document.getElementById('print-report')?.addEventListener('click', printReport);
    document.getElementById('export-data')?.addEventListener('click', exportData);
    document.getElementById('generate-ai-report')?.addEventListener('click', showAIReport);
    document.getElementById('copy-ai-report')?.addEventListener('click', copyAIReport);
    
    // Set up map controls (they will be connected once the map loads)
    document.getElementById('map-satellite')?.addEventListener('click', () => setMapType('satellite'));
    document.getElementById('map-terrain')?.addEventListener('click', () => setMapType('terrain'));
    document.getElementById('map-zoom-in')?.addEventListener('click', () => zoomMap(1));
    document.getElementById('map-zoom-out')?.addEventListener('click', () => zoomMap(-1));
    
    // Set up opportunity tab event listener
    document.getElementById('opportunity-tab')?.addEventListener('shown.bs.tab', loadOpportunityVisualizations);
    
    // Make sure the map refreshes when the tab is shown - this is critical for Google Maps to render correctly
    document.getElementById('fullmap-tab')?.addEventListener('shown.bs.tab', function() {
        if (fullPropertyMap && propertyData && propertyData.map) {
            setTimeout(function() {
                google.maps.event.trigger(fullPropertyMap, 'resize');
                fullPropertyMap.setCenter({
                    lat: parseFloat(propertyData.map.latitude),
                    lng: parseFloat(propertyData.map.longitude)
                });
            }, 50);
        }
    });
});

// Load property data from API
function loadPropertyData(stockNumber) {
    fetch(`/api/property/${stockNumber}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Property not found');
            }
            return response.json();
        })
        .then(data => {
            propertyData = data;
            renderPropertyDetails(data);
            showPropertyDetail();
        })
        .catch(error => {
            console.error('Error loading property data:', error);
            showPropertyNotFound();
        });
}

// Show property detail and hide loading
function showPropertyDetail() {
    document.getElementById('loading').classList.add('d-none');
    document.getElementById('property-detail').classList.remove('d-none');
    document.getElementById('property-not-found').classList.add('d-none');
    
    // Update document title with property number
    document.title = `Property ${propertyData.summary.stockNumber} - ADLA`;
}

// Show property not found message
function showPropertyNotFound() {
    document.getElementById('loading').classList.add('d-none');
    document.getElementById('property-detail').classList.add('d-none');
    document.getElementById('property-not-found').classList.remove('d-none');
    document.getElementById('missing-stock-number').textContent = STOCK_NUMBER;
}

// Render property details in the UI
function renderPropertyDetails(data) {
    // Set summary information
    document.getElementById('property-stock-number').textContent = data.summary.stockNumber;
    document.getElementById('location-text').textContent = data.summary.location;
    document.getElementById('property-price').textContent = data.summary.price;
    document.getElementById('property-acres').textContent = data.summary.acres;
    document.getElementById('property-score').textContent = data.summary.score;
    
    // Set contact information - look in both summary and categories
    let companyName = 'N/A';
    let companyPhone = 'N/A';
    
    // Try to get from summary first
    if (data.summary && data.summary.company) {
        companyName = data.summary.company;
    }
    
    if (data.summary && data.summary.phone) {
        companyPhone = data.summary.phone;
    }
    
    // If not in summary, try to get from categories
    if (companyName === 'N/A' && data.categories && data.categories['Contact Information']) {
        const companyInfo = data.categories['Contact Information'].find(item => item.field === 'Sale Company Name');
        if (companyInfo) {
            companyName = companyInfo.value;
        }
    }
    
    if (companyPhone === 'N/A' && data.categories && data.categories['Contact Information']) {
        const phoneInfo = data.categories['Contact Information'].find(item => item.field === 'Sale Company Phone');
        if (phoneInfo) {
            companyPhone = phoneInfo.value;
        }
    }
    
    document.getElementById('company-name').textContent = companyName;
    document.getElementById('company-phone').textContent = companyPhone;
    
    // Populate the property overview section
    try {
        // Basic metrics
        document.getElementById('overview-acres').textContent = data.summary.acres;
        document.getElementById('overview-price').textContent = data.summary.price;
        document.getElementById('overview-location').textContent = data.summary.location;
        document.getElementById('overview-score').textContent = data.summary.score;
        
        // Calculate opportunity factor percentages
        let locationValue = 0;
        let developmentPotential = 0;
        let housingDemand = 0;
        let populationGrowth = 0;
        
        // Try to derive values from categories
        if (data.categories) {
            // Location value - based on median house value or price per acre
            if (data.categories['Location Details']) {
                const nearWalmart = data.categories['Location Details'].find(item => 
                    item.field === 'Nearest_Walmart_Distance_Miles');
                if (nearWalmart) {
                    // Convert distance to value (closer is better)
                    const distance = parseFloat(nearWalmart.value) || 10;
                    locationValue = Math.max(0, Math.min(100, 100 - (distance * 10)));
                }
            }
            
            // Development potential - based on land size
            if (data.categories['Property Information']) {
                const landSize = data.categories['Property Information'].find(item => 
                    item.field === 'Land Area (AC)');
                if (landSize) {
                    // Scale acres to percentage (assuming 100 acres is 100%)
                    const acres = parseFloat(landSize.value) || 0;
                    developmentPotential = Math.min(100, acres);
                }
            }
            
            // Housing demand from analytics metrics
            if (data.categories['Analytics Metrics']) {
                const demand = data.categories['Analytics Metrics'].find(item => 
                    item.field === 'Demand for Attainable Rent');
                if (demand) {
                    // Normalize demand to 0-100 scale (assuming max demand is 100k)
                    const demandValue = parseFloat(demand.value.replace(/,/g, '')) || 0;
                    housingDemand = Math.min(100, (demandValue / 1000));
                }
                
                const score = data.categories['Analytics Metrics'].find(item => 
                    item.field === 'Composite Score');
                if (score) {
                    // Scale score (0-1) to percentage
                    const scoreValue = parseFloat(score.value) || 0;
                    populationGrowth = Math.round(scoreValue * 100);
                }
            }
            
            // Population growth from demographics
            if (data.categories['Demographics Data (15 min)']) {
                const population = data.categories['Demographics Data (15 min)'].find(item => 
                    item.field === 'TotPop_15');
                if (population) {
                    // Scale population (assume 200k is 100%)
                    const pop = parseFloat(population.value.replace(/,/g, '')) || 0;
                    populationGrowth = Math.min(100, (pop / 2000));
                }
            }
        }
        
        // Set percentage text and progress bars
        document.getElementById('location-value-percent').textContent = `${Math.round(locationValue)}%`;
        document.getElementById('location-value-progress').style.width = `${locationValue}%`;
        
        document.getElementById('development-potential-percent').textContent = `${Math.round(developmentPotential)}%`;
        document.getElementById('development-potential-progress').style.width = `${developmentPotential}%`;
        
        document.getElementById('housing-demand-percent').textContent = `${Math.round(housingDemand)}%`;
        document.getElementById('housing-demand-progress').style.width = `${housingDemand}%`;
        
        document.getElementById('population-growth-percent').textContent = `${Math.round(populationGrowth)}%`;
        document.getElementById('population-growth-progress').style.width = `${populationGrowth}%`;
    } catch (error) {
        console.error('Error populating property overview:', error);
    }
    
    // Render property information sections
    renderCategoryTable('property-info', data.categories['Property Information']);
    renderCategoryTable('location-info', data.categories['Location Details']);
    
    // Render demographics tables
    renderCategoryTable('demographics-5', data.categories['Demographics Data (5 min)']);
    renderCategoryTable('demographics-10', data.categories['Demographics Data (10 min)']);
    renderCategoryTable('demographics-15', data.categories['Demographics Data (15 min)']);
    renderCategoryTable('demographics-20', data.categories['Demographics Data (20 min)']);
    renderCategoryTable('demographics-25', data.categories['Demographics Data (25 min)']);
    
    // Render analytics information
    renderCategoryTable('analytics-info', data.categories['Analytics Metrics']);
    
    // Initialize map if coordinates are available
    if (data.map) {
        initializePropertyMap(data.map.latitude, data.map.longitude);
    } else {
        // Hide map if no coordinates
        document.getElementById('map-placeholder').style.display = 'block';
        document.getElementById('property-map').style.display = 'none';
        document.getElementById('full-property-map').innerHTML = '<div class="alert alert-warning">No coordinates available for this property</div>';
        
        // Disable map controls
        document.querySelectorAll('.map-controls button').forEach(btn => {
            btn.disabled = true;
        });
    }
}

// Render a category table
function renderCategoryTable(elementId, categoryData) {
    const tableBody = document.getElementById(elementId)?.querySelector('tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (!categoryData || categoryData.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="2" class="text-center text-muted">No data available</td>';
        tableBody.appendChild(row);
        return;
    }
    
    categoryData.forEach(item => {
        const row = document.createElement('tr');
        
        const nameCell = document.createElement('td');
        nameCell.className = 'fw-bold';
        nameCell.textContent = item.name;
        
        const valueCell = document.createElement('td');
        valueCell.textContent = item.value;
        
        // Highlight special values
        if (item.field === 'Composite Score') {
            valueCell.className = 'fw-bold text-primary';
        } else if (item.field.includes('Affordability') && item.value.includes('-')) {
            valueCell.className = 'text-success'; // Negative gap is good (more affordable)
        } else if (item.field.includes('Price') && item.value !== 'N/A') {
            valueCell.className = 'text-dark';
        }
        
        row.appendChild(nameCell);
        row.appendChild(valueCell);
        tableBody.appendChild(row);
    });
}

// Initialize Google Maps for property location
let mapsLoaded = false;
let mapLoadAttempts = 0;
const MAX_MAP_LOAD_ATTEMPTS = 5;

function initMap() {
    console.log("Google Maps API loaded");
    mapsLoaded = true;
    
    // Check if we already have data and need to initialize maps
    if (propertyData && propertyData.map) {
        initializePropertyMap(propertyData.map.latitude, propertyData.map.longitude);
    }
}

// Initialize the property map with coordinates
function initializePropertyMap(latitude, longitude) {
    if (!mapsLoaded) {
        // If Google Maps isn't loaded yet, wait a bit and retry
        if (mapLoadAttempts < MAX_MAP_LOAD_ATTEMPTS) {
            mapLoadAttempts++;
            console.log(`Waiting for Google Maps to load (attempt ${mapLoadAttempts})...`);
            setTimeout(() => initializePropertyMap(latitude, longitude), 1000);
        } else {
            console.error("Failed to load Google Maps after multiple attempts");
            document.getElementById('map-placeholder').style.display = 'flex';
            document.getElementById('property-map').style.display = 'none';
            document.getElementById('map-placeholder').querySelector('p').textContent = 'Map could not be loaded. Please refresh the page.';
        }
        return;
    }
    
    console.log("Initializing map with coordinates:", latitude, longitude);
    
    try {
        // Ensure coordinates are valid numbers
        latitude = parseFloat(latitude);
        longitude = parseFloat(longitude);
        
        if (isNaN(latitude) || isNaN(longitude)) {
            throw new Error("Invalid coordinates");
        }
        
        const propertyLocation = { lat: latitude, lng: longitude };
        
        // Hide placeholder and show map
        document.getElementById('map-placeholder').style.display = 'none';
        document.getElementById('property-map').style.display = 'block';
        
        // Small map in the header
        propertyMap = new google.maps.Map(document.getElementById('property-map'), {
            center: propertyLocation,
            zoom: 14,
            mapTypeId: google.maps.MapTypeId.HYBRID,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
            zoomControl: false
        });
        
        // Full interactive map
        fullPropertyMap = new google.maps.Map(document.getElementById('full-property-map'), {
            center: propertyLocation,
            zoom: 16,
            mapTypeId: google.maps.MapTypeId.HYBRID,
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true
        });
        
        // Create marker for both maps
        propertyMarker = new google.maps.Marker({
            position: propertyLocation,
            map: propertyMap,
            title: `Property ${propertyData.summary.stockNumber}`,
            animation: google.maps.Animation.DROP
        });
        
        // Add marker to the full map
        const fullMapMarker = new google.maps.Marker({
            position: propertyLocation,
            map: fullPropertyMap,
            title: `Property ${propertyData.summary.stockNumber}`,
            animation: google.maps.Animation.DROP
        });
        
        // Store marker for later reference
        fullPropertyMap.markers = [fullMapMarker];
        
        // Add info window to the full map marker
        const infoContent = `
            <div style="padding: 10px; max-width: 250px;">
                <h5 style="margin-top: 0; color: var(--primary-color); font-weight: bold;">${propertyData.summary.stockNumber}</h5>
                <p style="margin-bottom: 8px;"><strong>Location:</strong> ${propertyData.summary.location}</p>
                <p style="margin-bottom: 8px;"><strong>Price:</strong> ${propertyData.summary.price}</p>
                <p style="margin-bottom: 8px;"><strong>Area:</strong> ${propertyData.summary.acres} acres</p>
                <div style="margin-top: 8px; padding: 5px; background-color: var(--primary-color); color: white; border-radius: 4px; text-align: center;">
                    <strong>Score:</strong> ${propertyData.summary.score}
                </div>
            </div>
        `;
        
        const infoWindow = new google.maps.InfoWindow({
            content: infoContent,
            maxWidth: 300
        });
        
        // Add click listener to marker to show info window
        fullMapMarker.addListener('click', function() {
            infoWindow.open(fullPropertyMap, fullMapMarker);
        });
        
        // Show info window by default
        infoWindow.open(fullPropertyMap, fullMapMarker);
        
        // Make sure map is properly sized
        google.maps.event.trigger(propertyMap, 'resize');
        google.maps.event.trigger(fullPropertyMap, 'resize');
        
        console.log("Maps initialized successfully");
    } catch (error) {
        console.error("Error initializing maps:", error);
        document.getElementById('map-placeholder').style.display = 'flex';
        document.getElementById('property-map').style.display = 'none';
        document.getElementById('map-placeholder').querySelector('p').textContent = 'Error loading map: ' + error.message;
    }
}

// Set map type (satellite or terrain)
function setMapType(type) {
    if (!fullPropertyMap) return;
    
    if (type === 'satellite') {
        fullPropertyMap.setMapTypeId(google.maps.MapTypeId.HYBRID);
    } else if (type === 'terrain') {
        fullPropertyMap.setMapTypeId(google.maps.MapTypeId.TERRAIN);
    }
}

// Zoom map in or out
function zoomMap(amount) {
    if (!fullPropertyMap) return;
    
    const currentZoom = fullPropertyMap.getZoom();
    fullPropertyMap.setZoom(currentZoom + amount);
}

// Print property report
function printReport() {
    window.print();
}

// Export property data as JSON
function exportData() {
    if (!propertyData) return;
    
    // Create a formatted version for export
    const exportData = {
        stockNumber: propertyData.summary.stockNumber,
        location: propertyData.summary.location,
        coordinates: propertyData.map,
        details: {}
    };
    
    // Add all category data
    Object.entries(propertyData.categories).forEach(([category, fields]) => {
        exportData.details[category] = {};
        
        fields.forEach(field => {
            exportData.details[category][field.name] = field.value;
        });
    });
    
    // Create download link
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `property_${propertyData.summary.stockNumber}.json`);
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Load opportunity visualizations
function loadOpportunityVisualizations() {
    // Check if visualizations are already loaded
    if (window.opportunityVisualizationsLoaded) {
        return;
    }
    
    console.log('Loading opportunity visualizations for property', STOCK_NUMBER);
    
    // Show loading indicators
    document.querySelectorAll('.visualization-container').forEach(container => {
        if (!container.querySelector('.loading-spinner')) {
            container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading visualization...</p></div>';
        }
    });
    
    fetch(`/api/property/${STOCK_NUMBER}/opportunity`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load opportunity visualizations');
                });
            }
            return response.json();
        })
        .then(visualizations => {
            console.log('Opportunity visualizations loaded:', Object.keys(visualizations));
            
            // Display each visualization
            if (visualizations.radar_chart) {
                try {
                    displayPlotly('property-radar-chart', visualizations.radar_chart);
                } catch (error) {
                    console.error('Error displaying radar chart:', error);
                    showVisualizationError('property-radar-chart', 'Error displaying radar chart: ' + error.message);
                }
            } else {
                showVisualizationError('property-radar-chart', 'Radar chart data not available');
            }
            
            if (visualizations.quadrant_chart) {
                try {
                    displayPlotly('property-quadrant-chart', visualizations.quadrant_chart);
                } catch (error) {
                    console.error('Error displaying opportunity quadrant:', error);
                    showVisualizationError('property-quadrant-chart', 'Error displaying opportunity quadrant: ' + error.message);
                }
            } else {
                showVisualizationError('property-quadrant-chart', 'Opportunity quadrant data not available');
            }
            
            if (visualizations.growth_gap_chart) {
                try {
                    displayPlotly('property-growth-gap-chart', visualizations.growth_gap_chart);
                } catch (error) {
                    console.error('Error displaying growth gap chart:', error);
                    showVisualizationError('property-growth-gap-chart', 'Error displaying growth gap chart: ' + error.message);
                }
            } else {
                showVisualizationError('property-growth-gap-chart', 'Growth vs. housing gap data not available');
            }
            
            if (visualizations.advantage_chart) {
                try {
                    displayPlotly('property-advantage-chart', visualizations.advantage_chart);
                } catch (error) {
                    console.error('Error displaying advantage chart:', error);
                    showVisualizationError('property-advantage-chart', 'Error displaying competitive advantage chart: ' + error.message);
                }
            } else {
                showVisualizationError('property-advantage-chart', 'Competitive advantage data not available');
            }
            
            // Mark visualizations as loaded
            window.opportunityVisualizationsLoaded = true;
        })
        .catch(error => {
            console.error('Error loading opportunity visualizations:', error);
            document.querySelectorAll('.visualization-container').forEach(container => {
                showVisualizationError(container.id, error.message);
            });
        });
}

// Display a Plotly visualization in the specified container
function displayPlotly(containerId, figureJson) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container #${containerId} not found`);
        return;
    }
    
    // Clear loading indicator
    container.innerHTML = '';
    
    try {
        if (!figureJson || !figureJson.data || !figureJson.layout) {
            throw new Error('Invalid visualization data format');
        }
        
        console.log(`Plotting ${containerId} with ${figureJson.data.length} data traces`);
        Plotly.newPlot(container, figureJson.data, figureJson.layout, {responsive: true});
        console.log(`Plotly chart displayed in #${containerId}`);
    } catch (error) {
        console.error(`Error displaying chart in #${containerId}:`, error);
        showVisualizationError(containerId, error.message);
    }
}

// Show error message in visualization container
function showVisualizationError(containerId, errorMessage) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="error-message">
            <h3>Visualization Error</h3>
            <p>${errorMessage}</p>
            <button onclick="loadOpportunityVisualizations()">Try Again</button>
        </div>
    `;
}

// Show AI Report modal and fetch the report
function showAIReport() {
    // Get the modal element
    const modal = new bootstrap.Modal(document.getElementById('ai-report-modal'));
    
    // Reset the modal content
    document.getElementById('ai-report-loading').classList.remove('d-none');
    document.getElementById('ai-report-content').classList.add('d-none');
    document.getElementById('ai-report-error').classList.add('d-none');
    
    // Show the modal
    modal.show();
    
    // Fetch the AI report
    fetchAIReport(STOCK_NUMBER);
}

// Fetch AI report from API
function fetchAIReport(stockNumber) {
    fetch(`/api/property/${stockNumber}/ai-report`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate AI report');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            document.getElementById('ai-report-loading').classList.add('d-none');
            
            // Show report content
            const contentElement = document.getElementById('ai-report-content');
            contentElement.classList.remove('d-none');
            
            // Convert the report text to HTML with proper formatting
            contentElement.innerHTML = formatReportText(data.report);
        })
        .catch(error => {
            console.error('Error fetching AI report:', error);
            
            // Hide loading indicator
            document.getElementById('ai-report-loading').classList.add('d-none');
            
            // Show error message
            const errorElement = document.getElementById('ai-report-error');
            errorElement.classList.remove('d-none');
            
            document.getElementById('ai-report-error-message').textContent = 
                error.message || 'Failed to generate AI report. Please try again later.';
        });
}

// Format the report text with proper HTML formatting
function formatReportText(text) {
    if (!text) return '<p>No report content available.</p>';
    
    // Replace newlines with <br> tags
    let formatted = text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    
    // Wrap in paragraphs if not already
    if (!formatted.startsWith('<p>')) {
        formatted = '<p>' + formatted;
    }
    if (!formatted.endsWith('</p>')) {
        formatted = formatted + '</p>';
    }
    
    // Format headings (lines ending with a colon followed by newline)
    formatted = formatted.replace(/<p>([^<:]+):<\/p>/g, '<h4>$1</h4>');
    
    // Format lists (lines starting with - or * or numbers)
    formatted = formatted.replace(/<br>- /g, '</li><li>');
    formatted = formatted.replace(/<br>\* /g, '</li><li>');
    formatted = formatted.replace(/<br>[0-9]+\. /g, '</li><li>');
    formatted = formatted.replace(/<p>- /g, '<p><ul><li>');
    formatted = formatted.replace(/<p>\* /g, '<p><ul><li>');
    formatted = formatted.replace(/<p>[0-9]+\. /g, '<p><ol><li>');
    formatted = formatted.replace(/<\/li><\/p>/g, '</li></ul></p>');
    
    // Add special formatting for the overall score
    formatted = formatted.replace(/([Ss]core:?\s*([0-9]|10)(\s*\/\s*10)?)/g, '<span class="badge bg-info p-2 fs-5">$1</span>');
    
    return formatted;
}

// Copy AI report to clipboard
function copyAIReport() {
    const reportContent = document.getElementById('ai-report-content').innerText;
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(reportContent)
            .then(() => {
                // Show success feedback
                const copyButton = document.getElementById('copy-ai-report');
                const originalText = copyButton.innerHTML;
                
                copyButton.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
                copyButton.classList.remove('btn-primary');
                copyButton.classList.add('btn-success');
                
                // Reset after 2 seconds
                setTimeout(() => {
                    copyButton.innerHTML = originalText;
                    copyButton.classList.remove('btn-success');
                    copyButton.classList.add('btn-primary');
                }, 2000);
            })
            .catch(err => {
                console.error('Error copying text: ', err);
                alert('Failed to copy report to clipboard');
            });
    } else {
        // Fallback for browsers that don't support clipboard API
        const textarea = document.createElement('textarea');
        textarea.value = reportContent;
        textarea.style.position = 'fixed';  // Avoid scrolling to bottom
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        try {
            document.execCommand('copy');
            
            // Show success feedback
            const copyButton = document.getElementById('copy-ai-report');
            const originalText = copyButton.innerHTML;
            
            copyButton.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
            copyButton.classList.remove('btn-primary');
            copyButton.classList.add('btn-success');
            
            // Reset after 2 seconds
            setTimeout(() => {
                copyButton.innerHTML = originalText;
                copyButton.classList.remove('btn-success');
                copyButton.classList.add('btn-primary');
            }, 2000);
        } catch (err) {
            console.error('Error copying text: ', err);
            alert('Failed to copy report to clipboard');
        }
        
        document.body.removeChild(textarea);
    }
} 
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
    
    // Set up map controls (they will be connected once the map loads)
    document.getElementById('map-satellite')?.addEventListener('click', () => setMapType('satellite'));
    document.getElementById('map-terrain')?.addEventListener('click', () => setMapType('terrain'));
    document.getElementById('map-zoom-in')?.addEventListener('click', () => zoomMap(1));
    document.getElementById('map-zoom-out')?.addEventListener('click', () => zoomMap(-1));
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
function initMap() {
    mapsLoaded = true;
    // Maps will be initialized when data is loaded
}

// Initialize the property map with coordinates
function initializePropertyMap(latitude, longitude) {
    if (!mapsLoaded) {
        // If Google Maps isn't loaded yet, wait a bit and retry
        setTimeout(() => initializePropertyMap(latitude, longitude), 500);
        return;
    }
    
    // Hide placeholder
    document.getElementById('map-placeholder').style.display = 'none';
    document.getElementById('property-map').style.display = 'block';
    
    const propertyLocation = { lat: latitude, lng: longitude };
    
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
            <h5 style="margin-top: 0; color: #0062cc; font-weight: bold;">${propertyData.summary.stockNumber}</h5>
            <p style="margin-bottom: 8px;"><strong>Location:</strong> ${propertyData.summary.location}</p>
            <p style="margin-bottom: 8px;"><strong>Price:</strong> ${propertyData.summary.price}</p>
            <p style="margin-bottom: 8px;"><strong>Area:</strong> ${propertyData.summary.acres} acres</p>
            <div style="margin-top: 8px; padding: 5px; background-color: #17a2b8; color: white; border-radius: 4px; text-align: center;">
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
    
    // Add event listener to update full map when tab is shown
    document.getElementById('fullmap-tab').addEventListener('shown.bs.tab', function(e) {
        google.maps.event.trigger(fullPropertyMap, 'resize');
        fullPropertyMap.setCenter(propertyLocation);
    });
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
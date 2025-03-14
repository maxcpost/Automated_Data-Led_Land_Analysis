// Dashboard JavaScript

// Store current filter
let currentFilter = 'all';
let scoreChart = null;
let priceChart = null;
let allListings = [];
let sortBy = 'score-desc'; // Default sort order

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Set up filter button clicks
    document.getElementById('all-filter').addEventListener('click', () => setFilter('all'));
    document.getElementById('priced-filter').addEventListener('click', () => setFilter('priced'));
    document.getElementById('nonpriced-filter').addEventListener('click', () => setFilter('nonpriced'));
    
    // Set up search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Set up sort functionality
    const sortSelect = document.getElementById('sort-by');
    if (sortSelect) {
        sortSelect.addEventListener('change', handleSort);
    }
    
    // Set up export button
    const exportButton = document.getElementById('export-csv');
    if (exportButton) {
        exportButton.addEventListener('click', exportToCSV);
    }
    
    // Load initial data
    loadListings('all');
});

// Set active filter
function setFilter(filter) {
    // Don't reload if already on this filter
    if (filter === currentFilter) return;
    
    // Update button styling
    document.querySelectorAll('#filter-buttons .btn').forEach(btn => {
        btn.classList.remove('btn-primary', 'active');
        btn.classList.add('btn-outline-primary');
    });
    
    document.getElementById(`${filter}-filter`).classList.remove('btn-outline-primary');
    document.getElementById(`${filter}-filter`).classList.add('btn-primary', 'active');
    
    // Update current filter and load data
    currentFilter = filter;
    loadListings(filter);
}

// Load listings data from API
function loadListings(filter) {
    // Show loading message
    document.getElementById('listings-data').innerHTML = `
        <tr>
            <td colspan="9" class="text-center">
                <div class="spinner-border text-accent my-5" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading property data...</p>
            </td>
        </tr>
    `;
    
    // Fetch data from API
    fetch(`/api/listings?filter=${filter}`)
        .then(response => response.json())
        .then(data => {
            // Store all listings for charts and searching
            allListings = data.listings;
            
            // Update property count badge
            updatePropertyCount(allListings.length);
            
            // Sort the listings
            sortListings(allListings);
            
            // Display listings
            displayListings(allListings);
            
            // Update charts
            updateCharts(allListings);
        })
        .catch(error => {
            console.error('Error fetching listings:', error);
            document.getElementById('listings-data').innerHTML = 
                '<tr><td colspan="9" class="text-center text-danger">Error loading data. Please try again.</td></tr>';
        });
}

// Update property count in header
function updatePropertyCount(count) {
    const countElement = document.getElementById('total-properties');
    if (countElement) {
        countElement.textContent = count;
    }
    
    // Update results count
    const totalCountElement = document.getElementById('total-count');
    if (totalCountElement) {
        totalCountElement.textContent = count;
    }
    
    const visibleCountElement = document.getElementById('visible-count');
    if (visibleCountElement) {
        visibleCountElement.textContent = count;
    }
}

// Handle sorting
function handleSort(e) {
    sortBy = e.target.value;
    sortListings(allListings);
    displayListings(allListings);
}

// Sort listings based on current sort selection
function sortListings(listings) {
    // Skip if no listings
    if (!listings || listings.length === 0) return;
    
    switch (sortBy) {
        case 'score-desc':
            listings.sort((a, b) => {
                const scoreA = parseFloat(a.Score) || 0;
                const scoreB = parseFloat(b.Score) || 0;
                return scoreB - scoreA;
            });
            break;
        case 'score-asc':
            listings.sort((a, b) => {
                const scoreA = parseFloat(a.Score) || 0;
                const scoreB = parseFloat(b.Score) || 0;
                return scoreA - scoreB;
            });
            break;
        case 'price-desc':
            listings.sort((a, b) => {
                const priceA = parseNumericValue(a['Sale Price']) || 0;
                const priceB = parseNumericValue(b['Sale Price']) || 0;
                return priceB - priceA;
            });
            break;
        case 'price-asc':
            listings.sort((a, b) => {
                const priceA = parseNumericValue(a['Sale Price']) || 0;
                const priceB = parseNumericValue(b['Sale Price']) || 0;
                return priceA - priceB;
            });
            break;
    }
}

// Parse numeric value from formatted string (e.g. "$123,456")
function parseNumericValue(value) {
    if (typeof value !== 'string') return value;
    return parseFloat(value.replace(/[^0-9.-]+/g, ''));
}

// Handle search input
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase().trim();
    
    // If search is empty, show all listings
    if (!searchTerm) {
        document.getElementById('empty-state').classList.add('d-none');
        sortListings(allListings);
        displayListings(allListings);
        return;
    }
    
    // Filter listings based on search term
    const filteredListings = allListings.filter(listing => {
        return Object.values(listing).some(value => {
            if (value === null || value === undefined) return false;
            return String(value).toLowerCase().includes(searchTerm);
        });
    });
    
    // Sort the filtered listings
    sortListings(filteredListings);
    
    // Show empty state if no results
    if (filteredListings.length === 0) {
        document.getElementById('empty-state').classList.remove('d-none');
        document.getElementById('listings-table').classList.add('d-none');
    } else {
        document.getElementById('empty-state').classList.add('d-none');
        document.getElementById('listings-table').classList.remove('d-none');
    }
    
    // Update counts
    const visibleCountElement = document.getElementById('visible-count');
    if (visibleCountElement) {
        visibleCountElement.textContent = filteredListings.length;
    }
    
    // Display filtered listings
    displayListings(filteredListings);
}

// Export data to CSV
function exportToCSV() {
    // Skip if no listings
    if (!allListings || allListings.length === 0) return;
    
    // Create CSV content
    const headers = Object.keys(allListings[0]).join(',');
    const rows = allListings.map(listing => Object.values(listing).map(value => {
        if (value === null || value === undefined) return '';
        return `"${String(value).replace(/"/g, '""')}"`;
    }).join(','));
    
    const csvContent = [headers, ...rows].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `adla_properties_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Display listings in table
function displayListings(listings) {
    const tableBody = document.getElementById('listings-data');
    
    // Check if we have listings
    if (!listings || listings.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center">No listings found.</td></tr>';
        return;
    }
    
    // Generate table rows
    let html = '';
    listings.forEach(listing => {
        // Format numbers for display
        const formatNumber = (val) => {
            if (val === null || val === undefined || val === 'N/A') return 'N/A';
            // If already formatted with $ or , just return as is
            if (typeof val === 'string' && (val.includes('$') || val.includes(','))) return val;
            // Otherwise format as number
            return !isNaN(val) ? Number(val).toLocaleString() : val;
        };
        
        // Make stock number a clickable link
        const stockNumberDisplay = listing.StockNumber ? 
            `<a href="/property/${listing.StockNumber}" class="text-primary stock-number-link">${listing.StockNumber}</a>` : 
            'N/A';
        
        html += `
            <tr>
                <td>${stockNumberDisplay}</td>
                <td class="number-cell">${listing['Sale Price'] || 'N/A'}</td>
                <td class="number-cell">${formatNumber(listing.Acres)}</td>
                <td class="number-cell">${listing['Price/Acre'] || 'N/A'}</td>
                <td class="number-cell">${formatNumber(listing.Demand)}</td>
                <td class="number-cell">${formatNumber(listing['Housing Gap'])}</td>
                <td class="number-cell">${formatNumber(listing.Affordability)}</td>
                <td class="number-cell">${formatNumber(listing.Convenience)}</td>
                <td class="number-cell score-cell">${listing.Score || 'N/A'}</td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
    
    // Add click handlers for the entire row
    document.querySelectorAll('#listings-table tbody tr').forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if they clicked on the stock number link directly
            if (e.target.classList.contains('stock-number-link')) {
                return;
            }
            
            // Get stock number from the first cell
            const stockNumberLink = this.querySelector('.stock-number-link');
            if (stockNumberLink) {
                window.location.href = stockNumberLink.href;
            }
        });
    });
}

// Update charts with new data
function updateCharts(listings) {
    // Prepare data for score chart
    const scoreData = prepareScoreChartData(listings);
    updateScoreChart(scoreData);
    
    // Prepare data for price chart
    const priceData = preparePriceChartData(listings);
    updatePriceChart(priceData);
}

// Prepare data for score chart
function prepareScoreChartData(listings) {
    // Get all valid composite scores
    const scores = listings.map(item => {
        // Extract number from string if needed
        if (typeof item.Score === 'string') {
            return parseFloat(item.Score);
        }
        return item.Score;
    }).filter(score => !isNaN(score) && score !== null);
    
    // Create bins for histogram (0.0-0.1, 0.1-0.2, etc.)
    const bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
    const labels = bins.slice(0, -1).map((bin, i) => `${bin.toFixed(1)}-${bins[i+1].toFixed(1)}`);
    
    // Count listings in each bin
    const counts = Array(bins.length - 1).fill(0);
    
    scores.forEach(score => {
        for (let i = 0; i < bins.length - 1; i++) {
            if (score >= bins[i] && score < bins[i+1]) {
                counts[i]++;
                break;
            }
            // Handle the case where score is exactly 1.0
            if (score === 1.0 && i === bins.length - 2) {
                counts[i]++;
            }
        }
    });
    
    return { labels, counts };
}

// Update score distribution chart
function updateScoreChart(data) {
    const ctx = document.getElementById('score-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (scoreChart) {
        scoreChart.destroy();
    }
    
    // Create new chart
    scoreChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Number of Properties',
                data: data.counts,
                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                borderColor: 'rgb(13, 110, 253)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Properties'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Composite Score Range'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Distribution of Composite Scores'
                }
            }
        }
    });
}

// Prepare data for price chart
function preparePriceChartData(listings) {
    // Extract prices and remove any non-numeric values
    const prices = listings.map(item => {
        if (typeof item['Price/Acre'] === 'string') {
            // Remove $ and commas
            return parseFloat(item['Price/Acre'].replace(/[$,]/g, ''));
        }
        return item['Price/Acre'];
    }).filter(price => !isNaN(price) && price !== null);
    
    // Skip if no valid prices
    if (prices.length === 0) {
        return { labels: [], counts: [] };
    }
    
    // Find min and max prices (rounded to nearest 10,000)
    const minPrice = Math.floor(Math.min(...prices) / 10000) * 10000;
    const maxPrice = Math.ceil(Math.max(...prices) / 10000) * 10000;
    
    // Create price ranges (bins)
    const binSize = Math.max(10000, Math.ceil((maxPrice - minPrice) / 10 / 10000) * 10000);
    const bins = [];
    for (let i = minPrice; i <= maxPrice; i += binSize) {
        bins.push(i);
    }
    if (bins.length <= 1) {
        bins.push(maxPrice + binSize);
    }
    
    // Create labels for each bin
    const labels = bins.slice(0, -1).map((bin, i) => {
        return `$${(bin/1000).toFixed(0)}k-$${(bins[i+1]/1000).toFixed(0)}k`;
    });
    
    // Count listings in each bin
    const counts = Array(bins.length - 1).fill(0);
    
    prices.forEach(price => {
        for (let i = 0; i < bins.length - 1; i++) {
            if (price >= bins[i] && price < bins[i+1]) {
                counts[i]++;
                break;
            }
            // Handle the case where price is exactly the max
            if (price === bins[bins.length-1] && i === bins.length - 2) {
                counts[i]++;
            }
        }
    });
    
    return { labels, counts };
}

// Update price distribution chart
function updatePriceChart(data) {
    const ctx = document.getElementById('price-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (priceChart) {
        priceChart.destroy();
    }
    
    // Skip if no data
    if (data.labels.length === 0) {
        return;
    }
    
    // Create new chart
    priceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Number of Properties',
                data: data.counts,
                backgroundColor: 'rgba(25, 135, 84, 0.7)',
                borderColor: 'rgb(25, 135, 84)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Properties'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Price per Acre'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Distribution of Price per Acre'
                }
            }
        }
    });
} 
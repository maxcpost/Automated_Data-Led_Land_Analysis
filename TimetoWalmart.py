async function findNearestWalmart(locations, apiKey) {
  if (!apiKey) {
    throw new Error('Google Maps API key is required');
  }

  // Function to find nearest Walmart using Places API
  async function findWalmartNearLocation(lat, lng) {
    const placesEndpoint = `https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=${lat},${lng}&radius=50000&keyword=walmart&type=store&key=${apiKey}`;
    
    try {
      const response = await fetch(placesEndpoint);
      const data = await response.json();
      
      if (data.status === 'OK' && data.results.length > 0) {
        return data.results[0]; // Return nearest Walmart
      }
      return null;
    } catch (error) {
      console.error('Error finding Walmart:', error);
      return null;
    }
  }

  // Function to calculate travel time
  async function calculateTravelTime(origin, destination) {
    const distanceEndpoint = `https://maps.googleapis.com/maps/api/distancematrix/json?origins=${origin.lat},${origin.lng}&destinations=${destination.lat},${destination.lng}&mode=driving&key=${apiKey}`;
    
    try {
      const response = await fetch(distanceEndpoint);
      const data = await response.json();
      
      if (data.status === 'OK' && data.rows[0].elements[0].status === 'OK') {
        return {
          duration: data.rows[0].elements[0].duration.text,
          durationValue: data.rows[0].elements[0].duration.value, // seconds
          distance: data.rows[0].elements[0].distance.text
        };
      }
      return null;
    } catch (error) {
      console.error('Error calculating travel time:', error);
      return null;
    }
  }

  // Process CSV data
  async function processLocations() {
    const results = [];
    
    for (const location of locations) {
      try {
        // Find nearest Walmart
        const nearestWalmart = await findWalmartNearLocation(
          location.latitude,
          location.longitude
        );
        
        if (nearestWalmart) {
          // Calculate travel time
          const travelInfo = await calculateTravelTime(
            { lat: location.latitude, lng: location.longitude },
            { 
              lat: nearestWalmart.geometry.location.lat,
              lng: nearestWalmart.geometry.location.lng
            }
          );
          
          results.push({
            originalLocation: {
              latitude: location.latitude,
              longitude: location.longitude,
              address: location.address || 'Not provided'
            },
            nearestWalmart: {
              name: nearestWalmart.name,
              address: nearestWalmart.vicinity,
              latitude: nearestWalmart.geometry.location.lat,
              longitude: nearestWalmart.geometry.location.lng
            },
            travelInfo: travelInfo
          });
        }
        
        // Add delay to respect API rate limits
        await new Promise(resolve => setTimeout(resolve, 200));
        
      } catch (error) {
        console.error('Error processing location:', error);
        results.push({
          originalLocation: {
            latitude: location.latitude,
            longitude: location.longitude,
            address: location.address || 'Not provided'
          },
          error: error.message
        });
      }
    }
    
    return results;
  }

  return await processLocations();
}

// Example usage with CSV data
import Papa from 'papaparse';

async function processCSVFile(csvContent, apiKey) {
  // Parse CSV
  const parsedData = Papa.parse(csvContent, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true // Automatically convert numbers
  });

  // Process the locations
  const results = await findNearestWalmart(parsedData.data, apiKey);
  return results;
}

// Example of reading and processing a CSV file
async function main() {
  try {
    const csvContent = await window.fs.readFile('locations.csv', { encoding: 'utf8' });
    const GOOGLE_MAPS_API_KEY = 'YOUR_API_KEY_HERE';
    
    const results = await processCSVFile(csvContent, GOOGLE_MAPS_API_KEY);
    console.log('Results:', results);
    
  } catch (error) {
    console.error('Error:', error);
  }
}

export { findNearestWalmart, processCSVFile };
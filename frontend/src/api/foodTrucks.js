// All calls to the food truck API live here, so components never build URLs themselves.
import { apiRequest } from './apiRequest.js'

/**
 * Fetch trucks within radiusMiles of a point.
 * Returns a GeoJSON FeatureCollection: { type, features: [...] }
 */
export async function fetchNearbyFoodTrucks({ latitude, longitude, radiusMiles, openOnly }) {
  const queryParameters = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    radius_miles: String(radiusMiles),
  })
  if (openOnly) {
    queryParameters.set('open_only', 'true')
  }

  const response = await fetch(`/api/trucks/nearby/?${queryParameters.toString()}`)
  if (!response.ok) {
    throw new Error(`Nearby truck request failed with status ${response.status}`)
  }
  return response.json()
}

/** Trucks the logged-in owner can check in (staff see all). GeoJSON FeatureCollection. */
export function fetchMyFoodTrucks() {
  return apiRequest('/api/trucks/mine/')
}

/** Opens the truck at the given spot until openUntil (a Date). */
export function checkInFoodTruck({ truckId, latitude, longitude, openUntil }) {
  return apiRequest(`/api/trucks/${truckId}/check-in/`, {
    method: 'POST',
    body: { latitude, longitude, open_until: openUntil.toISOString() },
  })
}

/** Closes the truck immediately. */
export function checkOutFoodTruck({ truckId }) {
  return apiRequest(`/api/trucks/${truckId}/check-out/`, { method: 'POST' })
}

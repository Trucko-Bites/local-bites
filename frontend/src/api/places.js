// Place search: turns a typed city or address into coordinates (via our backend,
// which calls OpenStreetMap Nominatim with caching and rate limiting).
import { apiRequest } from './apiRequest.js'

/**
 * Returns up to 5 matches: [{ display_name, latitude, longitude }, ...]
 * Throws an Error with a readable message (e.g. "Place search is busy...").
 */
export async function searchPlaces({ searchText }) {
  const queryParameters = new URLSearchParams({ query: searchText })
  const responseBody = await apiRequest(`/api/places/search/?${queryParameters.toString()}`)
  return responseBody.results
}

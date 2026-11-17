import { useEffect, useRef } from 'react'
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'

const METERS_PER_MILE = 1609.344
const SELECTED_TRUCK_ZOOM = 14

// OpenStreetMap's public tiles are fine for development. Before real traffic,
// point VITE_TILE_URL at a hosted tile provider (see README).
const TILE_URL = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/**
 * Centers the map on the user, but only when the location SOURCE changes:
 * once for the fallback area, and once when the first real GPS fix arrives.
 * GPS readings drift a few meters constantly; re-centering on every reading
 * would keep yanking the map away from a truck the user just selected.
 */
function CenterOnUserLocation({ latitude, longitude, isUsingFallback }) {
  const leafletMap = useMap()
  const centeredForSourceRef = useRef(null) // "fallback" or "real" once centered

  useEffect(() => {
    const locationSource = isUsingFallback ? 'fallback' : 'real'
    if (centeredForSourceRef.current !== locationSource) {
      leafletMap.setView([latitude, longitude])
      centeredForSourceRef.current = locationSource
    }
  }, [leafletMap, latitude, longitude, isUsingFallback])

  return null
}

/** Smoothly pans and zooms to a truck when it is picked from the list. */
function FlyToSelectedTruck({ selectedTruckFeature }) {
  const leafletMap = useMap()
  const selectedTruckId = selectedTruckFeature?.id

  useEffect(() => {
    if (!selectedTruckFeature) return
    // GeoJSON coordinates are [longitude, latitude]; Leaflet wants [latitude, longitude]
    const [truckLongitude, truckLatitude] = selectedTruckFeature.geometry.coordinates
    leafletMap.flyTo([truckLatitude, truckLongitude], Math.max(leafletMap.getZoom(), SELECTED_TRUCK_ZOOM))
    // Only fly when a DIFFERENT truck is selected, not on every 30-second refresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leafletMap, selectedTruckId])

  return null
}

export default function FoodTruckMap({
  userLocation,
  isUsingFallback,
  radiusMiles,
  foodTruckFeatures,
  selectedTruckId,
}) {
  const userPosition = [userLocation.latitude, userLocation.longitude]
  const selectedTruckFeature = foodTruckFeatures.find((truckFeature) => truckFeature.id === selectedTruckId)

  return (
    <MapContainer center={userPosition} zoom={12} style={{ height: '100%', width: '100%' }}>
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <CenterOnUserLocation
        latitude={userLocation.latitude}
        longitude={userLocation.longitude}
        isUsingFallback={isUsingFallback}
      />
      <FlyToSelectedTruck selectedTruckFeature={selectedTruckFeature} />

      {/* The search radius ("geofence") drawn around the user */}
      <Circle
        center={userPosition}
        radius={radiusMiles * METERS_PER_MILE}
        pathOptions={{ color: '#1976d2', fillOpacity: 0.05 }}
      />
      <CircleMarker center={userPosition} radius={7} pathOptions={{ color: '#1976d2', fillOpacity: 1 }}>
        <Popup>You are here</Popup>
      </CircleMarker>

      {foodTruckFeatures.map((truckFeature) => {
        const [truckLongitude, truckLatitude] = truckFeature.geometry.coordinates
        const truckProperties = truckFeature.properties
        const isSelected = truckFeature.id === selectedTruckId
        return (
          <CircleMarker
            key={truckFeature.id}
            center={[truckLatitude, truckLongitude]}
            radius={isSelected ? 12 : 9}
            pathOptions={{
              color: truckProperties.is_open ? '#2e7d32' : '#757575',
              fillOpacity: 0.85,
              weight: isSelected ? 4 : 3, // thicker ring marks the selected truck
            }}
          >
            <Popup>
              <strong>{truckProperties.name}</strong>
              <br />
              {truckProperties.cuisine}
              <br />
              {truckProperties.distance_miles} mi away · {truckProperties.is_open ? 'Open' : 'Closed'}
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

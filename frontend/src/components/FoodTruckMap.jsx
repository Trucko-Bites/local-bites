import { useEffect, useRef } from 'react'
import Button from '@mui/material/Button'
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'

const METERS_PER_MILE = 1609.344
const SELECTED_TRUCK_ZOOM = 14

// OpenStreetMap's public tiles are fine for development. Before real traffic,
// point VITE_TILE_URL at a hosted tile provider (see DEVELOPMENT.md).
const TILE_URL = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/**
 * Centers the map on the search center, but only when the location SOURCE
 * changes: the fallback area, the first real GPS fix, or a newly searched
 * place (each has its own locationSourceKey). GPS readings drift a few meters
 * constantly; re-centering on every reading would keep yanking the map away
 * from a truck the user just selected.
 */
function CenterOnSearchCenter({ latitude, longitude, locationSourceKey }) {
  const leafletMap = useMap()
  const centeredForSourceKeyRef = useRef(null) // last key the map centered for

  useEffect(() => {
    if (centeredForSourceKeyRef.current !== locationSourceKey) {
      leafletMap.setView([latitude, longitude])
      centeredForSourceKeyRef.current = locationSourceKey
    }
  }, [leafletMap, latitude, longitude, locationSourceKey])

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
  searchCenter, // { latitude, longitude }: the user's location or a searched place
  searchCenterLabel, // popup text for the center marker
  locationSourceKey, // changes when the map should re-center (see CenterOnSearchCenter)
  radiusMiles,
  foodTruckFeatures,
  selectedTruckId,
  onSelectTruck,
}) {
  // Leaflet wants [latitude, longitude]
  const searchCenterPosition = [searchCenter.latitude, searchCenter.longitude]
  const selectedTruckFeature = foodTruckFeatures.find((truckFeature) => truckFeature.id === selectedTruckId)

  return (
    <MapContainer center={searchCenterPosition} zoom={12} style={{ height: '100%', width: '100%' }}>
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <CenterOnSearchCenter
        latitude={searchCenter.latitude}
        longitude={searchCenter.longitude}
        locationSourceKey={locationSourceKey}
      />
      <FlyToSelectedTruck selectedTruckFeature={selectedTruckFeature} />

      {/* The search radius ("geofence") drawn around the search center */}
      <Circle
        center={searchCenterPosition}
        radius={radiusMiles * METERS_PER_MILE}
        pathOptions={{ color: '#1976d2', fillOpacity: 0.05 }}
      />
      <CircleMarker center={searchCenterPosition} radius={7} pathOptions={{ color: '#1976d2', fillOpacity: 1 }}>
        <Popup>{searchCenterLabel}</Popup>
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
              <br />
              <Button size="small" sx={{ marginTop: 1 }} onClick={() => onSelectTruck(truckFeature.id)}>
                View Details
              </Button>
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

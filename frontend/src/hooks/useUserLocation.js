import { useEffect, useState } from 'react'

// Used until the browser reports a real position (downtown Redlands, CA)
const FALLBACK_LOCATION = { latitude: 34.0556, longitude: -117.1825 }

/**
 * Follows the user's position with the browser Geolocation API.
 * watchPosition keeps reporting as the user moves, which is what makes
 * the "geofence" (trucks within N miles of me) update on its own.
 *
 * Note: browsers only allow geolocation on HTTPS pages or on localhost.
 */
const IS_GEOLOCATION_SUPPORTED = typeof navigator !== 'undefined' && 'geolocation' in navigator

export function useUserLocation() {
  const [userLocation, setUserLocation] = useState(FALLBACK_LOCATION)
  // Start with the "unsupported" message instead of setting it inside the effect
  const [locationError, setLocationError] = useState(
    IS_GEOLOCATION_SUPPORTED ? null : 'This browser does not support location services.',
  )
  const [isUsingFallback, setIsUsingFallback] = useState(true)

  useEffect(() => {
    if (!IS_GEOLOCATION_SUPPORTED) {
      return undefined
    }

    const watchIdentifier = navigator.geolocation.watchPosition(
      (position) => {
        setUserLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        })
        setIsUsingFallback(false)
        setLocationError(null)
      },
      (positionError) => {
        setLocationError(positionError.message)
      },
      // maximumAge lets the browser reuse a reading up to 30s old (saves battery)
      { enableHighAccuracy: true, maximumAge: 30000, timeout: 15000 },
    )

    // Stop watching when the component using this hook unmounts
    return () => navigator.geolocation.clearWatch(watchIdentifier)
  }, [])

  return { userLocation, locationError, isUsingFallback }
}

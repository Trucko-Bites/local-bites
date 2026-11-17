import { useEffect, useState } from 'react'
import Alert from '@mui/material/Alert'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import FormControlLabel from '@mui/material/FormControlLabel'
import Paper from '@mui/material/Paper'
import Slider from '@mui/material/Slider'
import Switch from '@mui/material/Switch'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import StorefrontIcon from '@mui/icons-material/Storefront'

import { fetchNearbyFoodTrucks } from './api/foodTrucks.js'
import FoodTruckList from './components/FoodTruckList.jsx'
import FoodTruckMap from './components/FoodTruckMap.jsx'
import OwnerPanel from './components/OwnerPanel.jsx'
import { useUserLocation } from './hooks/useUserLocation.js'

// How often the map re-checks for trucks that checked in or closed
const REFRESH_INTERVAL_MILLISECONDS = 30000

export default function App() {
  const { userLocation, locationError, isUsingFallback } = useUserLocation()
  // sliderRadiusMiles moves while dragging (redraws the circle);
  // radiusMiles only changes on release (triggers the API call)
  const [sliderRadiusMiles, setSliderRadiusMiles] = useState(5)
  const [radiusMiles, setRadiusMiles] = useState(5)
  const [openOnly, setOpenOnly] = useState(false)
  const [foodTruckFeatures, setFoodTruckFeatures] = useState([])
  const [selectedTruckId, setSelectedTruckId] = useState(null)
  const [requestError, setRequestError] = useState(null)
  const [isOwnerPanelOpen, setIsOwnerPanelOpen] = useState(false)
  // Bumping this number re-runs the nearby query immediately (after a check-in)
  const [refreshRequestCount, setRefreshRequestCount] = useState(0)

  // Query right away whenever the user moves or changes the radius/filter,
  // then keep re-querying every REFRESH_INTERVAL_MILLISECONDS so owner
  // check-ins show up without the customer doing anything.
  useEffect(() => {
    let isCurrentEffect = true // ignore responses that arrive after the inputs changed

    function loadNearbyFoodTrucks() {
      fetchNearbyFoodTrucks({
        latitude: userLocation.latitude,
        longitude: userLocation.longitude,
        radiusMiles,
        openOnly,
      })
        .then((featureCollection) => {
          if (isCurrentEffect) {
            setFoodTruckFeatures(featureCollection.features)
            setRequestError(null)
          }
        })
        .catch((error) => {
          if (isCurrentEffect) setRequestError(error.message)
        })
    }

    loadNearbyFoodTrucks()

    const refreshIntervalIdentifier = setInterval(() => {
      // Skip refreshes while the tab is in the background; saves requests and battery
      if (document.visibilityState === 'visible') {
        loadNearbyFoodTrucks()
      }
    }, REFRESH_INTERVAL_MILLISECONDS)

    // Runs when inputs change or the component unmounts: stop the old timer
    // so only one refresh loop is ever running
    return () => {
      isCurrentEffect = false
      clearInterval(refreshIntervalIdentifier)
    }
  }, [userLocation.latitude, userLocation.longitude, radiusMiles, openOnly, refreshRequestCount])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* enableColorOnDark keeps the orange brand bar in dark mode (MUI greys it out by default) */}
      <AppBar position="static" enableColorOnDark>
        <Toolbar>
          <LocalShippingIcon sx={{ marginRight: 1 }} />
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Food Truck Finder
          </Typography>
          <Button color="inherit" startIcon={<StorefrontIcon />} onClick={() => setIsOwnerPanelOpen(true)}>
            Owner
          </Button>
        </Toolbar>
      </AppBar>

      <OwnerPanel
        isOpen={isOwnerPanelOpen}
        onClose={() => setIsOwnerPanelOpen(false)}
        onTrucksChanged={() => setRefreshRequestCount((previousCount) => previousCount + 1)}
      />

      {isUsingFallback && (
        <Alert severity="info">
          {locationError
            ? `Location unavailable (${locationError}). Showing a default area.`
            : 'Waiting for your location...'}
        </Alert>
      )}
      {requestError && <Alert severity="error">{requestError}</Alert>}

      {/* Map on the left, controls + list on the right; stacks on phones */}
      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box
          sx={[
            { flex: 1, minHeight: { xs: 300, md: 0 } },
            // In dark mode, dim the bright map tiles so they don't glare next to
            // the dark panel. Only the tile layer is filtered; markers stay vivid.
            (theme) =>
              theme.applyStyles('dark', {
                '& .leaflet-tile-pane': { filter: 'brightness(0.7) contrast(1.1)' },
              }),
          ]}
        >
          <FoodTruckMap
            userLocation={userLocation}
            isUsingFallback={isUsingFallback}
            radiusMiles={sliderRadiusMiles}
            foodTruckFeatures={foodTruckFeatures}
            selectedTruckId={selectedTruckId}
          />
        </Box>

        <Paper square sx={{ width: { xs: '100%', md: 360 }, overflowY: 'auto' }}>
          <Box sx={{ padding: 2 }}>
            <Typography gutterBottom>Search radius: {sliderRadiusMiles} mi</Typography>
            <Slider
              value={sliderRadiusMiles}
              min={1}
              max={50}
              step={1}
              valueLabelDisplay="auto"
              onChange={(_event, newRadius) => setSliderRadiusMiles(newRadius)}
              // onChangeCommitted fires once on release, not on every pixel dragged
              onChangeCommitted={(_event, newRadius) => setRadiusMiles(newRadius)}
            />
            <FormControlLabel
              control={<Switch checked={openOnly} onChange={(event) => setOpenOnly(event.target.checked)} />}
              label="Open now only"
            />
          </Box>
          <FoodTruckList
            foodTruckFeatures={foodTruckFeatures}
            selectedTruckId={selectedTruckId}
            onSelectTruck={setSelectedTruckId}
          />
        </Paper>
      </Box>
    </Box>
  )
}

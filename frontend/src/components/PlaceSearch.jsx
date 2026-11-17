import { useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import IconButton from '@mui/material/IconButton'
import InputAdornment from '@mui/material/InputAdornment'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import MyLocationIcon from '@mui/icons-material/MyLocation'
import SearchIcon from '@mui/icons-material/Search'

import { searchPlaces } from '../api/places.js'

/**
 * "Search a different area" box. Searches only when the user submits
 * (Enter or the search button), never while typing: Nominatim's usage
 * policy forbids search-as-you-type.
 *
 * Props:
 *   searchedPlaceName  name of the place being shown, or null when using GPS
 *   onPlaceSelected    called with { displayName, latitude, longitude }
 *   onUseMyLocation    switches back to the browser's GPS location
 */
export default function PlaceSearch({ searchedPlaceName, onPlaceSelected, onUseMyLocation }) {
  const [searchText, setSearchText] = useState('')
  const [placeResults, setPlaceResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchMessage, setSearchMessage] = useState(null) // errors and "no matches"

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault() // stop the browser from reloading the page
    const trimmedSearchText = searchText.trim()
    if (trimmedSearchText.length < 2) {
      setSearchMessage('Type at least 2 characters.')
      return
    }

    setIsSearching(true)
    setSearchMessage(null)
    setPlaceResults([])
    try {
      const foundPlaces = await searchPlaces({ searchText: trimmedSearchText })
      if (foundPlaces.length === 0) {
        setSearchMessage('No matching places. Try adding a state, like "Riverside, CA".')
      }
      setPlaceResults(foundPlaces)
    } catch (searchError) {
      setSearchMessage(searchError.message)
    } finally {
      setIsSearching(false)
    }
  }

  function handleChoosePlace(chosenPlace) {
    onPlaceSelected({
      displayName: chosenPlace.display_name,
      latitude: chosenPlace.latitude,
      longitude: chosenPlace.longitude,
    })
    // Clear the box and the result list once a place is picked
    setPlaceResults([])
    setSearchText('')
    setSearchMessage(null)
  }

  return (
    <Box>
      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          size="small"
          label="Search a city or address"
          value={searchText}
          onChange={(changeEvent) => setSearchText(changeEvent.target.value)}
          disabled={isSearching}
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton type="submit" aria-label="Search" edge="end" disabled={isSearching}>
                    <SearchIcon />
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
        />
      </form>

      {searchMessage && (
        <Alert severity="warning" sx={{ marginTop: 1 }}>
          {searchMessage}
        </Alert>
      )}

      {placeResults.length > 0 && (
        <List dense>
          {placeResults.map((placeResult) => (
            <ListItemButton
              // Two places can share a name, so include the coordinates in the key
              key={`${placeResult.display_name}-${placeResult.latitude}-${placeResult.longitude}`}
              onClick={() => handleChoosePlace(placeResult)}
            >
              <ListItemText primary={placeResult.display_name} />
            </ListItemButton>
          ))}
        </List>
      )}

      {searchedPlaceName && (
        <Box sx={{ marginTop: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Showing trucks near {searchedPlaceName}
          </Typography>
          <Button size="small" startIcon={<MyLocationIcon />} onClick={onUseMyLocation}>
            Use my location
          </Button>
        </Box>
      )}
    </Box>
  )
}

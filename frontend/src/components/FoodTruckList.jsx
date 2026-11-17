import Chip from '@mui/material/Chip'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'

/** Side list of nearby trucks, closest first (the API already sorts them). */
export default function FoodTruckList({ foodTruckFeatures, selectedTruckId, onSelectTruck }) {
  if (foodTruckFeatures.length === 0) {
    return (
      <Typography sx={{ padding: 2 }} color="text.secondary">
        No trucks in this radius. Try widening the search.
      </Typography>
    )
  }

  return (
    <List dense>
      {foodTruckFeatures.map((truckFeature) => {
        const truckProperties = truckFeature.properties
        return (
          <ListItemButton
            key={truckFeature.id}
            selected={truckFeature.id === selectedTruckId}
            onClick={() => onSelectTruck(truckFeature.id)}
          >
            <ListItemText
              primary={truckProperties.name}
              secondary={`${truckProperties.cuisine || 'Food'} · ${truckProperties.distance_miles} mi`}
            />
            <Chip
              size="small"
              label={truckProperties.is_open ? 'Open' : 'Closed'}
              color={truckProperties.is_open ? 'success' : 'default'}
              // Outlined "Closed" keeps a visible border in both light and dark mode
              variant={truckProperties.is_open ? 'filled' : 'outlined'}
            />
          </ListItemButton>
        )
      })}
    </List>
  )
}

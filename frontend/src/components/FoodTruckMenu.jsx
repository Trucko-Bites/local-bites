
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import Chip from '@mui/material/Chip'

const sampleMenu = [
  {
    id: 1,
    category: 'Burgers',
    name: 'Backyard Burger',
    description: 'Classic burger with house toppings',
    price: '12.00',
    is_available: true,
  },
  {
    id: 2,
    category: 'Burgers',
    name: 'Route 66 Burger',
    description: '',
    price: '12.00',
    is_available: true,
  },
  {
    id: 3,
    category: 'Sides',
    name: 'Rustic Russets',
    description: '',
    price: '6.00',
    is_available: false,
  },
]

// Temporary sample data for testing the UI.
// Replace with API data when the backend is ready.
export default function FoodTruckMenu({ truckId, items = sampleMenu }) {
  const categories = [...new Set(items.map((item) => item.category || 'Other'))]

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Menu
      </Typography>

      {items.length === 0 && (
        <Typography color="text.secondary">
          No menu is available for this truck yet.
        </Typography>
      )}

      {categories.map((category) => (
        <Box key={category} sx={{ mb: 3 }}>
          <Typography
            variant="subtitle1"
            fontWeight="bold"
            sx={{ mb: 1 }}
          >
            {category}
          </Typography>

          <Divider sx={{ mb: 1 }} />

          {items
            .filter((item) => (item.category || 'Other') === category)
            .map((item) => (
              <Box
                key={item.id}
                sx={{ py: 1.5 }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 2,
                    alignItems: 'flex-start',
                  }}
                >
                  <Typography fontWeight="medium">
                    {item.name}
                  </Typography>

                  <Typography fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
                    {item.price == null || item.price === ''
                      ? 'Ask for price'
                      : `$${Number(item.price).toFixed(2)}`}
                  </Typography>
                </Box>

                {item.description && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    {item.description}
                  </Typography>
                )}

                {item.is_available === false && (
                  <Chip
                    label="Sold Out"
                    size="small"
                    color="error"
                    variant="outlined"
                    sx={{ mt: 1 }}
                  />
                )}
              </Box>
            ))}
        </Box>
      ))}
    </Box>
  )
}


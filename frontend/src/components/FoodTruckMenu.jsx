import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import Chip from '@mui/material/Chip'


const menuByCuisine = {
  mexican: [
    { id: 1, category: 'Tacos', name: 'Birria Tacos', description: 'Slow-braised beef with consommé', price: '14.00', is_available: true },
    { id: 2, category: 'Tacos', name: 'Carne Asada Tacos', description: 'Grilled steak, cilantro, and onion', price: '12.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Street Corn', description: 'Elote with cotija cheese', price: '6.00', is_available: true },
  ],
  thai: [
    { id: 1, category: 'Noodles', name: 'Pad Thai', description: 'Rice noodles with tamarind sauce', price: '14.00', is_available: true },
    { id: 2, category: 'Curry', name: 'Green Curry', description: 'Coconut curry with vegetables', price: '15.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Vegetable Spring Rolls', description: 'Served with sweet chili sauce', price: '7.00', is_available: true },
  ],
  italian: [
    { id: 1, category: 'Pasta', name: 'Chicken Alfredo', description: 'Creamy Alfredo sauce over pasta', price: '16.00', is_available: true },
    { id: 2, category: 'Sandwiches', name: 'Meatball Sub', description: 'Meatballs, marinara, and mozzarella', price: '13.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Garlic Bread', description: 'Toasted bread with garlic butter', price: '5.00', is_available: true },
  ],
  bbq: [
    { id: 1, category: 'BBQ', name: 'Smoked Brisket', description: 'Slow-smoked beef brisket', price: '18.00', is_available: true },
    { id: 2, category: 'BBQ', name: 'Pulled Pork Sandwich', description: 'Smoked pork with BBQ sauce', price: '14.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Mac and Cheese', description: 'Creamy cheddar macaroni', price: '6.00', is_available: true },
  ],
  puerto_rican: [
    { id: 1, category: 'Entrees', name: 'Mofongo', description: 'Mashed plantains with garlic', price: '15.00', is_available: true },
    { id: 2, category: 'Entrees', name: 'Pernil', description: 'Slow-roasted pork shoulder', price: '16.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Arroz con Gandules', description: 'Rice with pigeon peas', price: '6.00', is_available: true },
  ],
  american: [
    { id: 1, category: 'Burgers', name: 'Classic Smash Burger', description: 'Beef patty with cheese and house sauce', price: '12.00', is_available: true },
    { id: 2, category: 'Sandwiches', name: 'Crispy Chicken Sandwich', description: 'Crispy chicken with pickles', price: '13.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Loaded Fries', description: 'Fries topped with cheese and bacon', price: '8.00', is_available: true },
  ],
  mediterranean: [
    { id: 1, category: 'Wraps', name: 'Chicken Shawarma', description: 'Seasoned chicken with garlic sauce', price: '14.00', is_available: true },
    { id: 2, category: 'Wraps', name: 'Falafel Wrap', description: 'Falafel with tahini and vegetables', price: '12.00', is_available: true },
    { id: 3, category: 'Sides', name: 'Hummus and Pita', description: 'Chickpea hummus with warm pita', price: '7.00', is_available: true },
  ],
}

const getCuisineMenu = (cuisine = '') => {
  const type = cuisine.toLowerCase()

  if (type.includes('mexican') || type.includes('taco')) return menuByCuisine.mexican
  if (type.includes('thai')) return menuByCuisine.thai
  if (type.includes('italian') || type.includes('pasta')) return menuByCuisine.italian
  if (type.includes('bbq') || type.includes('barbecue')) return menuByCuisine.bbq
  if (type.includes('puerto rican')) return menuByCuisine.puerto_rican
  if (type.includes('mediterranean') || type.includes('greek')) return menuByCuisine.mediterranean
  if (type.includes('american') || type.includes('burger')) return menuByCuisine.american

  return []
}


// Changed menu items based on cuisine types
export default function FoodTruckMenu({ truckId, cuisine, items }) {
  const menuItems = items ?? getCuisineMenu(cuisine)

  const categories = [
    ...new Set(menuItems.map((item) => item.category || 'Other'))
  ]

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Menu
      </Typography>

      {menuItems.length === 0 && (
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

          {menuItems
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


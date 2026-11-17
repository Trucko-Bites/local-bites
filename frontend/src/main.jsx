import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import 'leaflet/dist/leaflet.css' // Leaflet's map styles; the map renders broken without this
import App from './App.jsx'

const FOOD_TRUCK_ORANGE = '#e65100'

// Real light AND dark themes. Every MUI component (switch, chips, list text)
// gets colors designed for each mode, instead of the browser guessing by
// force-darkening a light-only page.
const appTheme = createTheme({
  colorSchemes: {
    light: { palette: { primary: { main: FOOD_TRUCK_ORANGE } } },
    dark: { palette: { primary: { main: FOOD_TRUCK_ORANGE } } },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* defaultMode="system" follows the operating system's light/dark setting */}
    <ThemeProvider theme={appTheme} defaultMode="system">
      {/* CssBaseline resets browser default styles and sets the page background per mode */}
      <CssBaseline enableColorScheme />
      <App />
    </ThemeProvider>
  </StrictMode>,
)

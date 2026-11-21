// The shared login state. AuthProvider fills it in; components read it with useAuth().
// Kept in its own file so AuthProvider.jsx only exports a component (fast refresh needs that).
import { createContext } from 'react'

export const AuthContext = createContext(null)

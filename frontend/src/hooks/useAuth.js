import { useContext } from 'react'
import { AuthContext } from '../auth/authContext.js'

/**
 * Who is logged in, plus the login actions. Returns:
 *   currentUser        undefined = still checking, null = logged out, { username, is_staff } = logged in
 *   logIn, register, logOut
 *   openAccountDialog('login' | 'signup')
 */
export function useAuth() {
  const authState = useContext(AuthContext)
  if (authState === null) {
    throw new Error('useAuth must be used inside <AuthProvider> (see main.jsx).')
  }
  return authState
}

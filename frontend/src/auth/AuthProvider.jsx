import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchCurrentUser,
  logIn as logInRequest,
  logOut as logOutRequest,
  register as registerRequest,
} from '../api/auth.js'
import AccountDialog from '../components/AccountDialog.jsx'
import { AuthContext } from './authContext.js'

/**
 * Asks the server who is logged in once, when the app loads, and shares the
 * answer with every component (header, reviews, Owner panel) through useAuth().
 * Also owns the one Log in / Sign up dialog so any component can open it.
 */
export default function AuthProvider({ children }) {
  // undefined = still checking, null = logged out, object = logged in
  const [currentUser, setCurrentUser] = useState(undefined)
  const [isAccountDialogOpen, setIsAccountDialogOpen] = useState(false)
  // Kept separately from "open" so the tab doesn't flip while the dialog fades out
  const [accountDialogTab, setAccountDialogTab] = useState('login')

  useEffect(() => {
    let isCurrentEffect = true // ignore the answer if this component unmounted first
    fetchCurrentUser()
      .then((user) => {
        if (isCurrentEffect) setCurrentUser(user)
      })
      .catch(() => {
        // Server unreachable: treat as logged out so the app still works for browsing
        if (isCurrentEffect) setCurrentUser(null)
      })
    return () => {
      isCurrentEffect = false
    }
  }, [])

  const logIn = useCallback(async (credentials) => {
    const user = await logInRequest(credentials)
    setCurrentUser(user)
    return user
  }, [])

  const register = useCallback(async (signUpDetails) => {
    const user = await registerRequest(signUpDetails)
    setCurrentUser(user) // the server already logged the new account in
    return user
  }, [])

  const logOut = useCallback(async () => {
    try {
      await logOutRequest()
    } catch (requestError) {
      // 403 means the session had already expired, which is logged out anyway
      if (requestError.status !== 403) throw requestError
    }
    setCurrentUser(null)
  }, [])

  const openAccountDialog = useCallback((tabName = 'login') => {
    setAccountDialogTab(tabName)
    setIsAccountDialogOpen(true)
  }, [])

  // useMemo: components using useAuth() only re-render when something here changes
  const authState = useMemo(
    () => ({ currentUser, logIn, register, logOut, openAccountDialog }),
    [currentUser, logIn, register, logOut, openAccountDialog],
  )

  return (
    <AuthContext value={authState}>
      {children}
      <AccountDialog
        isOpen={isAccountDialogOpen}
        selectedTab={accountDialogTab}
        onTabChange={setAccountDialogTab}
        onClose={() => setIsAccountDialogOpen(false)}
      />
    </AuthContext>
  )
}

import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import LoginIcon from '@mui/icons-material/Login'
import { useAuth } from '../hooks/useAuth.js'

/**
 * Header account button.
 * Logged out: "Log in / Sign up" opens the account dialog.
 * Logged in: the username; clicking it shows a menu with "Log out".
 */
export default function AccountButton() {
  const { currentUser, logOut, openAccountDialog } = useAuth()
  // The element the menu pops out from; null = menu closed
  const [menuAnchorElement, setMenuAnchorElement] = useState(null)

  // Still asking the server: show nothing rather than flash the wrong button
  if (currentUser === undefined) return null

  if (currentUser === null) {
    return (
      <Button
        color="inherit"
        startIcon={<LoginIcon />}
        onClick={() => openAccountDialog('login')}
        sx={{ whiteSpace: 'nowrap', flexShrink: 0 }} // the title shrinks instead of this label
      >
        {/* Phones get the short label so the header stays on one line */}
        <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
          Log in / Sign up
        </Box>
        <Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>
          Log in
        </Box>
      </Button>
    )
  }

  async function handleLogOut() {
    setMenuAnchorElement(null)
    await logOut()
  }

  return (
    <>
      <Button
        color="inherit"
        startIcon={<AccountCircleIcon />}
        onClick={(event) => setMenuAnchorElement(event.currentTarget)}
        aria-haspopup="menu"
        aria-expanded={Boolean(menuAnchorElement)}
        sx={{ textTransform: 'none', minWidth: 0 }} // show the username as typed, not uppercased
      >
        {/* Long usernames end in "..." instead of pushing the header onto two lines */}
        <Box
          component="span"
          sx={{ maxWidth: { xs: 110, sm: 220 }, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
        >
          {currentUser.username}
        </Box>
      </Button>
      <Menu anchorEl={menuAnchorElement} open={Boolean(menuAnchorElement)} onClose={() => setMenuAnchorElement(null)}>
        <MenuItem onClick={handleLogOut}>Log out</MenuItem>
      </Menu>
    </>
  )
}

import { useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import Stack from '@mui/material/Stack'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import TextField from '@mui/material/TextField'
import { useAuth } from '../hooks/useAuth.js'

// Matches Django's default password validators in backend settings
const PASSWORD_HINT = 'At least 8 characters. Not all numbers, not a common password, not like your username.'

/** First server message for one field, e.g. fieldErrors.username -> "That username is already taken." */
function firstFieldError(fieldErrors, fieldName) {
  const messages = fieldErrors[fieldName]
  return messages ? messages.join(' ') : null
}

function LogInForm({ onLoggedIn }) {
  const { logIn } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault() // stop the browser's full-page form submit
    setIsSubmitting(true)
    setFormError(null)
    try {
      await logIn({ username, password })
      onLoggedIn()
    } catch (requestError) {
      setFormError(requestError.message)
      setIsSubmitting(false) // only on failure; on success the dialog closes
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Stack spacing={2}>
        {formError && <Alert severity="error">{formError}</Alert>}
        <TextField
          label="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
          autoFocus
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
        <Button type="submit" variant="contained" disabled={isSubmitting || !username || !password}>
          {isSubmitting ? 'Logging in...' : 'Log in'}
        </Button>
      </Stack>
    </Box>
  )
}

function SignUpForm({ onSignedUp }) {
  const { register } = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  // Server messages per field, e.g. { email: ["An account with that email already exists."] }
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isFormFilledIn = username && email && password && passwordConfirmation

  async function handleSubmit(event) {
    event.preventDefault()
    setIsSubmitting(true)
    setFieldErrors({})
    setFormError(null)
    try {
      await register({ username, email, password, passwordConfirmation })
      onSignedUp()
    } catch (requestError) {
      if (requestError.status === 429) {
        setFormError('Too many sign-up attempts from this network. Please try again later.')
      } else if (Object.keys(requestError.fieldErrors).length > 0) {
        setFieldErrors(requestError.fieldErrors)
      } else {
        setFormError(requestError.message)
      }
      setIsSubmitting(false)
    }
  }

  const usernameError = firstFieldError(fieldErrors, 'username')
  const emailError = firstFieldError(fieldErrors, 'email')
  const passwordError = firstFieldError(fieldErrors, 'password')
  const passwordConfirmationError = firstFieldError(fieldErrors, 'password_confirmation')

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Stack spacing={2}>
        {formError && <Alert severity="error">{formError}</Alert>}
        <TextField
          label="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
          autoFocus
          error={Boolean(usernameError)}
          helperText={usernameError ?? 'Letters, numbers, and @ . + - _ only.'}
        />
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
          error={Boolean(emailError)}
          helperText={emailError}
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          required
          error={Boolean(passwordError)}
          helperText={passwordError ?? PASSWORD_HINT}
        />
        <TextField
          label="Confirm password"
          type="password"
          value={passwordConfirmation}
          onChange={(event) => setPasswordConfirmation(event.target.value)}
          autoComplete="new-password"
          required
          error={Boolean(passwordConfirmationError)}
          helperText={passwordConfirmationError}
        />
        <Button type="submit" variant="contained" disabled={isSubmitting || !isFormFilledIn}>
          {isSubmitting ? 'Creating account...' : 'Sign up'}
        </Button>
      </Stack>
    </Box>
  )
}

/**
 * The one Log in / Sign up dialog, opened from anywhere with openAccountDialog().
 * Closing it unmounts the forms, so they start empty next time.
 */
export default function AccountDialog({ isOpen, selectedTab, onTabChange, onClose }) {
  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="xs"
      // The paper is the element with role="dialog"; screen readers announce this name
      slotProps={{ paper: { 'aria-label': 'Log in or sign up' } }}
    >
      <Tabs value={selectedTab} onChange={(_event, newTab) => onTabChange(newTab)} variant="fullWidth">
        <Tab label="Log in" value="login" />
        <Tab label="Sign up" value="signup" />
      </Tabs>
      <DialogContent>
        {selectedTab === 'signup' ? <SignUpForm onSignedUp={onClose} /> : <LogInForm onLoggedIn={onClose} />}
      </DialogContent>
    </Dialog>
  )
}

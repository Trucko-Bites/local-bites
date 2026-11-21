// Login and sign-up using Django's session cookie (same origin as the API).
import { apiRequest } from './apiRequest.js'

/** Makes sure the csrftoken cookie exists before any POST. */
export async function ensureCsrfCookie() {
  await apiRequest('/api/auth/csrf/')
}

/** Returns { username, is_staff } when logged in, or null when logged out. */
export async function fetchCurrentUser() {
  try {
    return await apiRequest('/api/auth/me/')
  } catch (requestError) {
    if (requestError.status === 403) return null // simply not logged in
    throw requestError
  }
}

export async function logIn({ username, password }) {
  await ensureCsrfCookie()
  return apiRequest('/api/auth/login/', { method: 'POST', body: { username, password } })
}

/** Creates a customer account; the server logs it in and returns { username, is_staff }. */
export async function register({ username, email, password, passwordConfirmation }) {
  await ensureCsrfCookie()
  return apiRequest('/api/auth/register/', {
    method: 'POST',
    body: { username, email, password, password_confirmation: passwordConfirmation },
  })
}

export async function logOut() {
  await apiRequest('/api/auth/logout/', { method: 'POST' })
}

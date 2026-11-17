// Shared fetch helper for calls that change data (POST) or need the login session.

/** Reads Django's csrftoken cookie (set by GET /api/auth/csrf/). */
function readCsrfTokenFromCookie() {
  const csrfCookie = document.cookie
    .split('; ')
    .find((cookieText) => cookieText.startsWith('csrftoken='))
  return csrfCookie ? decodeURIComponent(csrfCookie.split('=')[1]) : ''
}

/** Turns a DRF error response into one readable sentence. */
async function describeErrorResponse(response) {
  try {
    const errorBody = await response.json()
    if (errorBody.detail) return errorBody.detail
    // Field errors look like {"open_until": ["Closing time must be in the future."]}
    return Object.values(errorBody).flat().join(' ')
  } catch {
    return `Request failed with status ${response.status}`
  }
}

/**
 * Sends a request with the session cookie and CSRF header attached.
 * Throws an Error with the server's message when the response isn't OK.
 * Returns parsed JSON, or null for empty responses (like 204 No Content).
 */
export async function apiRequest(url, { method = 'GET', body } = {}) {
  const response = await fetch(url, {
    method,
    credentials: 'same-origin', // send the session cookie
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': readCsrfTokenFromCookie(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    const requestError = new Error(await describeErrorResponse(response))
    requestError.status = response.status
    throw requestError
  }
  if (response.status === 204) return null
  return response.json()
}

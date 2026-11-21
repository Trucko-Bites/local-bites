// Shared fetch helper for calls that change data (POST) or need the login session.

/** Reads Django's csrftoken cookie (set by GET /api/auth/csrf/). */
function readCsrfTokenFromCookie() {
  const csrfCookie = document.cookie
    .split('; ')
    .find((cookieText) => cookieText.startsWith('csrftoken='))
  return csrfCookie ? decodeURIComponent(csrfCookie.split('=')[1]) : ''
}

/** Reads a DRF error body, or null when the response has no JSON body. */
async function readErrorBody(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

/** Turns a DRF error body into one readable sentence. */
function describeErrorBody(errorBody, responseStatus) {
  if (!errorBody) return `Request failed with status ${responseStatus}`
  if (errorBody.detail) return errorBody.detail
  // Field errors look like {"open_until": ["Closing time must be in the future."]}
  return Object.values(errorBody).flat().join(' ')
}

/**
 * Sends a request with the session cookie and CSRF header attached.
 * Throws an Error with the server's message when the response isn't OK.
 * The Error also carries .status and .fieldErrors (DRF's per-field messages,
 * e.g. {"username": ["That username is already taken."]}) so forms can show
 * each message under its own input.
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
    const errorBody = await readErrorBody(response)
    const requestError = new Error(describeErrorBody(errorBody, response.status))
    requestError.status = response.status
    // Only field errors are per-field; {"detail": "..."} is a whole-form message
    requestError.fieldErrors = errorBody && !errorBody.detail ? errorBody : {}
    throw requestError
  }
  if (response.status === 204) return null
  return response.json()
}

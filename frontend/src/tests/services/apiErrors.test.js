import { describe, it, expect, vi, beforeEach } from 'vitest'
import { handleApiError, getApiErrorCode, getApiErrorMessage, ERROR_TYPES } from '../../services/api'

// Every API error body is {"error": "<snake_case_code>", "message": "<human sentence>"}.
const apiError = (status, data) => ({ response: { status, data } })

describe('API error envelope', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('reads the code from `error` and the sentence from `message`', () => {
    const err = apiError(404, { error: 'project_not_found', message: 'Project not found' })
    expect(getApiErrorCode(err)).toBe('project_not_found')
    expect(getApiErrorMessage(err, 'fallback')).toBe('Project not found')

    const info = handleApiError(err)
    expect(info).toMatchObject({ code: 'project_not_found', message: 'Project not found', statusCode: 404 })
  })

  it('never shows the machine code as the message', () => {
    const info = handleApiError(apiError(400, { error: 'missing_fields' }))
    expect(info.message).toBe('Invalid request data')
    expect(info.code).toBe('missing_fields')
    expect(getApiErrorMessage(apiError(400, { error: 'missing_fields' }), 'Try again')).toBe('Try again')
  })

  it('treats invalid_credentials as a validation error, not an expired session', () => {
    const info = handleApiError(apiError(401, { error: 'invalid_credentials', message: 'Invalid credentials' }))
    expect(info.type).toBe(ERROR_TYPES.VALIDATION)
    expect(info.message).toBe('Invalid credentials')

    const expired = handleApiError(apiError(401, { error: 'token_expired', message: 'Token has expired' }))
    expect(expired.type).toBe(ERROR_TYPES.AUTH)
  })

  it('shows the server sentence for errors the user can act on, and a fixed one for the rest', () => {
    const wrongPassword = handleApiError(apiError(401, { error: 'invalid_credentials', message: 'Invalid credentials' }))
    expect(wrongPassword.userMessage).toBe('Invalid credentials')   // was "Please check your input and try again."

    const taken = handleApiError(apiError(409, { error: 'email_exists', message: 'Email already registered' }))
    expect(taken.userMessage).toBe('Email already registered')

    const limited = handleApiError(apiError(429, { error: 'rate_limit_exceeded', message: 'Too many requests. Please slow down.' }))
    expect(limited.userMessage).toBe('Too many requests. Please slow down.')

    const notFound = handleApiError(apiError(404, { error: 'project_not_found', message: 'Project not found' }))
    expect(notFound.userMessage).toBe('Project not found')

    // never expose a server error's text, and keep the session-expired wording for a stale token
    expect(handleApiError(apiError(500, { error: 'internal_error', message: 'db password leaked' })).userMessage)
      .toBe('Server error occurred. Please try again later.')
    expect(handleApiError(apiError(401, { error: 'token_expired', message: 'Token has expired' })).userMessage)
      .toBe('Your session has expired. Please log in again.')
    expect(handleApiError({ request: {} }).userMessage).toMatch(/Network connection failed/)
  })

  it('falls back when there is no response body', () => {
    expect(getApiErrorCode({ message: 'Network Error' })).toBeNull()
    expect(getApiErrorMessage({ message: 'Network Error' }, 'Offline')).toBe('Offline')
    expect(handleApiError({ request: {} }).type).toBe(ERROR_TYPES.NETWORK)
  })

  it('maps 429 to a rate-limit error with the server message', () => {
    const info = handleApiError(apiError(429, {
      error: 'rate_limit_exceeded', message: 'Too many requests.', retry_after: '30 per 1 minute',
    }))
    expect(info).toMatchObject({ type: ERROR_TYPES.RATE_LIMIT, code: 'rate_limit_exceeded', message: 'Too many requests.' })
  })
})

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { DISCORD_SIGN_IN_URL, rememberDestination, takeDestination } from './sso.js'
import { API_URL } from './http.js'

describe('DISCORD_SIGN_IN_URL', () => {
  it('points at the API rather than at Discord', () => {
    /*
     * The SPA never talks to Discord. It sends the browser to our own endpoint,
     * which mints the state and the PKCE challenge and redirects on — so the
     * client id and the scopes are not in the bundle, and neither is anything
     * that would have to change when they do.
     */
    expect(DISCORD_SIGN_IN_URL).toBe(`${API_URL}/auth/discord/authorize`)
  })

  it('carries no secret', () => {
    expect(DISCORD_SIGN_IN_URL).not.toMatch(/secret|client_id|token/i)
  })
})

describe('the destination across the round trip', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('brings back the page the guard interrupted', () => {
    rememberDestination('/library?q=owlbear')

    expect(takeDestination()).toBe('/library?q=owlbear')
  })

  it('falls back to the home page when nothing was stashed', () => {
    expect(takeDestination()).toBe('/')
  })

  it('refuses a destination pointing off this app', () => {
    /*
     * It came from a query string, so it came from whoever wrote the link — and
     * a sign-in that redirects wherever it is told deposits a freshly signed-in,
     * trusting visitor on somebody else's page.
     */
    rememberDestination('//evil.example')

    expect(takeDestination()).toBe('/')
  })

  it('refuses one that was written into storage directly', () => {
    // Stored values are not more trustworthy than query values — they *are* the
    // query values, one page load later.
    sessionStorage.setItem('ttrpg.sso.destination', 'https://evil.example')

    expect(takeDestination()).toBe('/')
  })

  it('is spent once, so a later sign-in does not inherit it', () => {
    rememberDestination('/library')

    expect(takeDestination()).toBe('/library')
    expect(takeDestination()).toBe('/')
  })

  it('survives storage being unavailable rather than blocking the sign-in', () => {
    /*
     * Safari in private mode and any page with storage disabled throw on
     * access. Losing the destination is a dull failure — you land on the home
     * page — and it must not be the reason a sign-in cannot start.
     */
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })

    expect(() => rememberDestination('/library')).not.toThrow()
    expect(takeDestination()).toBe('/')
  })
})

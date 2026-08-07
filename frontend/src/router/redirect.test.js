import { describe, it, expect } from 'vitest'
import { safeRedirect } from './redirect.js'

/*
 * The destination comes from a query string, so it comes from whoever wrote the
 * link. Everything here is one question: can a crafted ?redirect= take a
 * freshly signed-in user somewhere that is not this app.
 */
describe('safeRedirect', () => {
  it('keeps a path on this app', () => {
    expect(safeRedirect('/campaigns/7')).toBe('/campaigns/7')
    expect(safeRedirect('/library?q=owlbear#stats')).toBe('/library?q=owlbear#stats')
  })

  it('refuses a protocol-relative URL, which is another origin wearing a path', () => {
    // The attack that looks like a path: the browser reads //evil.example as a
    // host, not a directory.
    expect(safeRedirect('//evil.example/login')).toBe('/')
    expect(safeRedirect('/\\evil.example')).toBe('/')
  })

  it('refuses an absolute URL', () => {
    expect(safeRedirect('https://evil.example')).toBe('/')
    expect(safeRedirect('javascript:alert(1)')).toBe('/')
  })

  it('falls back when there is nothing usable', () => {
    expect(safeRedirect(undefined)).toBe('/')
    expect(safeRedirect('')).toBe('/')
    // vue-router hands over an array when a query key repeats.
    expect(safeRedirect(['/a', '/b'])).toBe('/')
  })

  it('takes a caller-supplied fallback', () => {
    expect(safeRedirect('https://evil.example', '/home')).toBe('/home')
  })
})

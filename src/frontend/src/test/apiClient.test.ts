import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiRequest, apiUrl, withQuery } from '../api/client'

describe('shared same-origin API client', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('builds same-origin API URLs without VITE_API_URL', () => {
    expect(apiUrl('/ptc-assistant/ask')).toBe('/api/v1/ptc-assistant/ask')
    expect(apiUrl('/api/v1/patients')).toBe('/api/v1/patients')
    expect(apiUrl('ptc-readiness')).toBe('/api/v1/ptc-readiness')
  })

  it('encodes query parameters and omits empty values', () => {
    expect(withQuery('/ptc-reports/case/C1/json', {
      gene: 'BRAF V600E',
      question: undefined,
      limit: 100,
      active: false,
    })).toBe('/ptc-reports/case/C1/json?gene=BRAF+V600E&limit=100&active=false')
  })

  it('sends authorization and JSON body through one request path', async () => {
    localStorage.setItem('auth_token', 'test-token')
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))

    await expect(apiRequest<{ ok: boolean }>('/example', {
      method: 'POST',
      body: JSON.stringify({ value: 1 }),
    })).resolves.toEqual({ ok: true })

    expect(fetch).toHaveBeenCalledWith('/api/v1/example', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({
        Authorization: 'Bearer test-token',
        'Content-Type': 'application/json',
      }),
    }))
  })

  it('returns undefined for 204 and preserves backend error details', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(apiRequest('/empty')).resolves.toBeUndefined()

    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Patient not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    }))
    await expect(apiRequest('/missing')).rejects.toThrow('Patient not found')
  })

  it('reports HTML routing failures without exposing a JSON parser exception', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('<!DOCTYPE html><html><body>SPA fallback</body></html>', {
      status: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    }))

    await expect(apiRequest('/ptc-visualization/cases/latest')).rejects.toThrow(
      'API returned non-JSON content (/api/v1/ptc-visualization/cases/latest): text/html',
    )
  })
})

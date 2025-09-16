import { renderHook } from '@testing-library/react'
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import { ToastProvider } from '@/components/providers/ToastProvider'
import { ReactNode } from 'react'

// Mutable mock for useAuth
const useAuthMock = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}))

// Wrapper component for testing
function TestWrapper({ children }: { children: ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>
}

// Mock fetch
const mockFetch = vi.fn()
const originalFetch = global.fetch

describe('useApi', () => {
  const originalEnv = process.env

  beforeEach(() => {
    global.fetch = mockFetch
    vi.clearAllMocks()
    process.env = { ...originalEnv, NEXT_PUBLIC_API_BASE_URL: 'http://localhost:8000' }
  })

  afterEach(() => {
    process.env = originalEnv
    global.fetch = originalFetch
  })

  it('makes API calls without token when not authenticated', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ test: 'data' }),
    })

    useAuthMock.mockReturnValue({ token: null, logout: vi.fn() })
    const { useApi } = await import('@/lib/api')
    const { result } = renderHook(() => useApi(), { wrapper: TestWrapper })
    const api = result.current

    await api('/test-endpoint')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/test-endpoint',
      {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      }
    )
  })

  it('adds Authorization header when token is present', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })

    useAuthMock.mockReturnValue({ token: 'test-token', logout: vi.fn() })
    const { useApi } = await import('@/lib/api')
    const { result } = renderHook(() => useApi(), { wrapper: TestWrapper })
    const api = result.current
    await api('/test-endpoint')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/test-endpoint',
      {
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        cache: 'no-store',
      }
    )
  })

  it('handles FormData correctly', async () => {
    const formData = new FormData()
    formData.append('test', 'value')

    useAuthMock.mockReturnValue({ token: null, logout: vi.fn() })
    const { useApi } = await import('@/lib/api')
    const { result } = renderHook(() => useApi(), { wrapper: TestWrapper })
    const api = result.current

    await api('/upload', { method: 'POST', body: formData })

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/upload',
      {
        method: 'POST',
        body: formData,
        headers: {},
        cache: 'no-store',
      }
    )
  })

  it('merges custom headers correctly', async () => {
    useAuthMock.mockReturnValue({ token: 'test-token', logout: vi.fn() })
    const { useApi } = await import('@/lib/api')
    const { result } = renderHook(() => useApi(), { wrapper: TestWrapper })
    const api = result.current

    await api('/test-endpoint', {
      headers: { 'Custom-Header': 'custom-value' },
    })

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/test-endpoint',
      {
        headers: {
          'Content-Type': 'application/json',
          'Custom-Header': 'custom-value',
          Authorization: 'Bearer test-token',
        },
        cache: 'no-store',
      }
    )
  })
})
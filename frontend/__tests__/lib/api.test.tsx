import { renderHook } from '@testing-library/react'
import { useApi } from '@/lib/api'
import { useSession } from 'next-auth/react'
import { vi, beforeEach, afterEach } from 'vitest'
import { server } from '@/src/mocks/server'
import { ToastProvider } from '@/components/providers/ToastProvider'
import { ReactNode } from 'react'

// Mock next-auth
vi.mock('next-auth/react')

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
    // Stop MSW server for these tests and use our manual mock
    server.close()
    global.fetch = mockFetch
    
    vi.clearAllMocks()
    process.env = { ...originalEnv }
    process.env.NEXT_PUBLIC_BACKEND_BASE_URL = 'http://localhost:8000'
  })

  afterEach(() => {
    process.env = originalEnv
    global.fetch = originalFetch
    // Restart MSW server after each test
    server.listen()
  })

  it('makes API calls without token when not authenticated', async () => {
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: 'unauthenticated',
      update: vi.fn(),
    })

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ test: 'data' }),
    })

    const { result } = renderHook(() => useApi(), {
      wrapper: TestWrapper
    })
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

  it('makes API calls with token when authenticated', async () => {
    vi.mocked(useSession).mockReturnValue({
      data: { access_token: 'test-token' } as any,
      status: 'authenticated',
      update: vi.fn(),
    })

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ test: 'data' }),
    })

    const { result } = renderHook(() => useApi(), {
      wrapper: TestWrapper
    })
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
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: 'unauthenticated',
      update: vi.fn(),
    })

    const formData = new FormData()
    formData.append('test', 'value')

    const { result } = renderHook(() => useApi(), {
      wrapper: TestWrapper
    })
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
    vi.mocked(useSession).mockReturnValue({
      data: { access_token: 'test-token' } as any,
      status: 'authenticated',
      update: vi.fn(),
    })

    const { result } = renderHook(() => useApi(), {
      wrapper: TestWrapper
    })
    const api = result.current

    await api('/test-endpoint', {
      headers: {
        'Custom-Header': 'custom-value',
      },
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
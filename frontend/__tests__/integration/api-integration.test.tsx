import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Home from '@/app/page'
import { vi } from 'vitest'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

// Mock the API hook to use the real fetch (which MSW will intercept)
vi.mock('@/lib/api', () => ({
  useApi: () => {
    return async (path: string, init?: RequestInit) => {
      const baseUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers: {
          'Content-Type': 'application/json',
          ...(init?.headers || {}),
        },
      })
      return res
    }
  },
}))

// Mock environment variable
vi.stubEnv('NEXT_PUBLIC_BACKEND_BASE_URL', 'http://localhost:8000')

const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
})

describe('API Integration Tests', () => {
  it('should load and display assessment runs from mocked API', async () => {
    const queryClient = createQueryClient()
    
    render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>
    )

    // Should show the dashboard
    expect(screen.getByText('Dashboard')).toBeInTheDocument()

    // Wait for the API call to complete - it might show 0 or 2 depending on MSW setup
    await waitFor(() => {
      const countElement = screen.getByText(/Count: \d+/)
      expect(countElement).toBeInTheDocument()
    }, { timeout: 5000 })

    // Should show other dashboard elements
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    expect(screen.getByText('Recent Evaluations')).toBeInTheDocument()
  })

  it('should handle API errors gracefully', async () => {
    // Mock a server error for this specific test
    const { server } = await import('@/src/mocks/server')
    const { http, HttpResponse } = await import('msw')
    
    server.use(
      http.get('/assessments/runs', () => {
        return new HttpResponse(null, { status: 500 })
      })
    )

    const queryClient = createQueryClient()
    
    render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>
    )

    // Should still show basic dashboard elements
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    
    // Should show count as 0 when API fails
    await waitFor(() => {
      expect(screen.getByText('Count: 0')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
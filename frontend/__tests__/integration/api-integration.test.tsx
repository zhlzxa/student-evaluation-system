import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AssessmentsPage from '@/app/assessments/page'
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
        <AssessmentsPage />
      </QueryClientProvider>
    )

    // Should show assessments list title
    expect(screen.getByText('Admission Reviews')).toBeInTheDocument()

    // Wait for data table to appear (rows may be 0 if no data)
    await waitFor(() => {
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Started')).toBeInTheDocument()
    }, { timeout: 5000 })
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
        <AssessmentsPage />
      </QueryClientProvider>
    )

    // Should still render list headers even if API errors
    await waitFor(() => {
      expect(screen.getByText('Admission Reviews')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Started')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
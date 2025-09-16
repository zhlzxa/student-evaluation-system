import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from '@/components/providers/ToastProvider'
import AssessmentsPage from '@/app/assessments/page'
import { vi, describe, it, expect, beforeAll, afterAll } from 'vitest'

// Reduce file descriptor usage by mocking heavy MUI icons
vi.mock('@mui/icons-material', () => ({
  Assessment: () => null,
  Visibility: () => null,
  Schedule: () => null,
  CheckCircle: () => null,
  HourglassEmpty: () => null,
  Cancel: () => null,
  Delete: () => null,
  Add: () => null,
  MoreVert: () => null,
}))

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

// Mock auth for page usage
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ token: null, logout: vi.fn(), isAuthenticated: true, loading: false, user: null }),
}))

// Use MSW server from setup
const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
})

// Ensure env base URL exists for tests
beforeAll(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://localhost:8000')
})

afterAll(() => {
  vi.unstubAllEnvs()
})

describe('API Integration Tests', () => {
  it('should load and display assessment runs from mocked API', async () => {
    const queryClient = createQueryClient()
    
    render(
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <AssessmentsPage />
        </QueryClientProvider>
      </ToastProvider>
    )

    expect(screen.getByText('Admission Reviews')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Started')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('should handle API errors gracefully', async () => {
    const { server } = await import('@/src/mocks/server')
    const { http, HttpResponse } = await import('msw')
    
    server.use(
      http.get('http://localhost:8000/assessments/runs', () => new HttpResponse(null, { status: 500 }))
    )

    const queryClient = createQueryClient()
    
    render(
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <AssessmentsPage />
        </QueryClientProvider>
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Admission Reviews')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Started')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
import '@testing-library/jest-dom'
import { beforeAll, afterEach, afterAll, beforeEach, vi } from 'vitest'
import { server } from './src/mocks/server'

// Start MSW server before all tests
beforeAll(() => {
  server.listen()
})

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers()
})

// Clean up after all tests
afterAll(() => {
  server.close()
})

beforeEach(() => {
  // Mock next/navigation
  vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    })),
    useSearchParams: vi.fn(() => ({
      get: vi.fn(),
    })),
    usePathname: vi.fn(() => '/'),
  }))

  // Mock next-auth
  vi.mock('next-auth/react', () => ({
    useSession: vi.fn(() => ({
      data: null,
      status: 'loading',
    })),
    SessionProvider: ({ children }: { children: React.ReactNode }) => children,
  }))

  // Clear all mocks before each test
  vi.clearAllMocks()
})
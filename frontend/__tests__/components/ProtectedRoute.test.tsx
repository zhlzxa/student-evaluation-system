import { render, screen } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Create a mutable mock for useAuth
const useAuthMock = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}))

import ProtectedRoute from '@/components/ProtectedRoute'

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders children when authenticated', () => {
    useAuthMock.mockReturnValue({ isAuthenticated: true, loading: false })

    render(
      <ProtectedRoute>
        <div data-testid="content">ok</div>
      </ProtectedRoute>
    )

    expect(screen.getByTestId('content')).toBeInTheDocument()
  })

  it('shows loader when loading', () => {
    useAuthMock.mockReturnValue({ isAuthenticated: false, loading: true })

    render(
      <ProtectedRoute>
        <div>should not render</div>
      </ProtectedRoute>
    )

    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('redirects to login when unauthenticated', () => {
    useAuthMock.mockReturnValue({ isAuthenticated: false, loading: false })

    render(
      <ProtectedRoute>
        <div>should not render</div>
      </ProtectedRoute>
    )

    expect(mockPush).toHaveBeenCalledWith('/login?message=session_expired')
  })
})



import { render, screen } from '@testing-library/react'
import { AppShell } from '@/components/layout/AppShell'
import { usePathname, useRouter } from 'next/navigation'
import { vi, beforeEach, describe, it, expect } from 'vitest'

// Mock auth context used by AppShell
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { email: 'user@test.com', full_name: 'Test User' },
    token: 'token',
    login: vi.fn(),
    logout: vi.fn(),
    loading: false,
    isAuthenticated: true,
  }),
}))

const mockPush = vi.fn()
const mockPathname = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => mockPathname(),
}))

describe('AppShell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPathname.mockReturnValue('/')
  })

  it('renders the app title', () => {
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    expect(screen.getByText('Student Admission Review System')).toBeInTheDocument()
  })

  it('renders children content', () => {
    render(
      <AppShell>
        <div data-testid="test-content">Test Content</div>
      </AppShell>
    )

    expect(screen.getByTestId('test-content')).toBeInTheDocument()
  })

  it('shows navigation permanently', async () => {
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    // Navigation items should be visible without clicking any menu
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Programme Criteria')).toBeInTheDocument()
  })

  it('navigates when navigation items are clicked', async () => {
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    screen.getByText('Home').click()

    expect(mockPush).toHaveBeenCalledWith('/assessments')
  })

  it('highlights current path in navigation', () => {
    mockPathname.mockReturnValue('/rules')
    
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    // The Programme Criteria item should be selected
    const rulesItem = screen.getByText('Programme Criteria').closest('[role="button"]')
    expect(rulesItem).toHaveClass('Mui-selected')
  })
})
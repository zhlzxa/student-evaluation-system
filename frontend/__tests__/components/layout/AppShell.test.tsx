import { render, screen } from '@testing-library/react'
import { AppShell } from '@/components/layout/AppShell'
import { usePathname, useRouter } from 'next/navigation'
import { vi } from 'vitest'

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

    expect(screen.getByText('Student Evaluation System')).toBeInTheDocument()
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
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('New Assessment')).toBeInTheDocument()
    expect(screen.getByText('Evaluation History')).toBeInTheDocument()
    expect(screen.getByText('Rules')).toBeInTheDocument()
  })

  it('navigates when navigation items are clicked', async () => {
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    screen.getByText('New Assessment').click()

    expect(mockPush).toHaveBeenCalledWith('/assessments/new')
  })

  it('highlights current path in navigation', () => {
    mockPathname.mockReturnValue('/rules')
    
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    // The Rules item should be selected
    const rulesItem = screen.getByText('Rules').closest('[role="button"]')
    expect(rulesItem).toHaveClass('Mui-selected')
  })
})
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

  it('opens drawer when menu button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    const menuButton = screen.getByTestId('MenuIcon').closest('button')!
    await user.click(menuButton)

    // Check if navigation items are visible
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('New Assessment')).toBeInTheDocument()
    expect(screen.getByText('Evaluation History')).toBeInTheDocument()
    expect(screen.getByText('Rules')).toBeInTheDocument()
  })

  it('navigates when navigation items are clicked', async () => {
    const user = userEvent.setup()
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    // Open drawer
    const menuButton = screen.getByTestId('MenuIcon').closest('button')!
    await user.click(menuButton)

    // Click on New Assessment
    const newAssessmentButton = screen.getByText('New Assessment')
    await user.click(newAssessmentButton)

    expect(mockPush).toHaveBeenCalledWith('/assessments/new')
  })

  it('highlights current path in navigation', () => {
    mockPathname.mockReturnValue('/rules')
    
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    )

    // Open drawer
    const menuButton = screen.getByTestId('MenuIcon').closest('button')!
    fireEvent.click(menuButton)

    // The Rules item should be selected
    const rulesItem = screen.getByText('Rules').closest('[role="button"]')
    expect(rulesItem).toHaveClass('Mui-selected')
  })
})
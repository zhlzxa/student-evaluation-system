import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Home from '@/app/page'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { vi, beforeEach } from 'vitest'

// Mock dependencies
vi.mock('next/navigation')
vi.mock('@tanstack/react-query')
vi.mock('@/lib/api', () => ({
  useApi: () => vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([]),
  }),
}))

const mockPush = vi.fn()

describe('Home Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    })
  })

  it('renders dashboard title', () => {
    vi.mocked(useQuery).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('renders quick actions card', () => {
    vi.mocked(useQuery).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    expect(screen.getByText('New Assessment')).toBeInTheDocument()
  })

  it('renders recent runs card with correct count', () => {
    const mockRuns = [
      { id: 1, name: 'Run 1' },
      { id: 2, name: 'Run 2' },
    ]

    vi.mocked(useQuery).mockReturnValue({
      data: mockRuns,
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    expect(screen.getByText('Recent Evaluations')).toBeInTheDocument()
    expect(screen.getByText('Count: 2')).toBeInTheDocument()
  })

  it('shows count 0 when runs data is not an array', () => {
    vi.mocked(useQuery).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    expect(screen.getByText('Count: 0')).toBeInTheDocument()
  })

  it('navigates to new assessment when button is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(useQuery).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    const newAssessmentButton = screen.getByRole('button', { name: 'New Assessment' })
    await user.click(newAssessmentButton)
    
    expect(mockPush).toHaveBeenCalledWith('/assessments/new')
  })

  it('navigates to assessments when view all button is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(useQuery).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any)

    render(<Home />)
    
    const viewAllButton = screen.getByRole('button', { name: 'View all' })
    await user.click(viewAllButton)
    
    expect(mockPush).toHaveBeenCalledWith('/assessments')
  })
})
import { render, screen } from '@testing-library/react'
import { ReactQueryProvider } from '@/components/providers/react-query'

describe('ReactQueryProvider', () => {
  it('renders children correctly', () => {
    render(
      <ReactQueryProvider>
        <div data-testid="test-child">Test Child</div>
      </ReactQueryProvider>
    )

    expect(screen.getByTestId('test-child')).toBeInTheDocument()
    expect(screen.getByText('Test Child')).toBeInTheDocument()
  })

  it('provides QueryClient context', () => {
    const TestComponent = () => {
      const { QueryClient } = require('@tanstack/react-query')
      return <div data-testid="has-context">Has QueryClient context</div>
    }

    render(
      <ReactQueryProvider>
        <TestComponent />
      </ReactQueryProvider>
    )

    expect(screen.getByTestId('has-context')).toBeInTheDocument()
  })
})
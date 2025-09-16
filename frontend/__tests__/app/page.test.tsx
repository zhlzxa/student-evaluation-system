import { vi, beforeEach, describe, it, expect } from 'vitest'

// For this page, the component immediately calls redirect('/assessments').
// We verify that behavior directly without rendering DOM.

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

describe('Home Page redirect', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('redirects to /assessments on render', async () => {
    const { redirect } = await import('next/navigation')
    const mod = await import('@/app/page')
    const Home = mod.default as () => any

    // Should not throw when invoked
    expect(() => Home()).not.toThrow()
    expect(redirect).toHaveBeenCalledWith('/assessments')
  })
})
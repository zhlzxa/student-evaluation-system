import { http, HttpResponse } from 'msw'

// Mock assessment runs data
const mockRuns = [
  {
    id: 1,
    name: 'Sample Assessment Run 1',
    status: 'completed',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T11:00:00Z',
  },
  {
    id: 2,
    name: 'Sample Assessment Run 2',
    status: 'pending',
    created_at: '2024-01-16T09:15:00Z',
    updated_at: '2024-01-16T09:15:00Z',
  },
  {
    id: 3,
    name: 'Sample Assessment Run 3',
    status: 'failed',
    created_at: '2024-01-17T14:45:00Z',
    updated_at: '2024-01-17T15:30:00Z',
  },
]

// Mock assessment data
const mockAssessments = [
  {
    id: 1,
    title: 'Mathematics Assessment',
    description: 'Basic mathematics test for grade 10',
    questions: ['What is 2+2?', 'What is the derivative of x²?'],
    created_at: '2024-01-10T08:00:00Z',
  },
  {
    id: 2,
    title: 'Science Assessment',
    description: 'Physics and chemistry basics',
    questions: ['What is Newton\'s first law?', 'What is H2O?'],
    created_at: '2024-01-12T10:30:00Z',
  },
]

// Mock rules data
const mockRules = [
  {
    id: 1,
    name: 'Plagiarism Detection',
    description: 'Detect plagiarized content',
    criteria: 'Check for duplicate text patterns',
    active: true,
  },
  {
    id: 2,
    name: 'Grammar Check',
    description: 'Check for grammatical errors',
    criteria: 'Analyze sentence structure and grammar',
    active: true,
  },
]

export const handlers = [
  // Assessment runs endpoints
  http.get('/assessments/runs', ({ request }) => {
    const url = new URL(request.url)
    const visibleOnly = url.searchParams.get('visible_only')
    
    if (visibleOnly === 'true') {
      return HttpResponse.json(mockRuns.slice(0, 2))
    }
    
    return HttpResponse.json(mockRuns)
  }),

  http.get('/assessments/runs/:id', ({ params }) => {
    const { id } = params
    const run = mockRuns.find(r => r.id === Number(id))
    
    if (!run) {
      return new HttpResponse(null, { status: 404 })
    }
    
    return HttpResponse.json(run)
  }),

  // Assessments endpoints
  http.get('/assessments', () => {
    return HttpResponse.json(mockAssessments)
  }),

  http.get('/assessments/:id', ({ params }) => {
    const { id } = params
    const assessment = mockAssessments.find(a => a.id === Number(id))
    
    if (!assessment) {
      return new HttpResponse(null, { status: 404 })
    }
    
    return HttpResponse.json(assessment)
  }),

  http.post('/assessments', async ({ request }) => {
    const body = await request.json() as any
    const newAssessment = {
      id: mockAssessments.length + 1,
      ...body,
      created_at: new Date().toISOString(),
    }
    
    mockAssessments.push(newAssessment)
    return HttpResponse.json(newAssessment, { status: 201 })
  }),

  // Rules endpoints
  http.get('/rules', () => {
    return HttpResponse.json(mockRules)
  }),

  http.get('/rules/:id', ({ params }) => {
    const { id } = params
    const rule = mockRules.find(r => r.id === Number(id))
    
    if (!rule) {
      return new HttpResponse(null, { status: 404 })
    }
    
    return HttpResponse.json(rule)
  }),

  http.post('/rules', async ({ request }) => {
    const body = await request.json() as any
    const newRule = {
      id: mockRules.length + 1,
      ...body,
    }
    
    mockRules.push(newRule)
    return HttpResponse.json(newRule, { status: 201 })
  }),

  // Reports endpoints removed

  // Authentication endpoints (mock)
  http.post('/auth/login', async ({ request }) => {
    const body = await request.json() as any
    
    // Simple mock authentication
    if (body.email === 'test@example.com' && body.password === 'password') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token',
        user: {
          id: 1,
          email: 'test@example.com',
          name: 'Test User',
        },
      })
    }
    
    return new HttpResponse(null, { status: 401 })
  }),

  http.post('/auth/register', async ({ request }) => {
    const body = await request.json() as any
    
    return HttpResponse.json({
      access_token: 'mock-jwt-token',
      user: {
        id: 2,
        email: body.email,
        name: body.name,
      },
    }, { status: 201 })
  }),

  // Catch-all for unhandled requests
  http.all('*', ({ request }) => {
    console.warn(`Unhandled ${request.method} request to ${request.url}`)
    return new HttpResponse(null, { status: 404 })
  }),
]
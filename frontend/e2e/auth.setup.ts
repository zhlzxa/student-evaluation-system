import { chromium, FullConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'

async function tryRegisterAndLogin(apiBase: string, email: string, password: string): Promise<string | null> {
  try {
    const registerRes = await fetch(`${apiBase}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        full_name: 'E2E User',
        invite_code: 'UCLIXN',
      }),
    })

    // If already exists or created, proceed to login
    if (!registerRes.ok && registerRes.status !== 400) {
      // Non-recoverable
      throw new Error(`Register failed: ${registerRes.status}`)
    }

    const loginRes = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!loginRes.ok) {
      throw new Error(`Login failed: ${loginRes.status}`)
    }

    const data = await loginRes.json().catch(() => null) as any
    const token = data?.access_token as string | undefined
    if (!token) return null
    return token
  } catch {
    return null
  }
}

function toBase64(obj: Record<string, any>): string {
  return Buffer.from(JSON.stringify(obj)).toString('base64')
}

function buildLocalToken(email: string): string {
  const header = { alg: 'none', typ: 'JWT' }
  const payload = {
    sub: email,
    user_id: 1,
    full_name: 'E2E User',
    exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24,
    is_active: true,
    is_superuser: false,
  }
  return `${toBase64(header)}.${toBase64(payload)}.`
}

export default async function globalSetup(config: FullConfig) {
  const storageDir = path.resolve(__dirname, '.auth')
  const storagePath = path.join(storageDir, 'storageState.json')
  if (!fs.existsSync(storageDir)) fs.mkdirSync(storageDir, { recursive: true })

  const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api'
  const baseURL = (config.projects[0]?.use as any)?.baseURL || 'http://localhost:3000'

  const email = `e2e_${Date.now()}@example.com`
  const password = 'E2e!2345'

  let token: string | null = null
  // Attempt real registration/login first (if backend available)
  token = await tryRegisterAndLogin(apiBase, email, password)
  if (!token) {
    // Fallback: generate local token compatible with AuthProvider.parseJWT
    token = buildLocalToken(email)
  }

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()
  // Navigate to origin so localStorage belongs to correct origin
  await page.goto(baseURL)
  await page.evaluate(([t]) => {
    localStorage.setItem('access_token', t as string)
  }, [token])
  // Go to an authenticated page to ensure client picks up auth
  await page.goto(baseURL + '/assessments')

  await context.storageState({ path: storagePath })
  await browser.close()
}




export type Role = 'CLERK' | 'MANAGER'

export type Session = {
  token: string
  role: Role
  displayName: string
  userId: string
}

export type Part = {
  code: string
  name: string
  onHand: number
  unitCost?: string
}

export type Requisition = {
  id: number
  partCode: string
  partName: string
  quantity: number
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  requestedBy: string
  unitCost?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly retryAfter: number | null

  constructor(message: string, status: number, retryAfter: number | null) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

const STORAGE_KEY = 'leme.session'

export function loadSession(): Session | null {
  const raw = sessionStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Session
    if (!parsed.token || !parsed.role || !parsed.displayName) return null
    return parsed
  } catch {
    return null
  }
}

export function saveSession(session: Session | null): void {
  if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  else sessionStorage.removeItem(STORAGE_KEY)
}

async function fail(response: Response): Promise<never> {
  let message = 'The counter could not complete that.'
  try {
    const body = (await response.json()) as { error?: string }
    if (body.error) message = body.error
  } catch {
    /* keep the fallback */
  }
  const retry = response.headers.get('Retry-After')
  const retryAfter = retry ? Number(retry) : null
  throw new ApiError(message, response.status, Number.isFinite(retryAfter) ? retryAfter : null)
}

async function send<T>(path: string, init: RequestInit, token?: string): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) await fail(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function signOn(userId: string, password: string): Promise<Session> {
  const body = await send<{ token: string; role: Role; displayName: string }>('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, password }),
  })
  return { ...body, userId }
}

export function signOff(token: string): Promise<void> {
  return send('/sessions', { method: 'DELETE' }, token)
}

export function listParts(token: string, query: string): Promise<{ synthetic: boolean; note: string; parts: Part[] }> {
  const q = query.trim()
  const path = q ? `/parts?q=${encodeURIComponent(q.slice(0, 40))}` : '/parts'
  return send(path, { method: 'GET' }, token)
}

export function listRequisitions(token: string): Promise<Requisition[]> {
  return send('/requisitions', { method: 'GET' }, token)
}

export function createRequisition(token: string, partCode: string, quantity: number): Promise<Requisition> {
  return send(
    '/requisitions',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ partCode, quantity }),
    },
    token,
  )
}

export function approveRequisition(token: string, id: number): Promise<Requisition> {
  return send(`/requisitions/${id}/approve`, { method: 'POST' }, token)
}

export function rejectRequisition(token: string, id: number): Promise<Requisition> {
  return send(`/requisitions/${id}/reject`, { method: 'POST' }, token)
}

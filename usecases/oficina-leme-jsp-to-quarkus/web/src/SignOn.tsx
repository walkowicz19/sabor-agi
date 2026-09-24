import { FormEvent, useState } from 'react'
import { LogIn } from 'lucide-react'
import { ApiError, signOn, type Session } from './api'

type SignOnProps = {
  onSignedOn: (session: Session) => void
}

export function SignOn({ onSignedOn }: SignOnProps) {
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onSignedOn(await signOn(userId.trim(), password))
    } catch (caught) {
      if (caught instanceof ApiError) {
        const wait =
          caught.status === 429 && caught.retryAfter
            ? ` Wait ${caught.retryAfter} seconds, then try again.`
            : ''
        setError(`${caught.message}.${wait}`)
      } else {
        setError('The counter did not answer. Start the desk API and try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="sign-on">
      <header className="brand">
        <h1>Oficina Leme</h1>
        <p>Parts counter</p>
      </header>
      <form className="sign-plate" onSubmit={submit}>
        <label>
          Counter id
          <input
            name="username"
            autoComplete="username"
            inputMode="numeric"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? (
          <p className="fault" role="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" className="plate action" disabled={busy}>
          <LogIn aria-hidden="true" />
          {busy ? 'Checking' : 'Sign on'}
        </button>
      </form>
    </main>
  )
}

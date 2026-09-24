import { useCallback, useState } from 'react'
import { loadSession, saveSession, type Session } from './api'
import { Desk } from './Desk'
import { SignOn } from './SignOn'

export function App() {
  const [session, setSession] = useState<Session | null>(() => loadSession())
  const signedOff = useCallback(() => {
    saveSession(null)
    setSession(null)
  }, [])

  if (!session) {
    return (
      <SignOn
        onSignedOn={(next) => {
          saveSession(next)
          setSession(next)
        }}
      />
    )
  }

  return <Desk session={session} onSignedOff={signedOff} />
}

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Lock, LogOut, Minus, Plus, Search } from 'lucide-react'
import {
  ApiError,
  approveRequisition,
  createRequisition,
  listParts,
  listRequisitions,
  rejectRequisition,
  signOff,
  type Part,
  type Requisition,
  type Session,
} from './api'
import { Dial } from './Dial'

type DeskProps = {
  session: Session
  onSignedOff: () => void
}

type Selection =
  | { kind: 'part'; code: string }
  | { kind: 'requisition'; id: number }

const PLATE: Record<Requisition['status'], string> = {
  PENDING: 'Pending',
  APPROVED: 'Approved',
  REJECTED: 'Refused',
}

function roleLabel(role: Session['role']): string {
  return role === 'MANAGER' ? 'Manager' : 'Clerk'
}

export function Desk({ session, onSignedOff }: DeskProps) {
  const [parts, setParts] = useState<Part[]>([])
  const [note, setNote] = useState('Synthetic fixture stock.')
  const [rows, setRows] = useState<Requisition[]>([])
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState<Part[] | null>(null)
  const [selection, setSelection] = useState<Selection>({ kind: 'part', code: '100331' })
  const [quantity, setQuantity] = useState(2)
  const [fault, setFault] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onHandOf = useMemo(() => {
    const map = new Map(parts.map((part) => [part.code, part]))
    return (code: string) => map.get(code)?.onHand ?? 0
  }, [parts])

  async function reload(token: string) {
    const [catalog, book] = await Promise.all([listParts(token, ''), listRequisitions(token)])
    setParts(catalog.parts)
    setNote(catalog.note)
    setRows(book)
    return { catalog: catalog.parts, book }
  }

  useEffect(() => {
    let cancelled = false
    reload(session.token).catch((caught) => {
      if (cancelled) return
      if (caught instanceof ApiError && caught.status === 401) onSignedOff()
      else setFault('The bins did not load.')
    })
    return () => {
      cancelled = true
    }
  }, [session.token, onSignedOff])

  const selectedPart = selection.kind === 'part' ? parts.find((part) => part.code === selection.code) : undefined
  const selectedRow = selection.kind === 'requisition' ? rows.find((row) => row.id === selection.id) : undefined

  const lead = selectedRow
    ? {
        code: selectedRow.partCode,
        name: selectedRow.partName,
        onHand: onHandOf(selectedRow.partCode),
        request: selectedRow.quantity,
        unitCost: selectedRow.unitCost,
      }
    : selectedPart
      ? {
          code: selectedPart.code,
          name: selectedPart.name,
          onHand: selectedPart.onHand,
          request: session.role === 'CLERK' ? quantity : null,
          unitCost: selectedPart.unitCost,
        }
      : null

  const queueParts = parts.filter((part) => part.code !== lead?.code)
  const queueRows = rows
  const showBook = rows.length > 0

  async function run(task: () => Promise<void>) {
    setBusy(true)
    setFault(null)
    try {
      await task()
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) onSignedOff()
      else if (caught instanceof ApiError) setFault(caught.message)
      else setFault('The counter did not answer.')
    } finally {
      setBusy(false)
    }
  }

  async function search(event: FormEvent) {
    event.preventDefault()
    await run(async () => {
      const catalog = await listParts(session.token, query)
      setMatches(catalog.parts)
    })
  }

  async function issue() {
    if (!selectedPart) return
    await run(async () => {
      const created = await createRequisition(session.token, selectedPart.code, quantity)
      await reload(session.token)
      setSelection({ kind: 'requisition', id: created.id })
      setMatches(null)
      setQuery('')
    })
  }

  async function approve() {
    if (!selectedRow) return
    await run(async () => {
      await approveRequisition(session.token, selectedRow.id)
      await reload(session.token)
    })
  }

  async function refuse() {
    if (!selectedRow) return
    await run(async () => {
      await rejectRequisition(session.token, selectedRow.id)
      await reload(session.token)
    })
  }

  async function leave() {
    try {
      await signOff(session.token)
    } catch {
      /* the local session still ends */
    }
    onSignedOff()
  }

  return (
    <main className="desk">
      <header className="brand-row">
        <div className="brand">
          <h1>Oficina Leme</h1>
          <p>Parts counter</p>
        </div>
        <button type="button" className="plate ghost" onClick={leave}>
          <span>
            {session.displayName}
            <small>{roleLabel(session.role)}</small>
          </span>
          <LogOut aria-hidden="true" />
          Sign off
        </button>
      </header>

      {fault ? (
        <p className="fault" role="alert">
          {fault}
        </p>
      ) : null}

      <section className="lead-cluster" aria-label="Live dial">
        <div className="lead-dial">
          {lead ? (
            <Dial
              size="lead"
              code={lead.code}
              name={lead.name}
              onHand={lead.onHand}
              request={lead.request}
              live
              unitCost={lead.unitCost}
            />
          ) : (
            <p className="waiting">Reading the bins.</p>
          )}
          <div className="lead-plates">
            {lead?.unitCost ? <p className="plate status">Unit cost {lead.unitCost}</p> : null}
          </div>
          {session.role === 'MANAGER' && selectedRow?.status === 'PENDING' ? (
            <div className="lever-stack">
              <button type="button" className="lever" onClick={approve} disabled={busy}>
                <span className="lever-handle" />
                <span className="lever-word">Approve</span>
              </button>
              <button type="button" className="plate action" onClick={refuse} disabled={busy}>
                Refuse
              </button>
            </div>
          ) : null}
        </div>
      </section>

      <section className="queue" aria-label={showBook ? 'Requisitions' : 'Other bins'}>
        {showBook
          ? queueRows.map((row) => (
              <div className="queue-item" key={row.id}>
                <Dial
                  size="queue"
                  code={row.partCode}
                  name={row.partName}
                  onHand={onHandOf(row.partCode)}
                  request={row.quantity}
                  live={false}
                  pressed={false}
                  onSelect={() => {
                    setFault(null)
                    setSelection({ kind: 'requisition', id: row.id })
                  }}
                />
                <p className="plate status">{PLATE[row.status]}</p>
              </div>
            ))
          : queueParts.map((part) => (
              <div className="queue-item" key={part.code}>
                <Dial
                  size="queue"
                  code={part.code}
                  name={part.name}
                  onHand={part.onHand}
                  request={null}
                  live={false}
                  onSelect={() => {
                    setFault(null)
                    setSelection({ kind: 'part', code: part.code })
                    setQuantity(part.onHand <= 1 ? 2 : 1)
                  }}
                />
              </div>
            ))}
        </section>

      <p className="plate fixture">{note.replace(/\.$/, '')}</p>

      {session.role === 'CLERK' && selectedPart ? (
        <div className="issue-stack">
          <div className="stepper">
            <button
              type="button"
              className="plate icon"
              aria-label="Decrease quantity"
              onClick={() => setQuantity((value) => Math.max(1, value - 1))}
            >
              <Minus aria-hidden="true" />
            </button>
            <label>
              Request
              <input
                inputMode="numeric"
                value={quantity}
                onChange={(event) => {
                  const next = Number(event.target.value)
                  if (Number.isInteger(next)) setQuantity(Math.min(99, Math.max(1, next)))
                }}
              />
            </label>
            <button
              type="button"
              className="plate icon"
              aria-label="Increase quantity"
              onClick={() => setQuantity((value) => Math.min(99, value + 1))}
            >
              <Plus aria-hidden="true" />
            </button>
          </div>
          <button type="button" className="plate action" onClick={issue} disabled={busy || !selectedPart}>
            Open requisition
          </button>
          <p className="lock-note">
            <Lock aria-hidden="true" />
            Approval sits with the manager.
          </p>
        </div>
      ) : null}

      <form className="finder" onSubmit={search}>
        <label>
          Find a part
          <input
            value={query}
            maxLength={40}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Code or name"
          />
        </label>
        <button type="submit" className="plate icon" aria-label="Find a part">
          <Search aria-hidden="true" />
        </button>
      </form>

      {matches ? (
        <ul className="matches">
          {matches.length === 0 ? <li className="plate status">No bin matches.</li> : null}
          {matches.map((part) => (
            <li key={part.code}>
              <button
                type="button"
                className="plate ghost"
                onClick={() => {
                  setSelection({ kind: 'part', code: part.code })
                  setQuantity(part.onHand <= 1 ? 2 : 1)
                  setMatches(null)
                  setQuery('')
                }}
              >
                {part.code} {part.name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  )
}

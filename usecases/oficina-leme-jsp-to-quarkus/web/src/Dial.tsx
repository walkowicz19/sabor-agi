import { polar, scaleMax, tickStep, valueAngle, wedgePath } from './gauge'

type DialProps = {
  code: string
  name: string
  onHand: number
  request: number | null
  live: boolean
  size: 'lead' | 'queue'
  pressed?: boolean
  onSelect?: () => void
  unitCost?: string
}

const CX = 100
const CY = 100
const FACE = 78

export function Dial({ code, name, onHand, request, live, size, pressed, onSelect, unitCost }: DialProps) {
  const max = scaleMax(onHand, live ? request : null)
  const step = tickStep(max, size === 'queue')
  const ticks: number[] = []
  for (let value = 0; value <= max + 1e-6; value += step) ticks.push(Math.round(value * 1000) / 1000)

  const needleValue = live && request !== null ? request : onHand
  const angle = valueAngle(needleValue, max)
  const showRed = live && request !== null
  const redEnd = Math.min(max, Math.max(onHand + Math.min(1.15, max * 0.2), request ?? onHand))
  const red =
    showRed && redEnd > onHand
      ? wedgePath(CX, CY, 52, 70, valueAngle(onHand, max), valueAngle(redEnd, max))
      : null

  const label = [
    `${code} ${name}`,
    `${onHand} on hand`,
    live && request !== null ? `request ${request}` : null,
    unitCost ? `unit cost ${unitCost}` : null,
  ]
    .filter(Boolean)
    .join(', ')

  const face = (
    <svg
      viewBox="0 0 200 200"
      className={size === 'lead' ? 'dial dial-lead' : 'dial dial-queue'}
      role={onSelect ? undefined : 'img'}
      aria-label={onSelect ? undefined : label}
      aria-hidden={onSelect ? true : undefined}
    >
      <circle cx={CX} cy={CY} r="96" className="bezel" />
      <circle cx={CX} cy={CY} r={FACE} className="face" />
      {red ? <path d={red} className="limit" /> : null}
      {ticks.map((value) => {
        const deg = valueAngle(value, max)
        const outer = polar(CX, CY, 74, deg)
        const inner = polar(CX, CY, 63, deg)
        const numeral = polar(CX, CY, 52, deg)
        return (
          <g key={value}>
            <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} className="tick" />
            <text x={numeral.x} y={numeral.y} className="numeral" textAnchor="middle" dominantBaseline="middle">
              {Number.isInteger(value) ? value : value.toFixed(0)}
            </text>
          </g>
        )
      })}
      <g className="needle" style={{ transform: `rotate(${angle}deg)` }}>
        <polygon points={`${CX},${CY - 70} ${CX - 3.2},${CY - 8} ${CX + 3.2},${CY - 8}`} />
        <circle cx={CX} cy={CY} r="4.5" />
      </g>
      <circle cx={CX} cy={CY} r={size === 'lead' ? 28 : 26} className="hub" />
      <text x={CX} y={size === 'lead' ? 96 : 97} className="hub-code" textAnchor="middle">
        {code}
      </text>
      <text x={CX} y={size === 'lead' ? 108 : 107} className="hub-name" textAnchor="middle">
        {name}
      </text>
    </svg>
  )

  if (!onSelect) return face

  return (
    <button type="button" className={pressed ? 'dial-hit is-selected' : 'dial-hit'} onClick={onSelect} aria-pressed={pressed} aria-label={label}>
      {face}
    </button>
  )
}

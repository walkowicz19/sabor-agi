/** Degrees clockwise from 12 o'clock. Zero sits at the bottom; values rise toward the right across a 300° sweep, so the top of the scale does not land on zero. */
export function valueAngle(value: number, max: number): number {
  const span = max <= 0 ? 1 : max
  const t = Math.max(0, Math.min(span, value)) / span
  return 180 - t * 300
}

export function polar(cx: number, cy: number, r: number, deg: number): { x: number; y: number } {
  const rad = (deg * Math.PI) / 180
  return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) }
}

export function scaleMax(onHand: number, request: number | null): number {
  const peak = Math.max(onHand, request ?? 0, 1)
  if (peak <= 6) return 6
  if (peak <= 12) return 12
  const step = peak <= 24 ? 6 : 12
  return Math.ceil(peak / step) * step
}

export function tickStep(max: number, compact = false): number {
  if (compact) {
    if (max <= 6) return 1
    if (max <= 12) return 3
    return Math.max(1, Math.round(max / 4))
  }
  if (max <= 12) return 1
  if (max <= 24) return 2
  return max / 6
}

/** Annular wedge along increasing values. Angles are clockwise from 12. */
export function wedgePath(
  cx: number,
  cy: number,
  inner: number,
  outer: number,
  startDeg: number,
  endDeg: number,
): string {
  const a = polar(cx, cy, outer, startDeg)
  const b = polar(cx, cy, outer, endDeg)
  const c = polar(cx, cy, inner, endDeg)
  const d = polar(cx, cy, inner, startDeg)
  const sweep = Math.abs(endDeg - startDeg) > 180 ? 1 : 0
  return [
    `M ${a.x.toFixed(2)} ${a.y.toFixed(2)}`,
    `A ${outer} ${outer} 0 ${sweep} 0 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`,
    `L ${c.x.toFixed(2)} ${c.y.toFixed(2)}`,
    `A ${inner} ${inner} 0 ${sweep} 1 ${d.x.toFixed(2)} ${d.y.toFixed(2)}`,
    'Z',
  ].join(' ')
}

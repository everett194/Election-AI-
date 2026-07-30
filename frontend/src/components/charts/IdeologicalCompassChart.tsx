import type { KeyboardEvent } from 'react'
import { layoutCompassPoints } from '../../lib/compassGeometry'
import { initialsFor, interpretCompassPosition } from '../../lib/derive'

export interface CompassCandidate {
  key: string
  name: string
  econ: number
  social: number
  color: string
}

interface IdeologicalCompassChartProps {
  voter: { econ: number; social: number }
  candidates: CompassCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  onHoverCandidate: (key: string | null) => void
  onTogglePinned: (key: string) => void
  variant?: 'card' | 'modal'
}

const DOMAIN = 120
const VB = 400
const PAD = 56

function toSvg(v: number): number {
  return ((v + DOMAIN) / (DOMAIN * 2)) * (VB - PAD * 2) + PAD
}

export function IdeologicalCompassChart({
  voter, candidates, selectedKeys, activeKey, onHoverCandidate, onTogglePinned, variant = 'card',
}: IdeologicalCompassChartProps) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))
  const byKey = new Map(visible.map((c) => [c.key, c]))
  const laidOut = layoutCompassPoints(visible.map((c) => ({ key: c.key, econ: c.econ, social: c.social })), voter)

  const handleKeyDown = (e: KeyboardEvent<SVGGElement>, key: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onTogglePinned(key)
    }
  }

  return (
    <div className={variant === 'modal' ? 'max-w-2xl mx-auto' : 'max-w-md mx-auto'}>
      <svg
        viewBox={`0 0 ${VB} ${VB}`}
        className="w-full h-auto"
        role="group"
        aria-label="Ideological compass showing your position and candidate positions"
      >
        <rect x={PAD} y={PAD} width={(VB - PAD * 2) / 2} height={(VB - PAD * 2) / 2} fill="#eef3fb" opacity="0.5" />
        <rect x={VB / 2} y={VB / 2} width={(VB - PAD * 2) / 2} height={(VB - PAD * 2) / 2} fill="#fdf3e0" opacity="0.4" />

        <line x1={PAD} y1={VB / 2} x2={VB - PAD} y2={VB / 2} stroke="#dde3ed" strokeWidth="1.5" />
        <line x1={VB / 2} y1={PAD} x2={VB / 2} y2={VB - PAD} stroke="#dde3ed" strokeWidth="1.5" />

        <text x={VB / 2} y={PAD - 20} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600">MORE CIVIL LIBERTIES</text>
        <text x={VB / 2} y={VB - PAD + 32} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600">MORE AUTHORITY</text>
        <text x={PAD - 34} y={VB / 2} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600"
          transform={`rotate(-90 ${PAD - 34} ${VB / 2})`}>PUBLIC INVESTMENT</text>
        <text x={VB - PAD + 34} y={VB / 2} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600"
          transform={`rotate(90 ${VB - PAD + 34} ${VB / 2})`}>MARKETS</text>

        <circle cx={toSvg(voter.econ)} cy={toSvg(-voter.social)} r="9" fill="#c0392b" opacity="0.9" />
        <circle cx={toSvg(voter.econ)} cy={toSvg(-voter.social)} r="15" fill="#c0392b" opacity="0.15" />
        <text x={toSvg(voter.econ)} y={toSvg(-voter.social) - 20} textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="700">YOU</text>

        {laidOut.map((point) => {
          const source = byKey.get(point.key)
          if (!source) return null
          const cx = toSvg(point.renderEcon)
          const cy = toSvg(-point.renderSocial)
          const active = activeKey === point.key
          const dimmed = activeKey !== null && !active

          return (
            <g
              key={point.key}
              tabIndex={0}
              role="button"
              aria-label={`${source.name}: ${interpretCompassPosition(source.econ, source.social)}`}
              aria-pressed={active}
              onMouseEnter={() => onHoverCandidate(point.key)}
              onMouseLeave={() => onHoverCandidate(null)}
              onFocus={() => onHoverCandidate(point.key)}
              onBlur={() => onHoverCandidate(null)}
              onClick={() => onTogglePinned(point.key)}
              onKeyDown={(e) => handleKeyDown(e, point.key)}
              opacity={dimmed ? 0.35 : 1}
              className="cursor-pointer outline-none"
            >
              <title>
                {`${source.name} — economic: ${Math.round(source.econ)}, governance: ${Math.round(source.social)}. ${interpretCompassPosition(source.econ, source.social)}`}
                {point.clusterSize > 1 ? ` Shares this area with ${point.clusterSize - 1} other candidate${point.clusterSize > 2 ? 's' : ''}.` : ''}
              </title>
              {point.jittered && (
                <line
                  x1={toSvg(point.econ)} y1={toSvg(-point.social)} x2={cx} y2={cy}
                  stroke={source.color} strokeWidth="1" strokeDasharray="2 2" opacity="0.6"
                />
              )}
              <circle
                cx={cx} cy={cy} r={active ? 14 : 12} fill={source.color}
                stroke={active ? '#0f2340' : 'white'} strokeWidth={active ? 2.5 : 1.5}
              />
              {point.clusterSize > 1 && (
                <circle cx={cx} cy={cy} r={active ? 18 : 16} fill="none" stroke={source.color} strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
              )}
              <text x={cx} y={cy + 4} textAnchor="middle" fill="white" fontSize="9" fontWeight="700" pointerEvents="none">
                {initialsFor(source.name)}
              </text>
              {active && (
                <text x={cx} y={cy - 20} textAnchor="middle" fill="#0f2340" fontSize="10" fontWeight="600" pointerEvents="none">
                  {source.name}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function CompassDetailsPanel({ candidates, selectedKeys, activeKey, voter }: {
  candidates: CompassCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  voter: { econ: number; social: number }
}) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))
  const focused = visible.find((c) => c.key === activeKey) ?? visible[0] ?? null

  return (
    <div className="bg-soft/60 rounded-xl border border-border p-3.5 text-xs space-y-2.5">
      <div>
        <p className="font-semibold text-navy mb-0.5">You</p>
        <p className="text-muted">
          Economic: <span className="font-mono text-navy">{Math.round(voter.econ)}</span>
          {' · '}
          Governance: <span className="font-mono text-navy">{Math.round(voter.social)}</span>
        </p>
      </div>
      {focused ? (
        <div className="pt-2 border-t border-border/60">
          <p className="font-semibold text-navy mb-0.5 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: focused.color }} aria-hidden="true" />
            {focused.name}
          </p>
          <p className="text-muted">
            Economic: <span className="font-mono text-navy">{Math.round(focused.econ)}</span>
            {' · '}
            Governance: <span className="font-mono text-navy">{Math.round(focused.social)}</span>
          </p>
          <p className="text-muted mt-1 leading-relaxed">{interpretCompassPosition(focused.econ, focused.social)}</p>
        </div>
      ) : (
        <p className="text-muted-light italic pt-2 border-t border-border/60">Hover or select a candidate to see their exact values.</p>
      )}
    </div>
  )
}

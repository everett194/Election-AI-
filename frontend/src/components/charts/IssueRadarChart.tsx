import type { ReactElement } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip,
} from 'recharts'
import type { BaseTickContentProps, TooltipContentProps } from 'recharts'

export interface RadarSeriesCandidate {
  key: string
  name: string
  color: string
}

interface IssueRadarChartProps {
  data: Record<string, string | number>[]
  candidates: RadarSeriesCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  onHoverCandidate: (key: string | null) => void
  onTogglePinned: (key: string) => void
  variant?: 'card' | 'modal'
}

function wrapLabel(value: string): string[] {
  const words = value.split(' ')
  const lines: string[] = []
  let current = ''
  for (const word of words) {
    const next = current ? `${current} ${word}` : word
    if (next.length > 14 && current) {
      lines.push(current)
      current = word
    } else {
      current = next
    }
  }
  if (current) lines.push(current)
  if (lines.length > 2) {
    const truncated = lines.slice(0, 2)
    truncated[1] = `${truncated[1].slice(0, 11)}…`
    return truncated
  }
  return lines
}

function renderCategoryTick(props: BaseTickContentProps): ReactElement {
  const { x, y, payload, textAnchor } = props
  const numX = Number(x)
  const numY = Number(y)
  const label = String(payload.value)
  const lines = wrapLabel(label)

  return (
    <text x={numX} y={numY} textAnchor={textAnchor} fill="#6b7a99" fontSize={10} dy={lines.length > 1 ? -4 : 3}>
      <title>{label}</title>
      {lines.map((line, i) => (
        <tspan key={i} x={numX} dy={i === 0 ? 0 : 12}>{line}</tspan>
      ))}
    </text>
  )
}

function RadarTooltipContent({ active, payload, label }: TooltipContentProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="bg-surface border border-border rounded-lg shadow-lg px-3 py-2 text-xs max-w-[220px]">
      <p className="font-semibold text-navy mb-1">{label}</p>
      <div className="space-y-0.5">
        {payload.map((entry) => (
          <div key={String(entry.dataKey)} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5 text-navy/80 truncate">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
              {entry.name}
            </span>
            <span className="font-mono text-navy shrink-0">{entry.value ?? '–'}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function IssueRadarChart({
  data, candidates, selectedKeys, activeKey, onHoverCandidate, onTogglePinned, variant = 'card',
}: IssueRadarChartProps) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))

  return (
    <div className={variant === 'modal' ? 'h-[70vh]' : 'h-[300px] sm:h-[340px]'}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 28, right: 48, bottom: 28, left: 48 }}>
          <PolarGrid stroke="#dde3ed" strokeOpacity={0.7} />
          <PolarAngleAxis dataKey="category" tick={renderCategoryTick} />
          <Radar
            name="You"
            dataKey="You"
            stroke="#0f2340"
            strokeDasharray="4 3"
            strokeWidth={1.5}
            fill="none"
            isAnimationActive={false}
          />
          {visible.map((c) => {
            const dimmed = activeKey !== null && activeKey !== c.key
            return (
              <Radar
                key={c.key}
                name={c.name}
                dataKey={c.name}
                stroke={c.color}
                fill={c.color}
                fillOpacity={dimmed ? 0.04 : 0.12}
                strokeOpacity={dimmed ? 0.25 : 1}
                strokeWidth={activeKey === c.key ? 3 : 2}
                onMouseEnter={() => onHoverCandidate(c.key)}
                onMouseLeave={() => onHoverCandidate(null)}
                onClick={() => onTogglePinned(c.key)}
                isAnimationActive={false}
              />
            )
          })}
          <RechartsTooltip content={(props) => <RadarTooltipContent {...(props as TooltipContentProps<number, string>)} />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

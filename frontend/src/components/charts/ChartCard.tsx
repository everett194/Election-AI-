import { useState, type ReactNode } from 'react'
import { Modal } from '../ui'

interface ChartCardProps {
  title: string
  subtitle: string
  children: (variant: 'card' | 'modal') => ReactNode
}

export function ChartCard({ title, subtitle, children }: ChartCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-surface rounded-2xl border border-border p-5">
      <div className="flex items-start justify-between gap-3 mb-1">
        <h3 className="font-semibold text-navy text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
          {title}
        </h3>
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="shrink-0 text-[11px] font-medium text-civic hover:text-civic-light flex items-center gap-1 transition-colors"
          aria-label={`Expand ${title}`}
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 2H2v4M10 2h4v4M6 14H2v-4M10 14h4v-4" />
          </svg>
          Expand
        </button>
      </div>
      <p className="text-[10px] text-muted mb-2">{subtitle}</p>
      {children('card')}

      <Modal open={expanded} onClose={() => setExpanded(false)} title={title} size="xl">
        <p className="text-xs text-muted mb-3">{subtitle}</p>
        {children('modal')}
      </Modal>
    </div>
  )
}

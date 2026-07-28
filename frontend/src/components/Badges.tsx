import type { IssueConfidence } from '../api'
import { Tooltip } from './ui'

// ─── EvidenceBadge ──────────────────────────────────────────────────────────
//
// Real confidence taxonomy from the backend's research pipeline (see
// election_lookup.py's research_candidates_for_race_with_fallback):
// real Tavily-backed evidence is tagged explicit / strong_inference /
// weak_inference; "speculative" means no real evidence was found and this
// is an unverified AI estimate; "unavailable" means the candidate simply
// has no answer at all for this question. There is no way to honestly
// distinguish "candidate-provided" vs "third-party" vs "voting-record"
// sources from what Tavily returns, so this taxonomy does not attempt to.

export type EvidenceType = IssueConfidence | 'unavailable'

const EVIDENCE_CONFIG: Record<
  EvidenceType,
  { label: string; shortLabel: string; color: string; tooltip: string; icon: React.ReactNode }
> = {
  explicit: {
    label: 'Explicit Statement',
    shortLabel: 'Explicit',
    color: 'bg-teal-light text-teal border-teal/25',
    tooltip: 'Directly supported by a specific source found during research.',
    icon: (
      <svg viewBox="0 0 14 14" fill="currentColor" className="w-3 h-3">
        <path fillRule="evenodd" clipRule="evenodd" d="M7 1a6 6 0 100 12A6 6 0 007 1zm2.78 4.28l-3.5 3.5a.75.75 0 01-1.06 0l-1.5-1.5a.75.75 0 111.06-1.06l.97.97 2.97-2.97a.75.75 0 111.06 1.06z"/>
      </svg>
    ),
  },
  strong_inference: {
    label: 'Strong Inference',
    shortLabel: 'Strong Inference',
    color: 'bg-blue-50 text-blue-700 border-blue-200',
    tooltip: 'Strongly implied by real evidence found during research, though not stated in so many words.',
    icon: (
      <svg viewBox="0 0 14 14" fill="currentColor" className="w-3 h-3">
        <path d="M7 7A3 3 0 107 1a3 3 0 000 6zm-4 5a4 4 0 118 0H3z"/>
      </svg>
    ),
  },
  weak_inference: {
    label: 'Weak Inference',
    shortLabel: 'Weak Inference',
    color: 'bg-orange-50 text-orange-700 border-orange-200',
    tooltip: 'Only weakly suggested by the evidence found during research. Treat with caution.',
    icon: (
      <svg viewBox="0 0 14 14" fill="currentColor" className="w-3 h-3">
        <path fillRule="evenodd" clipRule="evenodd" d="M1 2h12v9H1V2zm1 8h10V3H2v7zm1-5h8v1H3V5zm0 2h5v1H3V7z"/>
      </svg>
    ),
  },
  speculative: {
    label: 'Unverified Estimate',
    shortLabel: 'Estimate',
    color: 'bg-purple-50 text-purple-700 border-purple-200',
    tooltip: 'No real evidence was found for this question. This is an AI estimate, not sourced fact -- verify independently.',
    icon: (
      <svg viewBox="0 0 14 14" fill="currentColor" className="w-3 h-3">
        <path d="M7 1.5a.75.75 0 01.75.75V4h1.5a.75.75 0 010 1.5H7.75v2l2.25 1.5H11a.75.75 0 010 1.5h-1l-2.25-1.5-2.25 1.5H4.5a.75.75 0 010-1.5h1L7.75 7V5.5H6.25a.75.75 0 010-1.5h1.5V2.25A.75.75 0 017 1.5z"/>
      </svg>
    ),
  },
  unavailable: {
    label: 'Information Unavailable',
    shortLabel: 'Unavailable',
    color: 'bg-gray-50 text-gray-400 border-gray-200',
    tooltip: 'No position found for this question -- not sourced, not estimated.',
    icon: (
      <svg viewBox="0 0 14 14" fill="currentColor" className="w-3 h-3">
        <path fillRule="evenodd" clipRule="evenodd" d="M7 1a6 6 0 100 12A6 6 0 007 1zm-.75 4a.75.75 0 011.5 0v3a.75.75 0 01-1.5 0V5zM7 9.5a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
      </svg>
    ),
  },
}

export function EvidenceBadge({
  type,
  size = 'sm',
  withTooltip = false,
}: {
  type: EvidenceType
  size?: 'sm' | 'xs'
  withTooltip?: boolean
}) {
  const config = EVIDENCE_CONFIG[type]
  const badge = (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${config.color}
        ${size === 'xs' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'}`}
    >
      {config.icon}
      {size === 'xs' ? config.shortLabel : config.label}
    </span>
  )
  if (!withTooltip) return badge
  return <Tooltip content={config.tooltip}>{badge}</Tooltip>
}

// ─── ConfidenceIndicator ─────────────────────────────────────────────────────

const CONFIDENCE_CONFIG = [
  { label: 'Very Limited', color: 'bg-red-400' },
  { label: 'Limited', color: 'bg-gold' },
  { label: 'Moderate', color: 'bg-civic-light' },
  { label: 'Good', color: 'bg-teal' },
  { label: 'Comprehensive', color: 'bg-teal' },
]

export function ConfidenceIndicator({
  level,
  showLabel = true,
}: {
  level: number
  showLabel?: boolean
}) {
  const config = CONFIDENCE_CONFIG[level - 1] ?? CONFIDENCE_CONFIG[0]
  return (
    <div className="inline-flex items-center gap-2">
      <div className="flex gap-0.5" role="img" aria-label={`Information confidence: ${config.label}`}>
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={`h-2.5 w-2.5 rounded-sm transition-colors ${
              i <= level ? config.color : 'bg-soft-mid'
            }`}
          />
        ))}
      </div>
      {showLabel && (
        <span className="text-[11px] text-muted font-mono">{config.label}</span>
      )}
    </div>
  )
}

// ─── PartyLabel ──────────────────────────────────────────────────────────────

export function PartyLabel({ party }: { party: string | null }) {
  if (!party) {
    return (
      <span className="inline-flex items-center text-xs font-medium text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full border border-gray-200">
        Nonpartisan
      </span>
    )
  }
  const styles: Record<string, string> = {
    Democrat:     'text-blue-700 bg-blue-50 border-blue-200',
    Republican:   'text-red-700 bg-red-50 border-red-200',
    Green:        'text-green-700 bg-green-50 border-green-200',
    Libertarian:  'text-yellow-700 bg-yellow-50 border-yellow-200',
    Independent:  'text-gray-600 bg-gray-100 border-gray-200',
  }
  return (
    <span className={`inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full border ${styles[party] ?? styles.Independent}`}>
      {party}
    </span>
  )
}

// ─── IssueTag ─────────────────────────────────────────────────────────────────

export function IssueTag({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-civic-pale text-civic border border-civic/20">
      {label}
    </span>
  )
}

// ─── PolicyScaleBar ───────────────────────────────────────────────────────────

export function PolicyScaleBar({
  value,
  label,
}: {
  value: number
  label?: string
}) {
  const pct = ((value - 1) / 4) * 100
  return (
    <div className="space-y-1.5">
      {label && <p className="text-xs text-muted">{label}</p>}
      <div className="flex items-center gap-2.5">
        <span className="text-[9px] text-muted w-16 text-right shrink-0 uppercase tracking-wide">Approach 1</span>
        <div className="relative flex-1 h-2 bg-soft-mid rounded-full">
          <div
            className="absolute inset-y-0 left-0 bg-civic rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white border-2 border-civic rounded-full shadow-sm transition-all"
            style={{ left: `calc(${pct}% - 7px)` }}
          />
        </div>
        <span className="text-[9px] text-muted w-16 shrink-0 uppercase tracking-wide">Approach 2</span>
      </div>
    </div>
  )
}

// ─── MissingInfoBanner ───────────────────────────────────────────────────────

export function MissingInfoBanner({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2.5 px-3.5 py-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs leading-relaxed">
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5 text-amber-500">
        <path fillRule="evenodd" clipRule="evenodd" d="M8.485 1.495c.673-1.167 2.357-1.167 3.03 0l5.28 9.167c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625l5.28-9.167zM8 5.5a.75.75 0 01.75.75v2.5a.75.75 0 01-1.5 0v-2.5A.75.75 0 018 5.5zm0 6.5a.75.75 0 100-1.5.75.75 0 000 1.5z"/>
      </svg>
      {text}
    </div>
  )
}

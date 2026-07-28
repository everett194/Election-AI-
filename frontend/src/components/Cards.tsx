import { ConfidenceIndicator, IssueTag, PartyLabel } from './Badges'
import { Skeleton } from './ui'

// ─── Candidate avatar ─────────────────────────────────────────────────────────

const AVATAR_PALETTE = [
  'from-navy to-navy-mid',
  'from-civic to-civic-light',
  'from-teal to-teal-hover',
  'from-[#4a6382] to-[#2d5fa0]',
]

function Avatar({ initials, index = 0, size = 'md' }: { initials: string; index?: number; size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-10 h-10 text-sm', md: 'w-14 h-14 text-lg', lg: 'w-24 h-24 text-3xl' }
  const radii = { sm: 'rounded-lg', md: 'rounded-xl', lg: 'rounded-2xl' }
  return (
    <div className={`${sizes[size]} ${radii[size]} bg-gradient-to-br ${AVATAR_PALETTE[index % AVATAR_PALETTE.length]} flex items-center justify-center shrink-0`}>
      <span className="text-white font-bold" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
        {initials}
      </span>
    </div>
  )
}

// ─── CandidateCard ────────────────────────────────────────────────────────────

interface CandidateCardProps {
  name: string
  party: string | null
  photoInitials: string
  issueTags: string[]
  confidenceLevel: number
  summary: string | null
  index?: number
  onViewProfile: () => void
  selected?: boolean
  onToggleCompare?: () => void
  showCompare?: boolean
}

export function CandidateCard({
  name,
  party,
  photoInitials,
  issueTags,
  confidenceLevel,
  summary,
  index = 0,
  onViewProfile,
  selected = false,
  onToggleCompare,
  showCompare = false,
}: CandidateCardProps) {
  return (
    <div
      className={`group bg-surface rounded-2xl border transition-all duration-200 overflow-hidden
        ${selected
          ? 'border-civic shadow-md shadow-civic/10 ring-2 ring-civic/15'
          : 'border-border hover:border-border-strong hover:shadow-md hover:shadow-navy/8'
        }`}
    >
      {selected && <div className="h-0.5 bg-civic" />}

      <div className="p-5">
        <div className="flex items-start gap-3.5 mb-4">
          <Avatar initials={photoInitials} index={index} size="md" />
          <div className="flex-1 min-w-0">
            <h3
              className="font-semibold text-navy text-[15px] leading-tight mb-1.5 group-hover:text-civic transition-colors"
              style={{ fontFamily: 'Fraunces, Georgia, serif' }}
            >
              {name}
            </h3>
            <div className="flex flex-wrap items-center gap-1.5">
              <PartyLabel party={party} />
            </div>
          </div>

          {showCompare && onToggleCompare && (
            <label className="flex flex-col items-center gap-1 cursor-pointer shrink-0 -mt-0.5">
              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                ${selected ? 'bg-civic border-civic' : 'border-border-strong hover:border-civic'}`}
                onClick={onToggleCompare}
              >
                {selected && (
                  <svg viewBox="0 0 12 12" fill="none" className="w-3 h-3">
                    <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <span className="text-[9px] text-muted font-medium">Compare</span>
            </label>
          )}
        </div>

        <p className="text-sm text-navy/65 leading-relaxed line-clamp-3 mb-3.5">
          {summary ?? 'No documented position found yet -- take the questionnaire to trigger research on this candidate.'}
        </p>

        <div className="flex flex-wrap gap-1.5 mb-4">
          {issueTags.length > 0 ? (
            issueTags.map((issue) => <IssueTag key={issue} label={issue} />)
          ) : (
            <span className="text-xs text-muted italic">No issue coverage yet</span>
          )}
        </div>

        <div className="pt-3.5 border-t border-border flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] text-muted-light uppercase tracking-wide mb-1.5">Information confidence</p>
            <ConfidenceIndicator level={confidenceLevel} showLabel />
          </div>
          <button
            onClick={onViewProfile}
            className="px-4 py-2 rounded-xl bg-civic text-white text-xs font-semibold hover:bg-civic-hover active:bg-civic-hover transition-colors whitespace-nowrap"
          >
            View Profile
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── RaceCard ─────────────────────────────────────────────────────────────────

interface RaceCardProps {
  officeLabel: string
  jurisdictionName: string
  electionDate: string | null
  candidateCount: number
  notes: string | null
  onViewCandidates: () => void
  onTakeQuiz: () => void
}

export function RaceCard({ officeLabel, jurisdictionName, electionDate, candidateCount, notes, onViewCandidates, onTakeQuiz }: RaceCardProps) {
  return (
    <div className="group bg-surface rounded-2xl border border-border hover:border-border-strong hover:shadow-md hover:shadow-navy/8 transition-all duration-200 overflow-hidden">
      <div className="h-0.5 bg-gradient-to-r from-civic to-civic-light" />

      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <h3
            className="font-semibold text-navy text-[15px] leading-snug group-hover:text-civic transition-colors"
            style={{ fontFamily: 'Fraunces, Georgia, serif' }}
          >
            {officeLabel}
          </h3>
          <span className="shrink-0 text-xs font-mono font-medium text-civic bg-civic-pale px-2.5 py-1 rounded-lg border border-civic/20">
            {candidateCount} candidate{candidateCount === 1 ? '' : 's'}
          </span>
        </div>

        <p className="text-sm text-muted mb-1">{jurisdictionName}</p>

        <div className="flex items-center gap-1.5 text-xs text-muted mb-3">
          <svg viewBox="0 0 14 14" fill="currentColor" className="w-3.5 h-3.5 text-civic-light shrink-0">
            <path fillRule="evenodd" clipRule="evenodd" d="M2 2a1 1 0 011-1h8a1 1 0 011 1v1h1a1 1 0 011 1v8a1 1 0 01-1 1H1a1 1 0 01-1-1V4a1 1 0 011-1h1V2zm8 2H4v7h6V4z"/>
          </svg>
          {electionDate ?? 'Election date unknown'}
        </div>

        {notes && (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 leading-relaxed mb-4">
            {notes}
          </p>
        )}

        <div className="flex gap-2.5">
          <button
            onClick={onViewCandidates}
            disabled={candidateCount === 0}
            className="flex-1 py-2.5 rounded-xl bg-civic text-white text-xs font-semibold hover:bg-civic-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            View Candidates
          </button>
          <button
            onClick={onTakeQuiz}
            className="flex-1 py-2.5 rounded-xl border border-civic text-civic text-xs font-semibold hover:bg-civic-pale transition-colors"
          >
            Take Quiz
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── CandidateCardSkeleton ─────────────────────────────────────────────────────

export function CandidateCardSkeleton() {
  return (
    <div className="bg-surface rounded-2xl border border-border p-5 space-y-4">
      <div className="flex gap-3.5">
        <Skeleton className="w-14 h-14 rounded-xl shrink-0" />
        <div className="flex-1 space-y-2 py-1">
          <Skeleton className="h-4 w-3/5" />
          <Skeleton className="h-3 w-2/5" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
      </div>
      <div className="flex gap-1.5">
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  )
}

export function RaceCardSkeleton() {
  return (
    <div className="bg-surface rounded-2xl border border-border overflow-hidden">
      <div className="h-0.5 bg-soft-mid" />
      <div className="p-5 space-y-3">
        <div className="flex justify-between gap-3">
          <Skeleton className="h-5 w-3/5" />
          <Skeleton className="h-6 w-20 rounded-lg" />
        </div>
        <Skeleton className="h-3 w-2/5" />
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <div className="flex gap-2.5 pt-1">
          <Skeleton className="flex-1 h-9 rounded-xl" />
          <Skeleton className="flex-1 h-9 rounded-xl" />
        </div>
      </div>
    </div>
  )
}

export { Avatar }

import { useEffect } from 'react'
import { useNav } from '../context/nav'
import { useAppData, candidateKey } from '../context/appData'
import { EvidenceBadge, PartyLabel, MissingInfoBanner } from '../components/Badges'
import { Avatar } from '../components/Cards'
import { Alert, EmptyState } from '../components/ui'
import { initialsFor } from '../lib/derive'
import type { ApiQuestion, Office } from '../api'

function MiniScale({ value }: { value: number | null }) {
  if (value === null) return <span className="text-xs text-muted italic">Not available</span>
  const pct = ((value - 1) / 4) * 100
  return (
    <div className="flex items-center gap-1.5 w-full">
      <span className="text-[9px] text-muted shrink-0">1</span>
      <div className="relative flex-1 h-1.5 bg-soft-mid rounded-full">
        <div className="absolute inset-y-0 left-0 bg-civic rounded-full transition-all" style={{ width: `${pct}%` }} />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-2 border-civic rounded-full shadow-sm"
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>
      <span className="text-[9px] text-muted shrink-0">5</span>
    </div>
  )
}

export default function ComparisonPage() {
  const { navigate, params } = useNav()
  const { elections, questions, ensureQuestionsLoaded, profiles, comparisonKeys, toggleComparison, ensureRaceResearched, raceResearchStatus } = useAppData()

  const office = params.office as Office | undefined
  const race = elections.races.find((r) => r.office === office)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

  useEffect(() => {
    if (office) void ensureRaceResearched(office)
  }, [office, ensureRaceResearched])

  if (!race) {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-5xl mx-auto px-4 sm:px-6 py-16">
        <EmptyState
          title="No race selected"
          description="Select at least two candidates to compare from a race page first."
          action={<button onClick={() => navigate('elections')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Back to elections</button>}
        />
      </div>
    )
  }

  const shownKeys = comparisonKeys.filter((k) => k.startsWith(`${race.office}::`))
  const shownNames = shownKeys.map((k) => k.split('::')[1])
  const candidates = race.candidates.filter((c) => shownNames.includes(c.name))
  const n = candidates.length

  const researching = raceResearchStatus[race.office] === 'loading'

  const categories: { id: string; label: string; questions: ApiQuestion[] }[] = []
  for (const q of questions) {
    let group = categories.find((c) => c.id === q.category)
    if (!group) {
      group = { id: q.category, label: q.category_label, questions: [] }
      categories.push(group)
    }
    group.questions.push(q)
  }

  const gridCols = { 0: 'grid-cols-1', 1: 'grid-cols-2', 2: 'grid-cols-3', 3: 'grid-cols-4', 4: 'grid-cols-5' }[n] ?? 'grid-cols-2'
  const remaining = race.candidates.filter((c) => !shownNames.includes(c.name))

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-surface border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center gap-2 text-xs text-muted mb-3">
            <button onClick={() => navigate('home')} className="hover:text-civic">Home</button>
            <span>/</span>
            <button onClick={() => navigate('race', { office: race.office })} className="hover:text-civic">{race.office_label}</button>
            <span>/</span>
            <span className="text-navy font-medium">Compare Candidates</span>
          </div>
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl font-bold text-navy" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                Compare Candidates
              </h1>
              <p className="text-sm text-muted mt-1">{race.office_label} · {race.jurisdiction_name}</p>
            </div>
            <button
              onClick={() => navigate('quiz')}
              className="px-4 py-2 rounded-xl bg-teal text-white text-sm font-semibold hover:bg-teal-hover transition-colors"
            >
              Take the Quiz →
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row gap-3 mb-6 flex-wrap">
          <Alert type="info">
            Position scales below come from an automated search of public sources. Positions labeled "Unverified Estimate" are AI-generated guesses, not sourced evidence. This comparison is not an endorsement -- verify independently.
          </Alert>
        </div>

        {n < 2 ? (
          <EmptyState
            title="Select at least two candidates"
            description="Go back to the race page and choose 2-4 candidates to compare."
            action={<button onClick={() => navigate('race', { office: race.office })} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Back to {race.office_label}</button>}
          />
        ) : (
          <>
            {/* Candidate headers row */}
            <div className={`grid ${gridCols} gap-3 mb-6`}>
              {candidates.map((c, i) => (
                <div key={c.name} className="relative bg-surface rounded-xl border border-border p-4">
                  <button
                    onClick={() => toggleComparison(race.office, c.name)}
                    className="absolute top-2.5 right-2.5 w-6 h-6 rounded-lg flex items-center justify-center text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                    aria-label={`Remove ${c.name}`}
                  >
                    <svg viewBox="0 0 12 12" fill="currentColor" className="w-3.5 h-3.5">
                      <path d="M2.22 2.22a.75.75 0 011.06 0L6 4.94l2.72-2.72a.75.75 0 111.06 1.06L7.06 6l2.72 2.72a.75.75 0 11-1.06 1.06L6 7.06 3.28 9.78a.75.75 0 01-1.06-1.06L4.94 6 2.22 3.28a.75.75 0 010-1.06z"/>
                    </svg>
                  </button>
                  <div className="flex items-center gap-3 mb-2 pr-6">
                    <Avatar initials={initialsFor(c.name)} index={i} size="sm" />
                    <div className="min-w-0">
                      <p className="font-semibold text-navy text-sm leading-snug" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{c.name}</p>
                      <PartyLabel party={c.party} />
                    </div>
                  </div>
                </div>
              ))}
              {shownKeys.length < 4 && remaining.length > 0 && (
                <div className="bg-surface rounded-xl border-2 border-dashed border-border p-4 flex flex-col items-center justify-center gap-2 min-h-[96px]">
                  <p className="text-xs text-muted text-center">Add candidate</p>
                  <select
                    className="w-full text-xs py-1.5 px-2 rounded-lg border border-border text-navy bg-soft focus:outline-none focus:ring-1 focus:ring-civic"
                    value=""
                    onChange={(e) => { if (e.target.value) toggleComparison(race.office, e.target.value) }}
                  >
                    <option value="">Select…</option>
                    {remaining.map((c) => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {researching && <p className="text-sm text-muted mb-4">Researching candidate positions…</p>}

            {/* Issue rows, grouped by category */}
            <div className="bg-surface rounded-2xl border border-border overflow-hidden">
              {categories.map((category, catIdx) => (
                <div key={category.id}>
                  <div className={`grid ${gridCols} bg-soft ${catIdx > 0 ? 'border-t border-border' : ''}`}>
                    <div className="px-4 py-2 col-span-full">
                      <span className="text-xs font-mono font-semibold text-navy uppercase tracking-widest">{category.label}</span>
                    </div>
                  </div>
                  {category.questions.map((question, qIdx) => (
                    <div key={question.id} className={`grid ${gridCols} ${qIdx < category.questions.length - 1 ? 'border-b border-border/50' : 'border-b border-border'}`}>
                      <div className="bg-soft/60 px-4 py-3 flex flex-col justify-center border-r border-border">
                        <p className="text-xs text-navy/80 leading-snug">{question.text}</p>
                      </div>
                      {candidates.map((c) => {
                        const profile = profiles[candidateKey(race.office, c.name)]
                        const sourced = profile?.sourced_positions.find((p) => p.question_id === question.id)
                        return (
                          <div key={c.name} className="px-4 py-3 border-l border-border">
                            <div className="mb-2">
                              <EvidenceBadge type={sourced?.confidence ?? 'unavailable'} size="xs" withTooltip />
                            </div>
                            <MiniScale value={sourced?.position ?? null} />
                            {sourced?.source && (
                              <a href={sourced.source.url} target="_blank" rel="noopener noreferrer" className="mt-1 block text-[10px] text-civic hover:text-civic-light truncate">
                                {sourced.source.title || 'Source'} ↗
                              </a>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div className="mt-6 space-y-4">
              <MissingInfoBanner text="Positions labeled 'Unverified Estimate' or 'Unavailable' should be verified with independent research before making voting decisions." />

              <div className="bg-navy rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
                <div>
                  <p className="font-semibold text-white text-lg" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                    See how these candidates compare to your own views
                  </p>
                  <p className="text-blue-200/80 text-sm mt-1">
                    Take the questionnaire for a personalized alignment estimate.
                  </p>
                </div>
                <button
                  onClick={() => navigate('quiz')}
                  className="shrink-0 px-6 py-3 rounded-xl bg-teal text-white font-semibold hover:bg-teal-hover transition-colors"
                >
                  Take the Quiz →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

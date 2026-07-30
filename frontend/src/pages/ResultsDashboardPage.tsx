import { useEffect, useMemo, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData, candidateKey } from '../context/appData'
import { ConfidenceIndicator } from '../components/Badges'
import { Avatar } from '../components/Cards'
import { Alert, EmptyState } from '../components/ui'
import { ChartCard } from '../components/charts/ChartCard'
import { CandidateSelector } from '../components/charts/CandidateSelector'
import { IssueRadarChart } from '../components/charts/IssueRadarChart'
import { IdeologicalCompassChart, CompassDetailsPanel } from '../components/charts/IdeologicalCompassChart'
import { useCandidateSelection } from '../hooks/useCandidateSelection'
import { buildCandidateColorMap } from '../lib/candidateColors'
import { categoryLabelMap, confidenceBucket, initialsFor } from '../lib/derive'
import type { CandidateResult } from '../api'

// ─── Match card ───────────────────────────────────────────────────────────────

function MatchCard({ result, rank, expanded, onToggle, categoryLabels }: {
  result: CandidateResult
  rank: number
  expanded: boolean
  onToggle: () => void
  categoryLabels: Record<string, string>
}) {
  const { navigate } = useNav()
  const { profiles } = useAppData()
  const profile = profiles[candidateKey(result.office, result.name)]

  const barColor = rank === 1 ? 'bg-teal' : rank === 2 ? 'bg-civic' : 'bg-muted/40'
  const pctColor = rank === 1 ? 'text-teal' : rank === 2 ? 'text-civic' : 'text-muted'
  const pct = result.compatibility.overall_pct

  return (
    <div className={`bg-surface rounded-2xl border overflow-hidden transition-shadow hover:shadow-md
      ${rank === 1 ? 'border-teal/40 shadow-sm shadow-teal/10' : 'border-border'}`}>

      {rank === 1 && pct !== null && (
        <div className="bg-teal px-4 py-1.5 flex items-center gap-2 text-white text-xs font-semibold">
          Closest estimated alignment — not an endorsement. Verify with independent research.
        </div>
      )}

      <div className="p-5">
        <div className="flex items-start gap-3.5">
          <Avatar initials={initialsFor(result.name)} index={rank - 1} size="md" />
          <div className="flex-1">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-navy text-base leading-snug" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                  {result.name}
                </h3>
              </div>
              <div className="text-right shrink-0">
                {pct !== null ? (
                  <>
                    <span className={`text-3xl font-bold font-mono ${pctColor}`}>~{Math.round(pct)}%</span>
                    <p className="text-[10px] text-muted">estimated alignment</p>
                  </>
                ) : (
                  <p className="text-xs text-muted italic max-w-[120px]">No overlapping answered questions</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {pct !== null && (
          <>
            <div className="mt-4 h-2.5 bg-soft-mid rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
            </div>
            <p className="text-[10px] text-muted mt-1 text-right">{result.compatibility.question_count} question{result.compatibility.question_count === 1 ? '' : 's'} used in this estimate</p>
          </>
        )}

        <div className="mt-3 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-muted-light uppercase tracking-wide mb-1.5">Confidence level</p>
            <ConfidenceIndicator level={confidenceBucket(profile)} showLabel />
          </div>
          <button
            onClick={() => navigate('candidate', { office: result.office, name: result.name })}
            className="text-xs text-civic font-medium hover:text-civic-light transition-colors"
          >
            Full profile →
          </button>
        </div>

        {pct !== null && (
          <button
            onClick={onToggle}
            className="mt-4 w-full py-2 rounded-xl border border-border text-xs font-medium text-muted hover:text-navy hover:border-border-strong transition-colors flex items-center justify-center gap-1.5"
          >
            {expanded ? 'Hide' : 'Show'} issue-by-issue breakdown
          </button>
        )}

        {expanded && pct !== null && (
          <div className="mt-4 space-y-1.5 border-t border-border pt-4">
            <div className="grid grid-cols-2 gap-2 text-[10px] text-muted uppercase tracking-wide pb-1 font-medium">
              <span>Category</span><span className="text-right">Alignment</span>
            </div>
            {Object.entries(result.compatibility.by_category).map(([category, score]) => (
              <div key={category} className="grid grid-cols-2 gap-2 items-center py-1.5 border-b border-border/40 last:border-0">
                <span className="text-xs text-navy/70">{categoryLabels[category] ?? category}</span>
                <span className="text-xs font-medium text-navy text-right">{Math.round(score)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── ResultsDashboardPage ─────────────────────────────────────────────────────

export default function ResultsDashboardPage() {
  const { navigate } = useNav()
  const { results, resultsStatus, resultsError, questions, ensureQuestionsLoaded, computeResults } = useAppData()
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [showMethodology, setShowMethodology] = useState(false)
  const [showCompassMethod, setShowCompassMethod] = useState(false)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
  const labels = useMemo(() => categoryLabelMap(questions), [questions])

  const candidateColorMap = useMemo(
    () => buildCandidateColorMap(results?.candidates ?? []),
    [results],
  )

  const chartCandidates = useMemo(() => {
    if (!results) return []
    return results.candidates
      .filter((c) => c.compatibility.question_count > 0 || c.compass !== null)
      .map((c) => {
        const key = candidateKey(c.office, c.name)
        return {
          key,
          name: c.name,
          matchPct: c.compatibility.overall_pct,
          color: candidateColorMap.get(key) ?? '#6b7a99',
        }
      })
  }, [results, candidateColorMap])

  const selection = useCandidateSelection(chartCandidates)

  if (resultsStatus === 'idle') {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-2xl mx-auto px-4 py-16">
        <EmptyState
          title="No results yet"
          description="Take the questionnaire first to see how you compare to local candidates."
          action={<button onClick={() => navigate('quiz')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Take the questionnaire</button>}
        />
      </div>
    )
  }

  if (resultsStatus === 'loading') {
    return <div className="min-h-screen bg-soft flex items-center justify-center text-muted text-sm">Researching candidates and computing your results…</div>
  }

  if (resultsStatus === 'error' || !results) {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-2xl mx-auto px-4 py-16">
        <EmptyState
          title="Could not compute your results"
          description={resultsError ?? 'Something went wrong.'}
          action={<button onClick={() => void computeResults()} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Try again</button>}
        />
      </div>
    )
  }

  const rankedCandidates = results.candidates.filter((c) => c.compatibility.question_count > 0)
  const unrankedCandidates = results.candidates.filter((c) => c.compatibility.question_count === 0)

  const radarCategories = Object.keys(results.radar)
  const radarData = radarCategories.map((cat) => {
    const row: Record<string, string | number> = { category: labels[cat] ?? cat, You: Math.round(results.radar[cat]) }
    rankedCandidates.forEach((c) => {
      row[c.name] = Math.round(c.compatibility.by_category[cat] ?? 0)
    })
    return row
  })

  const radarSeriesCandidates = rankedCandidates.map((c) => {
    const key = candidateKey(c.office, c.name)
    return { key, name: c.name, color: candidateColorMap.get(key) ?? '#6b7a99' }
  })

  const compassCandidates = results.candidates
    .filter((c): c is CandidateResult & { compass: { econ: number; social: number } } => c.compass !== null)
    .map((c) => {
      const key = candidateKey(c.office, c.name)
      return { key, name: c.name, econ: c.compass.econ, social: c.compass.social, color: candidateColorMap.get(key) ?? '#6b7a99' }
    })

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-navy">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center gap-2 text-xs text-blue-300/70 mb-4">
            <button onClick={() => navigate('home')} className="hover:text-white">Home</button>
            <span>/</span>
            <button onClick={() => navigate('quiz')} className="hover:text-white">Questionnaire</button>
            <span>/</span>
            <span className="text-white">Results</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 leading-tight" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            Your alignment results
          </h1>
          <p className="text-blue-200/80 max-w-xl text-sm sm:text-base leading-relaxed">
            Based on your questionnaire answers and the candidates found for your ZIP code.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <Alert type="warning">
          <strong>These results are estimates.</strong> Match percentages are based on available evidence only and may be incomplete where candidate positions are uncertain or not yet documented. The highest match is not an endorsement. Use these results alongside your own independent research.
        </Alert>

        <div className="mt-8 grid lg:grid-cols-[1fr_340px] gap-8">
          {/* Left column: match cards */}
          <div className="space-y-5">
            <h2 className="font-semibold text-navy text-lg" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Candidate matches
            </h2>

            {results.candidates.length === 0 && (
              <EmptyState title="No candidates researched yet" description="Search for elections and browse a race to research candidates." />
            )}

            {[...rankedCandidates, ...unrankedCandidates].map((result, i) => (
              <MatchCard
                key={candidateKey(result.office, result.name)}
                result={result}
                rank={i + 1}
                expanded={!!expanded[candidateKey(result.office, result.name)]}
                onToggle={() => toggle(candidateKey(result.office, result.name))}
                categoryLabels={labels}
              />
            ))}

            <div className="bg-surface rounded-2xl border border-border overflow-hidden">
              <button
                onClick={() => setShowMethodology(!showMethodology)}
                className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-soft/50 transition-colors"
              >
                <span className="font-semibold text-navy text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                  How this was calculated
                </span>
                <svg viewBox="0 0 16 16" fill="currentColor" className={`w-4 h-4 text-muted transition-transform ${showMethodology ? 'rotate-180' : ''}`}>
                  <path fillRule="evenodd" clipRule="evenodd" d="M4.22 6.22a.75.75 0 011.06 0L8 8.94l2.72-2.72a.75.75 0 111.06 1.06l-3.25 3.25a.75.75 0 01-1.06 0L4.22 7.28a.75.75 0 010-1.06z"/>
                </svg>
              </button>
              {showMethodology && (
                <div className="px-5 pb-6 border-t border-border space-y-3 text-sm text-navy/70 leading-relaxed">
                  <p className="pt-4">Match percentages compare your questionnaire responses to candidate positions on the same 20 questions, using only questions where both you and the candidate have an answer. Each question is weighted by the importance you selected (Low, Medium, or High).</p>
                  <p>Questions you answered "Not Sure" or skipped are excluded. Candidates with zero overlapping answered questions show no percentage rather than a misleading number.</p>
                  <p>Match estimates are <strong>not predictions of future policy</strong> and do not account for positions not yet publicly documented.</p>
                </div>
              )}
            </div>
          </div>

          {/* Right column: actions */}
          <div className="space-y-2.5">
            <button
              onClick={() => navigate('quiz')}
              className="w-full py-3 rounded-xl border border-border text-muted text-sm font-medium hover:text-navy hover:border-border-strong transition-colors"
            >
              Retake questionnaire
            </button>
            <button
              onClick={() => navigate('elections')}
              className="w-full py-3 rounded-xl bg-navy text-white text-sm font-semibold hover:bg-navy-mid transition-colors"
            >
              Back to all races
            </button>
          </div>
        </div>

        {(rankedCandidates.length > 0 || compassCandidates.length > 0) && (
          <div className="mt-10">
            <h2 className="font-semibold text-navy text-lg mb-1" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Compare candidates visually
            </h2>
            <p className="text-sm text-muted leading-relaxed mb-5 max-w-2xl">
              Choose which candidates to compare below — your selection stays in sync between both charts.
            </p>

            <div className="grid lg:grid-cols-2 gap-6">
              {chartCandidates.length > 0 && (
                <ChartCard title="Issue-by-issue alignment" subtitle="How closely each candidate matches you, by category">
                  {(variant) => (
                    <div className={variant === 'modal' ? 'grid md:grid-cols-[1fr_240px] gap-5 items-start' : 'grid lg:grid-cols-[1fr_220px] gap-4 items-start'}>
                      <IssueRadarChart
                        data={radarData}
                        candidates={radarSeriesCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        onHoverCandidate={selection.setHovered}
                        onTogglePinned={selection.togglePinned}
                        variant={variant}
                      />
                      <CandidateSelector candidates={chartCandidates} selection={selection} />
                    </div>
                  )}
                </ChartCard>
              )}

              {compassCandidates.length > 0 && (
                <ChartCard title="Ideological compass" subtitle="Your estimated position vs. candidates on two axes">
                  {(variant) => (
                    <div className={variant === 'modal' ? 'grid md:grid-cols-[1fr_220px] gap-5 items-start' : 'grid lg:grid-cols-[1fr_200px] gap-4 items-start'}>
                      <IdeologicalCompassChart
                        voter={results.voter_compass}
                        candidates={compassCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        onHoverCandidate={selection.setHovered}
                        onTogglePinned={selection.togglePinned}
                        variant={variant}
                      />
                      <CompassDetailsPanel
                        candidates={compassCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        voter={results.voter_compass}
                      />
                    </div>
                  )}
                </ChartCard>
              )}
            </div>

            <div className="mt-4 max-w-2xl">
              <button
                type="button"
                onClick={() => setShowCompassMethod(!showCompassMethod)}
                className="text-xs text-civic hover:text-civic-light font-medium underline underline-offset-2"
              >
                How compass positions are calculated
              </button>
              {showCompassMethod && (
                <p className="text-xs text-muted leading-relaxed mt-2 max-w-lg">
                  Compass positions are estimated from your and each candidate's answers to the same 20 questions. The horizontal axis reflects economic policy (public investment vs. markets); the vertical axis reflects social governance approach (authority vs. civil liberties). These are not measures of partisan affiliation.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

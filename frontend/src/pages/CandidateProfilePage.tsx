import { useEffect, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData, candidateKey } from '../context/appData'
import { EvidenceBadge, ConfidenceIndicator, PartyLabel, IssueTag, PolicyScaleBar } from '../components/Badges'
import { Avatar } from '../components/Cards'
import { Alert, Disclaimer, SourceCitation, EmptyState, Modal, Tooltip } from '../components/ui'
import { allSourcesFor, confidenceBucket, initialsFor, issueTagsFor, categoryLabelMap } from '../lib/derive'
import type { Office } from '../api'

// ─── Source panel ─────────────────────────────────────────────────────────────

function SourcePanel({ url, title, isOpen, onToggle }: { url: string | null; title: string | null; isOpen: boolean; onToggle: () => void }) {
  if (!url) return null
  return (
    <div className="mt-2.5">
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs text-civic hover:text-civic-light font-medium transition-colors"
      >
        <svg viewBox="0 0 14 14" fill="currentColor" className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-90' : ''}`}>
          <path fillRule="evenodd" clipRule="evenodd" d="M4.22 5.72a.5.5 0 01.7 0L7 7.8l2.08-2.08a.5.5 0 01.7.7l-2.43 2.43a.5.5 0 01-.7 0L4.22 6.42a.5.5 0 010-.7z"/>
        </svg>
        {isOpen ? 'Hide' : 'Show'} source
      </button>

      {isOpen && (
        <div className="mt-2 pl-3 border-l-2 border-border">
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-xs text-civic hover:text-civic-light underline">
            {title || url} ↗
          </a>
        </div>
      )}
    </div>
  )
}

export default function CandidateProfilePage() {
  const { navigate, params } = useNav()
  const { elections, questions, ensureQuestionsLoaded, profiles, raceResearchStatus, raceResearchError, ensureRaceResearched } = useAppData()

  const office = params.office as Office | undefined
  const name = params.name
  const race = elections.races.find((r) => r.office === office)
  const candidate = race?.candidates.find((c) => c.name === name)

  const [openSources, setOpenSources] = useState<Set<string>>(new Set())
  const [activeTab, setActiveTab] = useState<'positions' | 'bio' | 'finance' | 'sources'>('positions')
  const [sourceModalOpen, setSourceModalOpen] = useState(false)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

  useEffect(() => {
    if (office) void ensureRaceResearched(office)
  }, [office, ensureRaceResearched])

  const toggleSource = (id: string) =>
    setOpenSources((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  if (!race || !candidate || !office) {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-5xl mx-auto px-4 sm:px-6 py-16">
        <EmptyState
          title="Candidate not found"
          description="Search for your elections and pick a candidate from a race to view their profile."
          action={<button onClick={() => navigate('elections')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Back to elections</button>}
        />
      </div>
    )
  }

  const profile = profiles[candidateKey(office, candidate.name)]
  const researching = raceResearchStatus[office] === 'loading'
  const researchFailed = raceResearchStatus[office] === 'error'
  const labels = categoryLabelMap(questions)
  const questionById = Object.fromEntries(questions.map((q) => [q.id, q]))
  const allSources = allSourcesFor(profile)

  const TABS = [
    { id: 'positions' as const, label: 'Policy Positions' },
    { id: 'bio' as const, label: 'Biography' },
    { id: 'finance' as const, label: 'Campaign Finance' },
    { id: 'sources' as const, label: 'All Sources' },
  ]

  return (
    <div className="min-h-screen bg-soft page-enter">
      {/* Breadcrumb */}
      <div className="bg-surface border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center gap-2 text-xs text-muted">
            <button onClick={() => navigate('home')} className="hover:text-civic transition-colors">Home</button>
            <span className="text-border">/</span>
            <button onClick={() => navigate('elections')} className="hover:text-civic transition-colors">Elections</button>
            <span className="text-border">/</span>
            <button onClick={() => navigate('race', { office })} className="hover:text-civic transition-colors">{race.office_label}</button>
            <span className="text-border">/</span>
            <span className="text-navy font-medium">{candidate.name}</span>
          </div>
        </div>
      </div>

      {/* Profile header */}
      <div className="bg-navy">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
            <Avatar initials={initialsFor(candidate.name)} index={0} size="lg" />

            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <PartyLabel party={candidate.party} />
                {candidate.incumbent && <span className="text-blue-300 text-xs">· Incumbent</span>}
              </div>
              <h1
                className="text-3xl sm:text-4xl font-bold text-white mb-2 leading-tight"
                style={{ fontFamily: 'Fraunces, Georgia, serif' }}
              >
                {candidate.name}
              </h1>
              <p className="text-blue-200/80 text-sm mb-3">
                Running for {race.office_label} · {race.jurisdiction_name}{race.election_date ? ` · Election: ${race.election_date}` : ''}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {issueTagsFor(profile, labels, 6).map((issue) => <IssueTag key={issue} label={issue} />)}
              </div>
            </div>

            <div className="flex flex-col items-start sm:items-end gap-3 shrink-0">
              <div className="bg-navy-mid rounded-xl px-4 py-3 border border-white/8">
                <p className="text-[10px] text-blue-300/70 uppercase tracking-wide mb-2">Information quality</p>
                <ConfidenceIndicator level={confidenceBucket(profile)} showLabel />
                {profile && (
                  <p className="text-[10px] text-blue-300/50 mt-1.5">
                    {profile.coverage.sourced} of {profile.coverage.total_questions} questions sourced
                  </p>
                )}
              </div>

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setSourceModalOpen(true)}
                  className="px-3.5 py-2 rounded-lg border border-white/20 text-white text-xs font-medium hover:bg-white/10 transition-colors"
                >
                  View Sources
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-surface border-b border-border sticky top-[60px] z-40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex gap-0 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-4 text-sm font-medium whitespace-nowrap border-b-2 transition-all ${
                  activeTab === tab.id
                    ? 'border-civic text-civic'
                    : 'border-transparent text-muted hover:text-navy hover:border-border-strong'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {researchFailed && (
          <div className="mb-6">
            <Alert type="warning">{raceResearchError[office] ?? 'Candidate research failed.'}</Alert>
          </div>
        )}
        <div className="mb-6">
          <Disclaimer>
            Positions on this page come from an automated search and may be incomplete. "Unverified estimate" positions are AI-generated guesses, not sourced evidence. Always verify with official sources.
          </Disclaimer>
        </div>

        {/* ─ Policy Positions ─ */}
        {activeTab === 'positions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-navy text-lg" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>Policy positions</h2>
              <Tooltip content="Hover any evidence badge for an explanation of what it means.">
                <span className="text-xs text-muted border border-border rounded-lg px-3 py-1.5 cursor-default hover:border-border-strong transition-colors">
                  Evidence legend ⓘ
                </span>
              </Tooltip>
            </div>

            {/* Legend */}
            <div className="bg-surface rounded-xl border border-border p-4">
              <p className="text-xs font-medium text-muted uppercase tracking-wide mb-3">Evidence types used on this page</p>
              <div className="flex flex-wrap gap-2">
                {(['explicit', 'strong_inference', 'weak_inference', 'speculative', 'unavailable'] as const).map((type) => (
                  <EvidenceBadge key={type} type={type} size="xs" withTooltip />
                ))}
              </div>
            </div>

            {researching && <p className="text-sm text-muted">Researching this candidate's positions…</p>}

            {!researching && candidate.positions.length > 0 && (
              <div className="bg-surface rounded-xl border border-border p-5">
                <h3 className="font-semibold text-navy text-sm mb-3" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>At a glance</h3>
                <ul className="space-y-3">
                  {candidate.positions.map((pos, i) => (
                    <li key={i} className="text-sm text-navy/75 leading-relaxed border-b border-border/60 last:border-0 pb-3 last:pb-0">
                      {pos.summary}
                      {pos.sources[0] && (
                        <a href={pos.sources[0].url} target="_blank" rel="noopener noreferrer" className="ml-2 text-xs text-civic hover:text-civic-light">
                          Source ↗
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!researching && !profile && (
              <EmptyState title="Research has not been completed yet" description="Take the questionnaire to trigger candidate research for this race." />
            )}

            {!researching && profile && profile.sourced_positions.length === 0 && (
              <EmptyState title="No documented position found" description="No evidence was found on the 20 questionnaire topics for this candidate." />
            )}

            {!researching && profile?.sourced_positions.map((sourced) => {
              const question = questionById[sourced.question_id]
              if (!question) return null
              return (
                <div key={sourced.question_id} className="bg-surface rounded-xl border border-border p-5 transition-shadow hover:shadow-sm">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="font-semibold text-navy text-[15px]" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                      {question.category_label}
                    </h3>
                    <EvidenceBadge type={sourced.confidence} withTooltip />
                  </div>

                  <p className="text-sm text-muted leading-relaxed mb-4">{question.text}</p>
                  <PolicyScaleBar value={sourced.position} label={`${question.approach_1}  vs.  ${question.approach_2}`} />

                  {sourced.confidence === 'speculative' && (
                    <div className="mt-3">
                      <Alert type="warning">
                        <strong>Unverified estimate:</strong> No real evidence was found for this question. This position was estimated by AI and should be verified independently.
                      </Alert>
                    </div>
                  )}

                  <SourcePanel
                    url={sourced.source?.url ?? null}
                    title={sourced.source?.title ?? null}
                    isOpen={openSources.has(sourced.question_id)}
                    onToggle={() => toggleSource(sourced.question_id)}
                  />
                </div>
              )
            })}
          </div>
        )}

        {/* ─ Biography ─ */}
        {activeTab === 'bio' && (
          <div className="space-y-5">
            <EmptyState
              title="Biography not available"
              description="ElectMatch's automated research does not currently produce candidate biographies. Check the candidate's campaign site or official voter guide for background information."
            />
          </div>
        )}

        {/* ─ Campaign Finance ─ */}
        {activeTab === 'finance' && (
          <div className="space-y-5">
            <EmptyState
              title="Campaign finance data not available"
              description="ElectMatch does not currently pull campaign finance filings. Check your county or state elections office for official filings."
            />
          </div>
        )}

        {/* ─ All Sources ─ */}
        {activeTab === 'sources' && (
          <div className="bg-surface rounded-xl border border-border p-6">
            <h2 className="font-semibold text-navy text-lg mb-5" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Complete source list
            </h2>

            {allSources.length === 0 && candidate.positions.every((p) => p.sources.length === 0) ? (
              <p className="text-sm text-muted italic">No sourced references found yet for this candidate.</p>
            ) : (
              <div className="space-y-1">
                {[
                  ...candidate.positions.flatMap((p) => p.sources),
                  ...allSources,
                ].map((source, i) => (
                  <div key={i} className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-navy truncate">{source.title || source.url}</p>
                    </div>
                    <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-xs text-civic hover:text-civic-light font-medium shrink-0">View ↗</a>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sources modal */}
      <Modal open={sourceModalOpen} onClose={() => setSourceModalOpen(false)} title="All Sources" size="lg">
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {[...candidate.positions.flatMap((p) => p.sources), ...allSources].length === 0 ? (
            <p className="text-sm text-muted italic">No sourced references found yet for this candidate.</p>
          ) : (
            [...candidate.positions.flatMap((p) => p.sources), ...allSources].map((source, i) => (
              <SourceCitation key={i} title={source.title || source.url} url={source.url} />
            ))
          )}
        </div>
      </Modal>
    </div>
  )
}

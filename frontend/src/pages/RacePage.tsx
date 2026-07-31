import { useEffect } from 'react'
import { useNav } from '../context/nav'
import { useAppData, candidateKey } from '../context/appData'
import { CandidateCard } from '../components/Cards'
import { Alert, EmptyState } from '../components/ui'
import { categoryLabelMap, confidenceBucket, initialsFor, issueTagsFor } from '../lib/derive'
import type { Office } from '../api'

export default function RacePage() {
  const { navigate, params } = useNav()
  const { elections, questions, ensureQuestionsLoaded, profiles, raceResearchStatus, raceResearchError, ensureRaceResearched, comparisonKeys, toggleComparison } = useAppData()

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
          title="Race not found"
          description="Search for your elections first to browse a specific race."
          action={<button onClick={() => navigate('elections')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Back to elections</button>}
        />
      </div>
    )
  }

  const labels = categoryLabelMap(questions)
  const researching = raceResearchStatus[race.office] === 'loading'
  const researchFailed = raceResearchStatus[race.office] === 'error'
  const selectedKeys = comparisonKeys.filter((k) => k.startsWith(`${race.office}::`))

  return (
    <div className="min-h-screen bg-soft page-enter">
      {/* Header */}
      <div className="bg-surface border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center gap-2 text-xs text-muted mb-3">
            <button onClick={() => navigate('home')} className="hover:text-civic transition-colors">Home</button>
            <span className="text-border">/</span>
            <button onClick={() => navigate('elections')} className="hover:text-civic transition-colors">Elections</button>
            <span className="text-border">/</span>
            <span className="text-navy font-medium">{race.office_label}</span>
          </div>

          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">
            <div>
              <h1 className="text-2xl font-bold text-navy mb-1.5" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                {race.office_label}
              </h1>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
                <span>{race.jurisdiction_name}</span>
                <span className="text-border">·</span>
                <span className="inline-flex items-center gap-1.5">
                  <svg viewBox="0 0 14 14" fill="currentColor" className="w-3.5 h-3.5 text-civic-light">
                    <path fillRule="evenodd" clipRule="evenodd" d="M2 2a1 1 0 011-1h8a1 1 0 011 1v1h1a1 1 0 011 1v8a1 1 0 01-1 1H1a1 1 0 01-1-1V4a1 1 0 011-1h1V2zm8 2H4v7h6V4z"/>
                  </svg>
                  {race.election_date ?? 'Election date unknown'}
                </span>
                <span className="text-border">·</span>
                <span className="text-xs font-mono font-medium text-civic bg-civic-pale px-2 py-0.5 rounded-lg border border-civic/20">
                  {race.candidates.length} candidate{race.candidates.length === 1 ? '' : 's'}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2.5">
              {selectedKeys.length >= 2 && (
                <button
                  onClick={() => navigate('comparison', { office: race.office })}
                  className="px-4 py-2.5 rounded-xl bg-navy text-white text-sm font-semibold hover:bg-navy-mid transition-colors"
                >
                  Compare {selectedKeys.length} →
                </button>
              )}
              <button
                onClick={() => navigate('quiz')}
                className="px-4 py-2.5 rounded-xl bg-teal text-white text-sm font-semibold hover:bg-teal-hover transition-colors"
              >
                Take the Quiz
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {researchFailed && (
          <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-800">
            {raceResearchError[race.office] ?? 'Candidate research failed.'}
          </div>
        )}

        {researching && (
          <div className="mb-6">
            <Alert type="info">
              Researching {race.candidates.length} candidate{race.candidates.length === 1 ? '' : 's'}' positions — this typically takes 30–60 seconds for races with several candidates. Feel free to keep browsing; each card fills in automatically.
            </Alert>
          </div>
        )}

        {/* Compare banner */}
        {selectedKeys.length > 0 && (
          <div className="mb-6 p-4 rounded-xl bg-navy/5 border border-navy/15 flex items-center justify-between gap-4">
            <div className="text-sm">
              <span className="font-semibold text-navy">{selectedKeys.length} candidate{selectedKeys.length > 1 ? 's' : ''} selected</span>
              <span className="text-muted ml-2 text-xs">(max 4 — need at least 2 to compare)</span>
            </div>
            {selectedKeys.length >= 2 && (
              <button
                onClick={() => navigate('comparison', { office: race.office })}
                className="px-3.5 py-1.5 rounded-lg bg-civic text-white text-xs font-semibold hover:bg-civic-hover transition-colors"
              >
                Compare →
              </button>
            )}
          </div>
        )}

        {/* Candidates -- always shown immediately (names/party come back with the
            race search itself); only the research-dependent parts (issue tags,
            confidence, at-a-glance summary) wait on the slower per-candidate
            policy lookup, which runs in the background. */}
        {race.candidates.length === 0 ? (
          <EmptyState title="No candidates found" description="No candidates were identified for this race." />
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {race.candidates.map((candidate, idx) => {
              const key = candidateKey(race.office, candidate.name)
              const profile = profiles[key]
              return (
                <CandidateCard
                  key={candidate.name}
                  name={candidate.name}
                  party={candidate.party}
                  photoInitials={initialsFor(candidate.name)}
                  issueTags={issueTagsFor(profile, labels)}
                  confidenceLevel={confidenceBucket(profile)}
                  summary={candidate.positions[0]?.summary ?? null}
                  researching={researching && !profile}
                  index={idx}
                  onViewProfile={() => navigate('candidate', { office: race.office, name: candidate.name })}
                  selected={comparisonKeys.includes(key)}
                  onToggleCompare={() => toggleComparison(race.office, candidate.name)}
                  showCompare
                />
              )
            })}
          </div>
        )}

        {/* Quiz CTA */}
        <div className="mt-12 bg-navy rounded-2xl p-8 text-center">
          <h2 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            Not sure who aligns with your priorities?
          </h2>
          <p className="text-blue-200/80 text-sm mb-5 max-w-lg mx-auto">
            Take the 20-question questionnaire to see your estimated alignment with each candidate. Results include confidence levels and are clearly labeled as estimates — not predictions or endorsements.
          </p>
          <button
            onClick={() => navigate('quiz')}
            className="px-6 py-3 rounded-xl bg-teal text-white font-semibold hover:bg-teal-hover transition-colors"
          >
            Take the Questionnaire
          </button>
        </div>
      </div>
    </div>
  )
}

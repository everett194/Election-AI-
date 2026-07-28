import { useMemo, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData } from '../context/appData'
import { RaceCard, RaceCardSkeleton } from '../components/Cards'
import { EmptyState, ErrorState } from '../components/ui'

export default function ElectionResultsPage() {
  const { navigate } = useNav()
  const { elections, searchElections } = useAppData()
  const [search, setSearch] = useState('')
  const [filterJurisdiction, setFilterJurisdiction] = useState('all')

  const jurisdictions = useMemo(
    () => ['all', ...Array.from(new Set(elections.races.map((r) => r.jurisdiction_name)))],
    [elections.races],
  )

  const filteredRaces = elections.races.filter((race) => {
    const matchSearch = !search ||
      race.office_label.toLowerCase().includes(search.toLowerCase()) ||
      race.jurisdiction_name.toLowerCase().includes(search.toLowerCase())
    const matchJurisdiction = filterJurisdiction === 'all' || race.jurisdiction_name === filterJurisdiction
    return matchSearch && matchJurisdiction
  })

  const racesWithCandidates = filteredRaces.filter((r) => r.candidates.length > 0)

  return (
    <div className="min-h-screen bg-soft page-enter">
      {/* Page header */}
      <div className="bg-surface border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center gap-2 text-xs text-muted mb-3">
            <button onClick={() => navigate('home')} className="hover:text-civic transition-colors">Home</button>
            <span className="text-border">/</span>
            <span className="text-navy font-medium">Elections</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-navy mb-1.5" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                {elections.zipcode ? `Elections for ${elections.zipcode}` : 'Elections'}
              </h1>
              {elections.retrievedAt && (
                <p className="text-sm text-muted">
                  Retrieved {new Date(elections.retrievedAt).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {elections.status === 'loaded' && elections.races.length > 0 && (
        <div className="bg-surface border-b border-border sticky top-[60px] z-30">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3">
            <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center">
              <div className="relative flex-1 max-w-sm">
                <svg viewBox="0 0 18 18" fill="currentColor" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none">
                  <path fillRule="evenodd" clipRule="evenodd" d="M7 2a5 5 0 100 10A5 5 0 007 2zm-7 5a7 7 0 1112.6 4.2l4.1 4.1a1 1 0 01-1.4 1.4L11.2 12.6A7 7 0 010 7z"/>
                </svg>
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search races or offices…"
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-border text-sm bg-soft text-navy placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-civic focus:border-transparent transition-all"
                />
              </div>

              <select
                value={filterJurisdiction}
                onChange={(e) => setFilterJurisdiction(e.target.value)}
                className="py-2.5 px-3.5 pr-8 rounded-xl border border-border text-sm bg-soft text-navy focus:outline-none focus:ring-2 focus:ring-civic transition-all appearance-none"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%236b7a99'%3E%3Cpath fill-rule='evenodd' d='M4.22 6.22a.75.75 0 011.06 0L8 8.94l2.72-2.72a.75.75 0 111.06 1.06l-3.25 3.25a.75.75 0 01-1.06 0L4.22 7.28a.75.75 0 010-1.06z'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
              >
                {jurisdictions.map((j) => (
                  <option key={j} value={j}>{j === 'all' ? 'All jurisdictions' : j}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {elections.status === 'idle' && (
          <EmptyState
            title="Search for your elections"
            description="Enter a ZIP code on the home page to see local races."
            action={<button onClick={() => navigate('home')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Go to search</button>}
          />
        )}

        {elections.status === 'loading' && (
          <div className="grid md:grid-cols-2 gap-5">
            {[1, 2, 3].map((i) => <RaceCardSkeleton key={i} />)}
          </div>
        )}

        {elections.status === 'error' && (
          <ErrorState
            title="Election data temporarily unavailable"
            description={elections.error ?? 'We were unable to load election information right now. Please try again.'}
            onRetry={() => void searchElections(elections.zipcode)}
          />
        )}

        {elections.status === 'loaded' && racesWithCandidates.length === 0 && filteredRaces.length > 0 && (
          <EmptyState
            title="No candidates found"
            description="Races were found for this ZIP code, but no candidates could be identified for them yet. See notes below."
          />
        )}

        {elections.status === 'loaded' && filteredRaces.length === 0 && elections.races.length > 0 && (
          <EmptyState
            title="No races match your search"
            description="Try different search terms or clear your filters."
            action={<button className="text-sm text-civic underline" onClick={() => { setSearch(''); setFilterJurisdiction('all') }}>Clear all filters</button>}
          />
        )}

        {elections.status === 'loaded' && elections.races.length === 0 && (
          <EmptyState
            title="No upcoming elections found"
            description="We couldn't find any local races for that ZIP code. Try a different ZIP code."
            action={<button onClick={() => navigate('home')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Try another ZIP code</button>}
          />
        )}

        {elections.status === 'loaded' && filteredRaces.length > 0 && (
          <>
            <div className="space-y-10">
              {jurisdictions.filter((j) => j !== 'all').map((jur) => {
                const races = filteredRaces.filter((r) => r.jurisdiction_name === jur)
                if (!races.length) return null
                return (
                  <div key={jur}>
                    <div className="flex items-center gap-3 mb-5">
                      <h2 className="text-xs font-mono font-semibold text-muted uppercase tracking-widest whitespace-nowrap">{jur}</h2>
                      <div className="flex-1 h-px bg-border" />
                      <span className="text-xs text-muted font-mono shrink-0">{races.length} {races.length === 1 ? 'race' : 'races'}</span>
                    </div>
                    <div className="grid md:grid-cols-2 gap-5">
                      {races.map((race) => (
                        <RaceCard
                          key={race.office}
                          officeLabel={race.office_label}
                          jurisdictionName={race.jurisdiction_name}
                          electionDate={race.election_date}
                          candidateCount={race.candidates.length}
                          notes={race.notes}
                          onViewCandidates={() => navigate('race', { office: race.office })}
                          onTakeQuiz={() => navigate('quiz')}
                        />
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="mt-10 pt-6 border-t border-border text-xs text-muted flex items-start gap-2.5">
              <svg viewBox="0 0 14 14" fill="currentColor" className="w-4 h-4 shrink-0 text-civic-light mt-0.5">
                <path fillRule="evenodd" clipRule="evenodd" d="M7 1a6 6 0 100 12A6 6 0 007 1zm-.75 3.25a.75.75 0 011.5 0v3a.75.75 0 01-1.5 0v-3zm.75 5.5a.75.75 0 100-1.5.75.75 0 000 1.5z"/>
              </svg>
              <p>Race information comes from an automated search and is not guaranteed complete or error-free. Candidate counts and election dates may change before filing deadlines. Always verify with your local election authority.</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

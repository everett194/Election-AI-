import { useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData } from '../context/appData'

// ─── Dashboard preview illustration ──────────────────────────────────────────
// Purely illustrative UI chrome -- deliberately generic (no candidate names,
// no percentages) so it can't be mistaken for real data.

function DashboardPreview() {
  return (
    <div className="relative rounded-2xl overflow-hidden shadow-[0_24px_64px_rgba(15,35,64,0.35)] border border-white/10 max-w-[480px] mx-auto">
      {/* Browser chrome */}
      <div className="bg-[#0a1e36] px-4 py-2.5 flex items-center gap-2">
        <div className="flex gap-1.5">
          {['#FF5F57','#FEBC2E','#28C840'].map((c) => (
            <div key={c} className="w-3 h-3 rounded-full" style={{ backgroundColor: c, opacity: 0.7 }} />
          ))}
        </div>
        <div className="flex-1 mx-3 h-5 bg-navy/60 rounded-md flex items-center px-2 gap-1.5">
          <svg viewBox="0 0 12 12" fill="currentColor" className="w-2.5 h-2.5 text-blue-300/40">
            <path fillRule="evenodd" clipRule="evenodd" d="M6 1a5 5 0 100 10A5 5 0 006 1zm-.5 3a.5.5 0 011 0v1.5H8a.5.5 0 010 1H5.5V4z"/>
          </svg>
          <span className="text-[9px] text-blue-300/50 font-mono">votelocal.org/elections</span>
        </div>
      </div>

      {/* App shell */}
      <div className="bg-[#f4f6f8] p-3 space-y-2">
        <div className="bg-[#0f2340] rounded-lg px-3 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-[#2d5fa0] rounded-sm" />
            <span className="text-white text-[10px] font-bold" style={{ fontFamily: 'Fraunces, serif' }}>VoteLocal</span>
          </div>
          <div className="flex gap-2 text-[9px] text-blue-300/70">
            <span>Elections</span><span>Candidates</span>
          </div>
          <div className="bg-[#1a9e87] text-white text-[9px] font-medium px-2 py-0.5 rounded-md">Take Quiz</div>
        </div>

        <div className="bg-white rounded-xl px-3 py-2.5 border border-[#dde3ed] flex items-center gap-2 shadow-sm">
          <svg viewBox="0 0 14 14" fill="currentColor" className="w-3.5 h-3.5 text-[#2d5fa0] shrink-0">
            <path fillRule="evenodd" clipRule="evenodd" d="M7 1a5 5 0 100 10A5 5 0 007 1zm2.5 4.5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/>
          </svg>
          <span className="text-[10px] text-[#6b7a99] flex-1">Your ZIP code</span>
          <span className="text-[9px] bg-[#1a9e87]/15 text-[#1a9e87] px-2 py-0.5 rounded font-semibold">races found</span>
        </div>

        {[
          { title: 'City Council race', accent: '#2d5fa0' },
          { title: 'School Board race', accent: '#2d5fa0' },
        ].map((r, i) => (
          <div key={i} className="bg-white rounded-xl border border-[#dde3ed] p-3 shadow-sm">
            <div className="flex items-center justify-between mb-1">
              <div>
                <p className="text-[10px] font-semibold text-[#0f2340]">{r.title}</p>
                <p className="text-[9px] text-[#6b7a99]">Election date &amp; candidate count</p>
              </div>
              <div className="flex gap-1">
                <div className="px-2 py-1 rounded-lg bg-[#2d5fa0] text-white text-[8px] font-semibold">View</div>
                <div className="px-2 py-1 rounded-lg border border-[#2d5fa0] text-[#2d5fa0] text-[8px] font-semibold">Quiz</div>
              </div>
            </div>
          </div>
        ))}

        <div className="bg-[#e4f5f1] rounded-xl border border-[#1a9e87]/20 p-3 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#0f2340] flex items-center justify-center text-white text-[10px] font-bold shrink-0" style={{ fontFamily: 'Fraunces, serif' }}>?</div>
          <div className="flex-1 min-w-0">
            <p className="text-[9px] font-semibold text-[#1a9e87]">Your closest estimated alignment</p>
            <p className="text-[8px] text-[#1a9e87]/70">Shown after you take the questionnaire</p>
            <div className="mt-1 h-1.5 bg-white/50 rounded-full overflow-hidden">
              <div className="h-full bg-[#1a9e87] rounded-full" style={{ width: '60%' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Supporting components ────────────────────────────────────────────────────

function TrustPill({ text, icon }: { text: string; icon: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-white/8 border border-white/12 text-sm text-blue-100">
      <span className="text-teal">{icon}</span>
      {text}
    </div>
  )
}

function StepCard({ n, title, desc, active }: { n: number; title: string; desc: string; active?: boolean }) {
  return (
    <div className={`relative p-6 rounded-2xl border transition-shadow ${active ? 'bg-surface border-civic/30 shadow-lg shadow-civic/8' : 'bg-surface border-border hover:shadow-md'}`}>
      {active && <div className="absolute top-0 left-6 right-6 h-0.5 bg-civic rounded-b" />}
      <div className="w-10 h-10 rounded-xl bg-civic-pale border border-civic/20 flex items-center justify-center mb-4">
        <span className="text-civic font-bold text-sm font-mono">{n}</span>
      </div>
      <h3 className="font-semibold text-navy text-base mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{title}</h3>
      <p className="text-sm text-muted leading-relaxed">{desc}</p>
    </div>
  )
}

function FeatureCard({ icon, title, desc, cta, onClick }: {
  icon: React.ReactNode
  title: string
  desc: string
  cta: string
  onClick: () => void
}) {
  return (
    <div className="group bg-surface rounded-2xl border border-border p-6 hover:border-civic/30 hover:shadow-lg hover:shadow-civic/8 transition-all duration-200">
      <div className="w-11 h-11 rounded-xl bg-civic-pale border border-civic/20 flex items-center justify-center mb-4 text-civic group-hover:bg-civic group-hover:text-white group-hover:border-civic transition-all duration-200">
        {icon}
      </div>
      <h3 className="font-semibold text-navy text-[15px] mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{title}</h3>
      <p className="text-sm text-muted leading-relaxed mb-4">{desc}</p>
      <button
        onClick={onClick}
        className="text-sm text-civic font-medium hover:text-civic-light transition-colors flex items-center gap-1.5"
      >
        {cta}
        <span className="group-hover:translate-x-0.5 transition-transform">→</span>
      </button>
    </div>
  )
}

// ─── HomePage ─────────────────────────────────────────────────────────────────

const ZIP_PATTERN = /^\d{5}$/

export default function HomePage() {
  const { navigate } = useNav()
  const { searchElections } = useAppData()
  const [zipcode, setZipcode] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = zipcode.trim()
    if (!ZIP_PATTERN.test(trimmed)) {
      setError('Enter a valid 5-digit ZIP code.')
      return
    }
    setError(null)
    void searchElections(trimmed)
    navigate('elections')
  }

  return (
    <div className="min-h-screen bg-soft page-enter">
      {/* ── Hero ────────────────────────────────────────────── */}
      <section className="relative bg-navy overflow-hidden">
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 40px, white 40px, white 41px), repeating-linear-gradient(90deg, transparent, transparent 40px, white 40px, white 41px)',
        }} />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-24">
          <div className="grid lg:grid-cols-[1fr_480px] gap-14 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal/15 border border-teal/30 text-teal text-xs font-medium mb-7">
                <span className="w-1.5 h-1.5 rounded-full bg-teal" />
                Nonpartisan · Source-based · Free to use
              </div>

              <h1
                className="text-4xl sm:text-5xl lg:text-[3.4rem] font-bold text-white leading-[1.1] mb-5 tracking-tight"
                style={{ fontFamily: 'Fraunces, Georgia, serif' }}
              >
                Know who represents<br />
                <span className="text-teal">your community.</span>
              </h1>

              <p className="text-lg text-blue-200/85 leading-relaxed mb-8 max-w-lg">
                Find your local candidates, compare their positions, and see who most closely aligns with your priorities.
              </p>

              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2.5 max-w-[480px] mb-2">
                <div className="relative flex-1">
                  <svg viewBox="0 0 20 20" fill="currentColor" className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-300/50 pointer-events-none">
                    <path fillRule="evenodd" clipRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 14.988 17 12.493 17 9A7 7 0 103 9c0 3.492 1.698 5.988 3.355 7.584a13.731 13.731 0 002.273 1.765 11.842 11.842 0 00.976.544l.062.029zM10 11.25a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5z"/>
                  </svg>
                  <input
                    type="text"
                    value={zipcode}
                    onChange={(e) => setZipcode(e.target.value)}
                    placeholder="ZIP code"
                    inputMode="numeric"
                    maxLength={5}
                    className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-white/10 border border-white/15 text-white placeholder:text-blue-300/50 text-sm focus:outline-none focus:ring-2 focus:ring-teal focus:bg-white/15 transition-all"
                  />
                </div>
                <button
                  type="submit"
                  className="px-5 py-3.5 rounded-xl bg-civic text-white font-semibold text-sm hover:bg-civic-hover transition-colors whitespace-nowrap shadow-lg shadow-civic/25"
                >
                  Find My Elections
                </button>
              </form>
              {error && <p className="text-sm text-red-300 mb-6">{error}</p>}

              <div className="mt-8 pt-8 border-t border-white/10 flex flex-wrap gap-2.5">
                {[
                  { text: 'Nonpartisan', icon: <svg viewBox="0 0 12 12" fill="currentColor" className="w-3 h-3"><path fillRule="evenodd" clipRule="evenodd" d="M10.78 3.22a.75.75 0 010 1.06l-6 5.25a.75.75 0 01-1-.06L1.22 6.28a.75.75 0 011.06-1.06l2.22 2.22 5.22-4.5a.75.75 0 011.06.28z"/></svg> },
                  { text: 'Source-based', icon: <svg viewBox="0 0 12 12" fill="currentColor" className="w-3 h-3"><path d="M3 2.5A.5.5 0 013.5 2h5a.5.5 0 010 1H8v1.5h1.5A1.5 1.5 0 0111 6v4a1 1 0 01-1 1H2a1 1 0 01-1-1V6a1.5 1.5 0 011.5-1.5H4V3H3.5a.5.5 0 01-.5-.5z"/></svg> },
                  { text: 'Local-election focused', icon: <svg viewBox="0 0 12 12" fill="currentColor" className="w-3 h-3"><path fillRule="evenodd" clipRule="evenodd" d="M6 1a4 4 0 100 8A4 4 0 006 1zm0 6a2 2 0 100-4 2 2 0 000 4zm0 2a7 7 0 00-5.88 3.19.5.5 0 00.84.54A6 6 0 0111.04 12.6a.5.5 0 00.84-.53A7 7 0 006 9z"/></svg> },
                  { text: 'Transparent about uncertainty', icon: <svg viewBox="0 0 12 12" fill="currentColor" className="w-3 h-3"><path fillRule="evenodd" clipRule="evenodd" d="M6 1a5 5 0 100 10A5 5 0 006 1zm-.5 3.5a.5.5 0 011 0v2a.5.5 0 01-1 0v-2zm.5 4.5a.5.5 0 100-1 .5.5 0 000 1z"/></svg> },
                ].map(({ text, icon }) => (
                  <TrustPill key={text} text={text} icon={icon} />
                ))}
              </div>
            </div>

            <div className="hidden lg:flex items-center justify-end">
              <DashboardPreview />
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────── */}
      <section className="py-20 px-4 bg-surface border-b border-border">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-xs font-mono font-medium text-civic uppercase tracking-widest mb-3">How It Works</p>
            <h2 className="text-3xl font-bold text-navy" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Three steps to informed local voting
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            <StepCard n={1} title="Enter your location" desc="Type your ZIP code. We'll search for every local race on your ballot -- city council, school board, county offices, and more." active />
            <StepCard n={2} title="Explore local races" desc="Read what public sources say about each candidate's positions, with clear evidence labels and source links wherever we found real evidence." />
            <StepCard n={3} title="Compare your views" desc="Take the questionnaire to see which candidates most closely align with your priorities. Results include confidence levels and are clearly labeled as estimates." />
          </div>
        </div>
      </section>

      {/* ── Feature grid ──────────────────────────────────────── */}
      <section className="py-20 px-4 bg-soft">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-xs font-mono font-medium text-civic uppercase tracking-widest mb-3">Research Tools</p>
            <h2 className="text-3xl font-bold text-navy" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Built for local elections
            </h2>
            <p className="text-muted mt-3 max-w-xl mx-auto text-sm leading-relaxed">
              Everything you need to research your ballot -- in one nonpartisan, source-cited platform.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path fillRule="evenodd" clipRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"/></svg>,
                title: 'Upcoming Races',
                desc: 'See every race on your ballot with election dates and candidate counts, straight from an automated search.',
                cta: 'Find elections', page: 'elections' as const,
              },
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path fillRule="evenodd" clipRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/></svg>,
                title: 'Candidate Profiles',
                desc: 'Policy positions with source citations and evidence quality labels -- explicit, inferred, or unavailable.',
                cta: 'Search elections first', page: 'elections' as const,
              },
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path d="M8 5a1 1 0 100 2h5.586l-1.293 1.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L13.586 5H8zm-5 5a1 1 0 100-2H2.414l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L2.414 10H3z"/></svg>,
                title: 'Side-by-Side Comparison',
                desc: 'Compare up to four candidates on housing, safety, taxes, education, and more in a clear visual format.',
                cta: 'Search elections first', page: 'elections' as const,
              },
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path fillRule="evenodd" clipRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"/></svg>,
                title: 'Values Questionnaire',
                desc: '20 questions across 7 issue areas, framed as a choice between two approaches. Rate importance and see your estimated alignment.',
                cta: 'Take the quiz', page: 'quiz' as const,
              },
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path fillRule="evenodd" clipRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"/></svg>,
                title: 'Match Dashboard',
                desc: 'See alignment as an estimated percentage, with full issue breakdowns, radar charts, and transparent methodology.',
                cta: 'Take the quiz', page: 'quiz' as const,
              },
              {
                icon: <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5"><path fillRule="evenodd" clipRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"/></svg>,
                title: 'Source Transparency',
                desc: 'Every position is labeled: explicit evidence, strong inference, weak inference, unverified estimate, or unavailable.',
                cta: 'Learn more', page: 'home' as const,
              },
            ].map((feature) => (
              <FeatureCard
                key={feature.title}
                icon={feature.icon}
                title={feature.title}
                desc={feature.desc}
                cta={feature.cta}
                onClick={() => navigate(feature.page)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── Preview strip ──────────────────────────────────────── */}
      <section className="py-16 px-4 bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { stat: '7', label: 'Issue categories', sublabel: 'per questionnaire' },
            { stat: '20', label: 'Quiz questions', sublabel: 'across all issues' },
            { stat: '5', label: 'Confidence levels', sublabel: 'clearly labeled' },
            { stat: '100%', label: 'Nonpartisan', sublabel: 'no endorsements' },
          ].map((item) => (
            <div key={item.label} className="text-center">
              <p className="text-4xl font-bold text-navy mb-1 font-mono" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{item.stat}</p>
              <p className="text-sm font-medium text-navy">{item.label}</p>
              <p className="text-xs text-muted">{item.sublabel}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────── */}
      <section className="bg-navy py-16 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-3" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            Ready to explore your local races?
          </h2>
          <p className="text-blue-200/80 mb-8 leading-relaxed">
            Enter your ZIP code and find every candidate on your ballot -- sourced, nonpartisan, and free.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => navigate('home')}
              className="px-6 py-3 rounded-xl bg-civic text-white font-semibold hover:bg-civic-hover transition-colors"
            >
              Back to search
            </button>
            <button
              onClick={() => navigate('quiz')}
              className="px-6 py-3 rounded-xl bg-teal text-white font-semibold hover:bg-teal-hover transition-colors"
            >
              Take the Questionnaire
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

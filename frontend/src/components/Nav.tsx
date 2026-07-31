import { useState, useEffect } from 'react'
import { useNav } from '../context/nav'
import type { PageName } from '../types'

const NAV_LINKS: { label: string; page: PageName }[] = [
  { label: 'Find Elections', page: 'elections' },
  { label: 'Candidates', page: 'race' },
  { label: 'How It Works', page: 'home' },
  { label: 'Methodology', page: 'home' },
  { label: 'About', page: 'home' },
]

export default function Nav() {
  const { page, navigate } = useNav()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Close mobile menu on page change
  useEffect(() => setMobileOpen(false), [page])

  return (
    <nav className={`bg-navy sticky top-0 z-50 transition-shadow duration-200 ${scrolled ? 'shadow-lg shadow-navy/20' : ''}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-[60px]">
          {/* Logo */}
          <button
            onClick={() => navigate('home')}
            className="flex items-center gap-2.5 group flex-shrink-0"
            aria-label="ElectMatch home"
          >
            {/* Hexagon civic mark */}
            <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
              <polygon
                points="14,2 25,8 25,20 14,26 3,20 3,8"
                fill="#2d5fa0"
                stroke="#4a7ec9"
                strokeWidth="1"
              />
              <path d="M9 14l3 3 7-7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span
              className="text-white font-bold text-[1.05rem] tracking-tight leading-none"
              style={{ fontFamily: 'Fraunces, Georgia, serif' }}
            >
              ElectMatch
            </span>
          </button>

          {/* Desktop nav links */}
          <div className="hidden lg:flex items-center gap-0.5 mx-6 flex-1 justify-center">
            {NAV_LINKS.map((link) => (
              <button
                key={link.label}
                onClick={() => navigate(link.page)}
                className={`px-3 py-2 rounded-lg text-[13px] font-medium transition-colors whitespace-nowrap ${
                  page === link.page
                    ? 'text-white bg-white/10'
                    : 'text-blue-200/80 hover:text-white hover:bg-white/8'
                }`}
              >
                {link.label}
              </button>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2.5 flex-shrink-0">
            {/* Take the Quiz CTA */}
            <button
              onClick={() => navigate('quiz')}
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal text-white text-[13px] font-semibold hover:bg-teal-hover active:bg-teal-hover transition-colors"
            >
              <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
                <path d="M7.25 2.5a.75.75 0 01.75-.75h5.5a.75.75 0 010 1.5H8a.75.75 0 01-.75-.75zm0 5a.75.75 0 01.75-.75h5.5a.75.75 0 010 1.5H8a.75.75 0 01-.75-.75zm0 5a.75.75 0 01.75-.75h5.5a.75.75 0 010 1.5H8a.75.75 0 01-.75-.75zM3 2.75a.75.75 0 100 1.5.75.75 0 000-1.5zm-.75 5.75a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3 12.25a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
              </svg>
              Take the Quiz
            </button>

            {/* Mobile hamburger */}
            <button
              className="lg:hidden text-blue-200 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                {mobileOpen
                  ? <path fillRule="evenodd" clipRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>
                  : <path fillRule="evenodd" clipRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"/>
                }
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile drawer */}
        {mobileOpen && (
          <div className="lg:hidden border-t border-white/8 py-3 space-y-0.5">
            {NAV_LINKS.map((link) => (
              <button
                key={link.label}
                onClick={() => navigate(link.page)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  page === link.page
                    ? 'text-white bg-white/10'
                    : 'text-blue-200/80 hover:text-white hover:bg-white/8'
                }`}
              >
                {link.label}
              </button>
            ))}
            <div className="pt-2 pb-1 px-1">
              <button
                onClick={() => navigate('quiz')}
                className="w-full py-2.5 rounded-lg bg-teal text-white text-sm font-semibold hover:bg-teal-hover transition-colors"
              >
                Take the Quiz
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}

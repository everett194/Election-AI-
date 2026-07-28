import { useNav } from '../context/nav'
import type { PageName } from '../types'

interface FooterLink { label: string; page: PageName }

const FOOTER_LINKS: { heading: string; links: FooterLink[] }[] = [
  {
    heading: 'Platform',
    links: [
      { label: 'Find Elections', page: 'elections' },
      { label: 'Candidates', page: 'race' },
      { label: 'Compare', page: 'comparison' },
      { label: 'Take the Quiz', page: 'quiz' },
    ],
  },
  {
    heading: 'About',
    links: [
      { label: 'How It Works', page: 'home' },
      { label: 'Methodology', page: 'home' },
      { label: 'Data Sources', page: 'home' },
      { label: 'About Us', page: 'home' },
    ],
  },
  {
    heading: 'Policies',
    links: [
      { label: 'Editorial Guidelines', page: 'home' },
      { label: 'Privacy Policy', page: 'home' },
      { label: 'Terms of Use', page: 'home' },
      { label: 'Contact', page: 'home' },
    ],
  },
]

export default function Footer() {
  const { navigate } = useNav()
  return (
    <footer className="bg-navy-dark text-blue-200/70 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-10">
          {/* Brand */}
          <div>
            <button
              onClick={() => navigate('home')}
              className="flex items-center gap-2.5 mb-4"
            >
              <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7">
                <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" fill="#2d5fa0" stroke="#4a7ec9" strokeWidth="1"/>
                <path d="M9 14l3 3 7-7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span className="text-white font-bold text-[1.05rem]" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>VoteLocal</span>
            </button>
            <p className="text-sm leading-relaxed text-blue-200/60">
              Nonpartisan civic-technology for local elections. Helping you understand who represents your community.
            </p>
          </div>

          {/* Nav groups */}
          {FOOTER_LINKS.map((group) => (
            <div key={group.heading}>
              <p className="text-white font-semibold text-sm mb-4">{group.heading}</p>
              <ul className="space-y-2.5">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <button
                      onClick={() => navigate(link.page)}
                      className="text-sm text-blue-200/60 hover:text-white transition-colors"
                    >
                      {link.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-white/8 pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-xs text-blue-200/40 max-w-xl leading-relaxed">
            © 2025 VoteLocal · Candidate information comes from an automated public web search and is not guaranteed
            complete or error-free. VoteLocal does not endorse any candidate or party.
          </p>
          <div className="flex gap-2 shrink-0">
            {[
              { label: 'Nonpartisan', color: 'text-teal bg-teal/10 border-teal/20' },
              { label: 'Source-based', color: 'text-blue-300 bg-blue-300/10 border-blue-300/20' },
            ].map(({ label, color }) => (
              <span key={label} className={`text-xs px-3 py-1 rounded-full border font-medium ${color}`}>
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}

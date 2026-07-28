import { useState } from 'react'
import { NavContext } from './context/nav'
import { AppDataProvider } from './context/appData'
import type { PageName } from './types'
import Nav from './components/Nav'
import Footer from './components/Footer'
import HomePage from './pages/HomePage'
import ElectionResultsPage from './pages/ElectionResultsPage'
import RacePage from './pages/RacePage'
import CandidateProfilePage from './pages/CandidateProfilePage'
import ComparisonPage from './pages/ComparisonPage'
import QuestionnairePage from './pages/QuestionnairePage'
import ResultsDashboardPage from './pages/ResultsDashboardPage'

const PAGE_COMPONENTS: Record<PageName, React.ComponentType> = {
  home: HomePage,
  elections: ElectionResultsPage,
  race: RacePage,
  candidate: CandidateProfilePage,
  comparison: ComparisonPage,
  quiz: QuestionnairePage,
  results: ResultsDashboardPage,
}

// Pages that don't show the main footer (quiz is full-screen)
const HIDE_FOOTER: PageName[] = []

export default function App() {
  const [page, setPage] = useState<PageName>('home')
  const [params, setParams] = useState<Record<string, string>>({})

  const navigate = (newPage: PageName, newParams?: Record<string, string>) => {
    setPage(newPage)
    setParams(newParams ?? {})
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const PageComponent = PAGE_COMPONENTS[page]

  return (
    <NavContext.Provider value={{ page, navigate, params }}>
      <AppDataProvider>
        <div className="flex flex-col min-h-screen bg-soft">
          <Nav />
          <main className="flex-1">
            <PageComponent />
          </main>
          {!HIDE_FOOTER.includes(page) && <Footer />}
        </div>
      </AppDataProvider>
    </NavContext.Provider>
  )
}

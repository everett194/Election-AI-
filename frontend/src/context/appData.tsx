/**
 * Shared application data + actions, available to every page via useAppData().
 * This is where real backend data lives -- pages read from here instead of
 * importing static placeholder data. See src/api.ts for the actual fetches.
 */

import { createContext, useContext, useCallback, useMemo, useState, type ReactNode } from 'react'
import * as api from '../api'
import type { ApiRace, ApiQuestion, CandidateProfile, ResultsResponse, Office } from '../api'

export type FetchStatus = 'idle' | 'loading' | 'loaded' | 'error'
export type ImportanceLevel = 'low' | 'medium' | 'high'

export const IMPORTANCE_TO_SCORE: Record<ImportanceLevel, number> = { low: 1, medium: 3, high: 5 }

export function candidateKey(office: string, name: string): string {
  return `${office}::${name}`
}

interface ElectionsState {
  status: FetchStatus
  zipcode: string
  retrievedAt: string | null
  races: ApiRace[]
  error: string | null
}

const EMPTY_ELECTIONS: ElectionsState = {
  status: 'idle',
  zipcode: '',
  retrievedAt: null,
  races: [],
  error: null,
}

interface AppDataContextType {
  elections: ElectionsState
  searchElections: (zipcode: string) => Promise<void>

  questions: ApiQuestion[]
  questionsStatus: FetchStatus
  ensureQuestionsLoaded: () => Promise<void>

  profiles: Record<string, CandidateProfile>
  raceResearchStatus: Partial<Record<Office, FetchStatus>>
  raceResearchError: Partial<Record<Office, string | null>>
  ensureRaceResearched: (office: Office) => Promise<void>
  ensureAllRacesResearched: () => Promise<void>

  comparisonKeys: string[]
  toggleComparison: (office: Office, name: string) => void
  clearComparison: () => void

  quizAnswers: Record<string, number | null>
  quizImportance: Record<string, ImportanceLevel>
  setQuizAnswer: (questionId: string, value: number | null) => void
  setQuizImportance: (questionId: string, value: ImportanceLevel) => void
  resetQuiz: () => void

  results: ResultsResponse | null
  resultsStatus: FetchStatus
  resultsError: string | null
  computeResults: () => Promise<void>
}

const AppDataContext = createContext<AppDataContextType | null>(null)

export function useAppData(): AppDataContextType {
  const ctx = useContext(AppDataContext)
  if (!ctx) throw new Error('useAppData must be used within AppDataProvider')
  return ctx
}

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [elections, setElections] = useState<ElectionsState>(EMPTY_ELECTIONS)
  const [questions, setQuestions] = useState<ApiQuestion[]>([])
  const [questionsStatus, setQuestionsStatus] = useState<FetchStatus>('idle')

  const [profiles, setProfiles] = useState<Record<string, CandidateProfile>>({})
  const [raceResearchStatus, setRaceResearchStatus] = useState<Partial<Record<Office, FetchStatus>>>({})
  const [raceResearchError, setRaceResearchError] = useState<Partial<Record<Office, string | null>>>({})

  const [comparisonKeys, setComparisonKeys] = useState<string[]>([])

  const [quizAnswers, setQuizAnswers] = useState<Record<string, number | null>>({})
  const [quizImportance, setQuizImportance] = useState<Record<string, ImportanceLevel>>({})

  const [results, setResults] = useState<ResultsResponse | null>(null)
  const [resultsStatus, setResultsStatus] = useState<FetchStatus>('idle')
  const [resultsError, setResultsError] = useState<string | null>(null)

  // Core candidate-research fetch, factored out of ensureRaceResearched so it
  // can also be kicked off directly with fresh race data inside
  // searchElections -- calling ensureRaceResearched there would read stale
  // `elections` state, since setElections's effect hasn't landed yet.
  const researchRace = useCallback(async (zipcode: string, race: ApiRace) => {
    if (race.candidates.length === 0) return
    setRaceResearchStatus((prev) => ({ ...prev, [race.office]: 'loading' }))
    setRaceResearchError((prev) => ({ ...prev, [race.office]: null }))
    try {
      const response = await api.researchCandidates({
        zipcode,
        office: race.office,
        jurisdiction_name: race.jurisdiction_name,
        candidates: race.candidates.map((c) => ({ name: c.name, party: c.party, incumbent: c.incumbent })),
      })
      setProfiles((prev) => {
        const next = { ...prev }
        for (const [name, profile] of Object.entries(response.profiles)) {
          next[candidateKey(race.office, name)] = profile
        }
        return next
      })
      setRaceResearchStatus((prev) => ({ ...prev, [race.office]: 'loaded' }))
    } catch (err) {
      setRaceResearchStatus((prev) => ({ ...prev, [race.office]: 'error' }))
      setRaceResearchError((prev) => ({
        ...prev,
        [race.office]: err instanceof api.ApiError ? err.message : 'Candidate research failed.',
      }))
    }
  }, [])

  const searchElections = useCallback(
    async (zipcode: string) => {
      setElections({ status: 'loading', zipcode, retrievedAt: null, races: [], error: null })
      setProfiles({})
      setRaceResearchStatus({})
      setRaceResearchError({})
      setComparisonKeys([])
      setResults(null)
      setResultsStatus('idle')
      try {
        const response = await api.getElections(zipcode)
        setElections({
          status: 'loaded',
          zipcode: response.zipcode,
          retrievedAt: response.retrieved_at,
          races: response.races,
          error: null,
        })

        // Research every candidate found, right away, in the background --
        // not awaited, so the page itself is already interactive.
        void Promise.all(
          response.races.filter((r) => r.candidates.length > 0).map((r) => researchRace(zipcode, r)),
        )
      } catch (err) {
        setElections({
          status: 'error',
          zipcode,
          retrievedAt: null,
          races: [],
          error: err instanceof api.ApiError ? err.message : 'Something went wrong loading elections.',
        })
      }
    },
    [researchRace],
  )

  const ensureQuestionsLoaded = useCallback(async () => {
    if (questionsStatus === 'loaded' || questionsStatus === 'loading') return
    setQuestionsStatus('loading')
    try {
      const data = await api.getQuestions()
      setQuestions(data)
      setQuestionsStatus('loaded')
    } catch {
      setQuestionsStatus('error')
    }
  }, [questionsStatus])

  const ensureRaceResearched = useCallback(
    async (office: Office) => {
      if (raceResearchStatus[office] === 'loaded' || raceResearchStatus[office] === 'loading') return
      const race = elections.races.find((r) => r.office === office)
      if (!race || race.candidates.length === 0) return
      await researchRace(elections.zipcode, race)
    },
    [elections.races, elections.zipcode, raceResearchStatus, researchRace],
  )

  const ensureAllRacesResearched = useCallback(async () => {
    await Promise.all(
      elections.races.filter((r) => r.candidates.length > 0).map((r) => ensureRaceResearched(r.office)),
    )
  }, [elections.races, ensureRaceResearched])

  const toggleComparison = useCallback((office: Office, name: string) => {
    const key = candidateKey(office, name)
    setComparisonKeys((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key)
      if (prev.length >= 4) return prev
      return [...prev, key]
    })
  }, [])

  const clearComparison = useCallback(() => setComparisonKeys([]), [])

  const setQuizAnswer = useCallback((questionId: string, value: number | null) => {
    setQuizAnswers((prev) => ({ ...prev, [questionId]: value }))
  }, [])

  const setQuizImportanceValue = useCallback((questionId: string, value: ImportanceLevel) => {
    setQuizImportance((prev) => ({ ...prev, [questionId]: value }))
  }, [])

  const resetQuiz = useCallback(() => {
    setQuizAnswers({})
    setQuizImportance({})
    setResults(null)
    setResultsStatus('idle')
    setResultsError(null)
  }, [])

  const computeResults = useCallback(async () => {
    setResultsStatus('loading')
    setResultsError(null)
    try {
      await ensureAllRacesResearched()
      const answerEntries = Object.entries(quizAnswers).filter(
        (entry): entry is [string, number] => entry[1] !== null && entry[1] !== undefined,
      )
      const importanceScores: Record<string, number> = {}
      for (const [id, level] of Object.entries(quizImportance)) {
        importanceScores[id] = IMPORTANCE_TO_SCORE[level]
      }

      const candidatesForScoring = elections.races.flatMap((race) =>
        race.candidates.map((c) => {
          const profile = profiles[candidateKey(race.office, c.name)]
          return { name: c.name, office: race.office, positions: profile?.positions ?? {} }
        }),
      )

      const response = await api.getResults({
        answers: Object.fromEntries(answerEntries),
        importance: importanceScores,
        candidates: candidatesForScoring,
      })
      setResults(response)
      setResultsStatus('loaded')
    } catch (err) {
      setResultsStatus('error')
      setResultsError(err instanceof api.ApiError ? err.message : 'Could not compute your results.')
    }
  }, [ensureAllRacesResearched, elections.races, profiles, quizAnswers, quizImportance])

  const value = useMemo<AppDataContextType>(
    () => ({
      elections,
      searchElections,
      questions,
      questionsStatus,
      ensureQuestionsLoaded,
      profiles,
      raceResearchStatus,
      raceResearchError,
      ensureRaceResearched,
      ensureAllRacesResearched,
      comparisonKeys,
      toggleComparison,
      clearComparison,
      quizAnswers,
      quizImportance,
      setQuizAnswer,
      setQuizImportance: setQuizImportanceValue,
      resetQuiz,
      results,
      resultsStatus,
      resultsError,
      computeResults,
    }),
    [
      elections,
      searchElections,
      questions,
      questionsStatus,
      ensureQuestionsLoaded,
      profiles,
      raceResearchStatus,
      raceResearchError,
      ensureRaceResearched,
      ensureAllRacesResearched,
      comparisonKeys,
      toggleComparison,
      clearComparison,
      quizAnswers,
      quizImportance,
      setQuizAnswer,
      setQuizImportanceValue,
      resetQuiz,
      results,
      resultsStatus,
      resultsError,
      computeResults,
    ],
  )

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
}

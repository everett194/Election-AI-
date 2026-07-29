/**
 * Fetch client for the VoteLocal backend (backend_api.py). This is the only
 * module that talks to the network -- pages call the functions here rather
 * than fetching directly, so there's one place that knows the API shape.
 *
 * No API key ever passes through this file or the frontend build: Tavily
 * and Anthropic keys live only on the server (see backend_api.py /
 * election_lookup.py / tavily_search.py).
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, 'Could not reach the VoteLocal server. Check your connection and try again.')
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // response body wasn't JSON -- fall back to the generic message above
    }
    throw new ApiError(response.status, detail)
  }

  return response.json() as Promise<T>
}

// ─── Shared types (mirror backend_api.py's serializers) ─────────────────────

export interface ApiSource {
  url: string
  title: string | null
}

export interface ApiPosition {
  summary: string
  confidence: 'high' | 'medium' | 'low'
  sources: ApiSource[]
}

export interface ApiCandidate {
  name: string
  party: string | null
  incumbent: boolean | null
  positions: ApiPosition[]
}

export type Office = 'mayor' | 'county' | 'us_house'

export interface ApiRace {
  office: Office
  office_label: string
  jurisdiction_name: string
  election_date: string | null
  election_type: 'primary' | 'general' | null
  notes: string | null
  candidates: ApiCandidate[]
}

export interface ElectionsResponse {
  zipcode: string
  retrieved_at: string
  races: ApiRace[]
}

export interface ApiQuestion {
  id: string
  category: string
  category_label: string
  econ_weight: number
  social_weight: number
  text: string
  approach_1: string
  approach_2: string
}

export type IssueConfidence = 'explicit' | 'strong_inference' | 'weak_inference' | 'speculative'

export interface IssuePosition {
  question_id: string
  position: number
  confidence: IssueConfidence
  source: ApiSource | null
}

export interface CandidateProfile {
  candidate_name: string
  office: Office
  positions: Record<string, number>
  sourced_positions: IssuePosition[]
  coverage: { total_questions: number; answered: number; sourced: number; speculative: number }
  categories_covered: string[]
  compass: { econ: number; social: number; has_econ: boolean; has_social: boolean }
}

export interface ResearchResponse {
  profiles: Record<string, CandidateProfile>
}

export interface CandidateCompatibility {
  overall_pct: number | null
  by_category: Record<string, number>
  question_count: number
}

export interface CandidateResult {
  name: string
  office: Office
  compass: { econ: number; social: number } | null
  compatibility: CandidateCompatibility
}

export interface ResultsResponse {
  radar: Record<string, number>
  voter_compass: { econ: number; social: number }
  candidates: CandidateResult[]
}

// ─── Endpoints ────────────────────────────────────────────────────────────

export function getQuestions(): Promise<ApiQuestion[]> {
  return request('/api/questions')
}

export function getElections(zipcode: string, deep = false): Promise<ElectionsResponse> {
  return request(`/api/elections?zip=${encodeURIComponent(zipcode)}${deep ? '&deep=true' : ''}`)
}

export function researchCandidates(body: {
  zipcode: string
  office: Office
  jurisdiction_name: string
  candidates: { name: string; party: string | null; incumbent: boolean | null }[]
}): Promise<ResearchResponse> {
  return request('/api/candidates/research', { method: 'POST', body: JSON.stringify(body) })
}

export function getResults(body: {
  answers: Record<string, number>
  importance: Record<string, number>
  candidates: { name: string; office: Office; positions: Record<string, number> }[]
}): Promise<ResultsResponse> {
  return request('/api/results', { method: 'POST', body: JSON.stringify(body) })
}

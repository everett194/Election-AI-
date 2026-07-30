/**
 * Small, honest derivations from real backend data -- initials for an
 * avatar, a 1-5 confidence bucket from real coverage stats, issue tags from
 * real covered categories. Nothing here invents data; it only summarizes
 * data that already came from the backend.
 */

import type { ApiQuestion, ApiSource, CandidateProfile } from '../api'

export function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  const first = parts[0][0] ?? ''
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return (first + last).toUpperCase()
}

/** 1 (little/no real coverage) to 5 (comprehensive real coverage) from actual sourced-question counts. */
export function confidenceBucket(profile: CandidateProfile | undefined): number {
  if (!profile || profile.coverage.total_questions === 0) return 1
  const ratio = profile.coverage.sourced / profile.coverage.total_questions
  if (ratio >= 0.8) return 5
  if (ratio >= 0.5) return 4
  if (ratio >= 0.25) return 3
  if (ratio > 0) return 2
  return 1
}

export function categoryLabelMap(questions: ApiQuestion[]): Record<string, string> {
  const map: Record<string, string> = {}
  for (const q of questions) map[q.category] = q.category_label
  return map
}

export function issueTagsFor(
  profile: CandidateProfile | undefined,
  labels: Record<string, string>,
  max = 3,
): string[] {
  if (!profile) return []
  return profile.categories_covered.slice(0, max).map((id) => labels[id] ?? id)
}

/** Union of every real source cited for this candidate, deduped by URL. */
export function allSourcesFor(profile: CandidateProfile | undefined): ApiSource[] {
  if (!profile) return []
  const seen = new Set<string>()
  const sources: ApiSource[] = []
  for (const pos of profile.sourced_positions) {
    if (!pos.source || seen.has(pos.source.url)) continue
    seen.add(pos.source.url)
    sources.push(pos.source)
  }
  return sources
}

export const CONFIDENCE_LABELS = ['Very limited', 'Limited', 'Moderate', 'Good', 'Comprehensive']

export function interpretCompassPosition(econ: number, social: number): string {
  if (Math.abs(econ) < 15 && Math.abs(social) < 15) {
    return 'Close to the center on both axes — no strong lean either way.'
  }
  const econLabel = econ >= 0 ? 'markets' : 'public investment'
  const socialLabel = social >= 0 ? 'civil liberties' : 'authority'
  const econStrength = Math.abs(econ) >= 40 ? 'strongly' : Math.abs(econ) >= 15 ? 'moderately' : 'only slightly'
  const socialStrength = Math.abs(social) >= 40 ? 'strongly' : Math.abs(social) >= 15 ? 'moderately' : 'only slightly'
  return `Leans ${econStrength} toward ${econLabel} and ${socialStrength} toward ${socialLabel}.`
}

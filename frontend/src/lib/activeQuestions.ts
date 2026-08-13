/**
 * Client-side mirror of questionnaire_scoring.build_active_questions --
 * selects the personalized questionnaire (5 core questions + up to 2
 * additional per selected category, capped at 12) from question metadata
 * already fetched via /api/questions. This only drives the frontend's
 * question flow/progress display; the backend is still the sole authority
 * on weights and scoring (see derive_effective_weights in
 * questionnaire_scoring.py) -- whatever question ids actually get
 * submitted are scored correctly regardless of how this list was built.
 */

import type { ApiQuestion } from '../api'

export const MAX_ACTIVE_QUESTIONS = 12
export const MAX_ADDITIONAL_PER_CATEGORY = 2
export const MIN_SELECTED_CATEGORIES = 1
export const MAX_SELECTED_CATEGORIES = 4
export const RECOMMENDED_SELECTED_CATEGORIES = 3

export function buildActiveQuestions(questions: ApiQuestion[], selectedCategories: string[]): ApiQuestion[] {
  const selected = new Set(selectedCategories)
  const active = questions.filter((q) => q.is_core)
  const activeIds = new Set(active.map((q) => q.id))
  let remaining = MAX_ACTIVE_QUESTIONS - active.length

  // Deterministic category order: the order categories first appear in the
  // fetched question list (same fixed order the backend iterates in), not
  // the voter's selection order -- so the same set of selected categories
  // always produces the same question list.
  const categoryOrder: string[] = []
  for (const q of questions) {
    if (!categoryOrder.includes(q.category)) categoryOrder.push(q.category)
  }

  for (const category of categoryOrder) {
    if (!selected.has(category) || remaining <= 0) continue
    const candidates = questions
      .filter((q) => q.category === category && !activeIds.has(q.id))
      .sort((a, b) => a.selection_priority - b.selection_priority)
    const take = candidates.slice(0, Math.min(MAX_ADDITIONAL_PER_CATEGORY, remaining))
    for (const q of take) {
      active.push(q)
      activeIds.add(q.id)
    }
    remaining -= take.length
  }

  return active
}

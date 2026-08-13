/**
 * Client-side mirror of questionnaire_scoring.order_questions_by_rank --
 * reorders all 20 questions (never a subset) so a voter's ranked-priority
 * categories' questions come first, in rank order, followed by every
 * remaining category in fixed canonical order. Drives the Stage 2 flow
 * order and progress display only -- the backend remains the sole
 * authority on weights and scoring (see derive_effective_weights /
 * derive_candidate_weights in questionnaire_scoring.py).
 */

import type { ApiQuestion } from '../api'

export const MIN_RANKED_CATEGORIES = 1
export const MAX_RANKED_CATEGORIES = 4
export const RECOMMENDED_RANKED_CATEGORIES = 3

export function orderQuestionsByRank(questions: ApiQuestion[], rankedCategories: string[]): ApiQuestion[] {
  const ranked = rankedCategories.slice(0, MAX_RANKED_CATEGORIES)
  const seenCategories = new Set<string>()
  const ordered: ApiQuestion[] = []

  // Deterministic category order: the order categories first appear in the
  // fetched question list, matching the backend's fixed canonical order.
  const categoryOrder: string[] = []
  for (const q of questions) {
    if (!categoryOrder.includes(q.category)) categoryOrder.push(q.category)
  }

  const questionsByCategory = (category: string) =>
    questions
      .filter((q) => q.category === category)
      .sort((a, b) => a.selection_priority - b.selection_priority)

  for (const category of ranked) {
    if (seenCategories.has(category) || !categoryOrder.includes(category)) continue
    seenCategories.add(category)
    ordered.push(...questionsByCategory(category))
  }

  for (const category of categoryOrder) {
    if (seenCategories.has(category)) continue
    seenCategories.add(category)
    ordered.push(...questionsByCategory(category))
  }

  return ordered
}

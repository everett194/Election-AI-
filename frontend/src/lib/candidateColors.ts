import { candidateKey } from '../context/appData'
import type { Office } from '../api'

export const CANDIDATE_PALETTE = [
  '#1a9e87',
  '#2d5fa0',
  '#c9922a',
  '#7d5ba6',
  '#b2543f',
  '#3f6b8a',
  '#5a8f4f',
  '#a24d78',
]

export function buildCandidateColorMap(
  candidates: { office: Office; name: string }[],
): Map<string, string> {
  const map = new Map<string, string>()
  candidates.forEach((c, i) => {
    map.set(candidateKey(c.office, c.name), CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length])
  })
  return map
}

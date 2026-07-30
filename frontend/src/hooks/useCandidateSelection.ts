import { useEffect, useMemo, useRef, useState } from 'react'

export interface SelectableCandidate {
  key: string
  name: string
  matchPct: number | null
}

export interface UseCandidateSelectionResult {
  selectedKeys: Set<string>
  activeKey: string | null
  search: string
  setSearch: (value: string) => void
  isSelected: (key: string) => boolean
  toggleSelected: (key: string) => void
  selectTopMatches: () => void
  selectAll: () => void
  clearAll: () => void
  setHovered: (key: string | null) => void
  togglePinned: (key: string) => void
  defaultKeys: string[]
  pinnedKey: string | null
}

const MAX_DEFAULT = 5

function computeTopMatches(candidates: SelectableCandidate[]): string[] {
  return [...candidates]
    .filter((c) => c.matchPct !== null)
    .sort((a, b) => (b.matchPct ?? 0) - (a.matchPct ?? 0))
    .slice(0, MAX_DEFAULT)
    .map((c) => c.key)
}

export function useCandidateSelection(candidates: SelectableCandidate[]): UseCandidateSelectionResult {
  const defaultKeys = useMemo(() => computeTopMatches(candidates), [candidates])
  const signature = defaultKeys.join('|')
  const lastSignature = useRef<string | null>(null)

  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(() => new Set(defaultKeys))
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)
  const [pinnedKey, setPinnedKey] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (lastSignature.current !== signature) {
      lastSignature.current = signature
      setSelectedKeys(new Set(defaultKeys))
      setPinnedKey(null)
    }
  }, [signature, defaultKeys])

  const toggleSelected = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const togglePinned = (key: string) => setPinnedKey((prev) => (prev === key ? null : key))

  return {
    selectedKeys,
    activeKey: hoveredKey ?? pinnedKey,
    search,
    setSearch,
    isSelected: (key) => selectedKeys.has(key),
    toggleSelected,
    selectTopMatches: () => setSelectedKeys(new Set(defaultKeys)),
    selectAll: () => setSelectedKeys(new Set(candidates.map((c) => c.key))),
    clearAll: () => { setSelectedKeys(new Set()); setPinnedKey(null) },
    setHovered: setHoveredKey,
    togglePinned,
    defaultKeys,
    pinnedKey,
  }
}

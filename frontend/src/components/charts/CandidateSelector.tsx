import type { UseCandidateSelectionResult } from '../../hooks/useCandidateSelection'

export interface SelectorCandidate {
  key: string
  name: string
  matchPct: number | null
  color: string
}

interface CandidateSelectorProps {
  candidates: SelectorCandidate[]
  selection: UseCandidateSelectionResult
}

export function CandidateSelector({ candidates, selection }: CandidateSelectorProps) {
  const query = selection.search.trim().toLowerCase()
  const visible = query ? candidates.filter((c) => c.name.toLowerCase().includes(query)) : candidates

  return (
    <div className="bg-surface rounded-2xl border border-border p-4 flex flex-col gap-3">
      <div>
        <label htmlFor="candidate-search" className="sr-only">Search candidates</label>
        <input
          id="candidate-search"
          type="text"
          value={selection.search}
          onChange={(e) => selection.setSearch(e.target.value)}
          placeholder="Search candidates…"
          className="w-full py-2 px-3 rounded-lg border border-border text-sm text-navy
            placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-civic focus:border-transparent"
        />
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={selection.selectTopMatches}
          className="text-[11px] font-medium px-2.5 py-1 rounded-full border border-civic/30 text-civic hover:bg-civic-pale transition-colors"
        >
          Select top matches
        </button>
        <button
          type="button"
          onClick={selection.selectAll}
          className="text-[11px] font-medium px-2.5 py-1 rounded-full border border-border text-muted hover:text-navy hover:border-border-strong transition-colors"
        >
          Select all
        </button>
        <button
          type="button"
          onClick={selection.clearAll}
          className="text-[11px] font-medium px-2.5 py-1 rounded-full border border-border text-muted hover:text-navy hover:border-border-strong transition-colors"
        >
          Clear all
        </button>
      </div>

      <ul className="max-h-56 overflow-y-auto -mx-1 px-1 space-y-0.5" aria-label="Candidates">
        {visible.length === 0 && (
          <li className="text-xs text-muted-light italic py-2 px-1">No candidates match "{selection.search}"</li>
        )}
        {visible.map((c) => {
          const checked = selection.isSelected(c.key)
          const active = selection.activeKey === c.key
          return (
            <li key={c.key}>
              <div
                className={`flex items-center gap-2 rounded-lg px-1.5 py-1.5 transition-colors ${active ? 'bg-soft' : 'hover:bg-soft/60'}`}
                onMouseEnter={() => selection.setHovered(c.key)}
                onMouseLeave={() => selection.setHovered(null)}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => selection.toggleSelected(c.key)}
                  aria-label={c.name}
                  className="w-4 h-4 rounded border-border-strong accent-civic shrink-0"
                />
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: c.color, boxShadow: active ? `0 0 0 2px white, 0 0 0 4px ${c.color}` : 'none' }}
                  aria-hidden="true"
                />
                <button
                  type="button"
                  onClick={() => selection.togglePinned(c.key)}
                  onFocus={() => selection.setHovered(c.key)}
                  onBlur={() => selection.setHovered(null)}
                  aria-pressed={selection.pinnedKey === c.key}
                  aria-label={`Highlight ${c.name} in both charts`}
                  className="flex-1 flex items-center justify-between gap-2 min-w-0 text-left"
                >
                  <span className="text-xs text-navy truncate" title={c.name}>
                    {c.name}
                  </span>
                  {c.matchPct !== null && (
                    <span className="text-[10px] font-mono text-muted shrink-0">~{Math.round(c.matchPct)}%</span>
                  )}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

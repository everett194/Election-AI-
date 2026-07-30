# Candidate Results Charts Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the "Issue-by-issue alignment" radar chart and "Ideological compass" scatter plot on `ResultsDashboardPage` into a polished, responsive, interactive visualization system with shared candidate selection, fixed label overlap/clipping, and expandable modal views — without touching backend APIs, matching logic, or routing.

**Architecture:** Extract the two charts (currently inlined in `ResultsDashboardPage.tsx`, one via Recharts, one via hand-rolled SVG) into standalone components under `src/components/charts/`. Introduce one lifted selection hook (`useCandidateSelection`) shared by both charts and a single `CandidateSelector` control panel, plus a shared color-assignment module so a candidate's color is identical in both charts. Wrap each chart in a `ChartCard` that adds an "Expand" button reusing (and hardening) the existing `Modal` component. The compass keeps its hand-rolled SVG approach (Recharts has no scatter/label-collision primitive that beats hand control here) but gains a deterministic, dependency-free collision-avoidance pass for near-identical points.

**Tech Stack:** React 19 + TypeScript (strict) + Vite. Charting: Recharts 3.10 (radar only; compass stays custom SVG). Styling: Tailwind CSS v4 via `@theme` tokens. No new dependencies.

## Global Constraints

- Do not change `src/api.ts` types, backend endpoints, `useAppData()` context shape, routing (`src/App.tsx`, `src/context/nav.tsx`), or the questionnaire/matching logic.
- No new npm dependencies — implement collision avoidance, tooltips, and modal focus-trapping by hand.
- `tsconfig.json` has `strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true` — every new file must compile clean under `npx tsc --noEmit`.
- There is no test runner configured in this repo (`package.json` has only `dev`/`build`/`preview`/`format` scripts, no `test`/`lint`). Verification for every task is: `npx tsc --noEmit` (type-check) + manual check via `npm run dev`. Do not add a test framework — out of scope and against the "avoid unnecessary dependencies" instruction.
- Preserve existing typography (`Fraunces` for headings via inline `style={{ fontFamily: ... }}`, Tailwind utility classes for body copy) and the existing civic/navy/teal/gold color language from `src/index.css`'s `@theme` block.
- Candidate identity key everywhere is `candidateKey(office, name)` from `src/context/appData.tsx` (`` `${office}::${name}` ``) — reuse it, don't invent a new key scheme.

---

## File Structure

New files:
- `frontend/src/lib/candidateColors.ts` — canonical ordered color palette + `buildCandidateColorMap()`, so radar and compass always agree on a candidate's color.
- `frontend/src/lib/compassGeometry.ts` — pure math: `layoutCompassPoints()` nudges near-identical compass points apart for rendering only, preserving true values for tooltips.
- `frontend/src/hooks/useCandidateSelection.ts` — lifted state: which candidates are checked (rendered), which one is "active" (hovered or pinned, drives cross-chart highlight/fade), search text, and the bulk actions (top matches / all / clear).
- `frontend/src/components/charts/CandidateSelector.tsx` — the single shared legend/control panel (search, bulk actions, scrollable checkbox list) — this is the chart legend, moved fully outside the plot.
- `frontend/src/components/charts/IssueRadarChart.tsx` — Recharts radar, wrapped category-label ticks, custom tooltip, fade-on-hover.
- `frontend/src/components/charts/IdeologicalCompassChart.tsx` — redesigned hand-rolled SVG compass (responsive viewBox, collision-aware rendering, keyboard-accessible points) plus an exported `CompassDetailsPanel` for the selected candidate's exact values.
- `frontend/src/components/charts/ChartCard.tsx` — shared card chrome (title/subtitle/Expand button) that renders chart content twice — once inline, once inside an expanded `Modal` — via a render-prop so selection state is never duplicated.

Modified files:
- `frontend/src/components/ui.tsx` — `Modal`: add `xl` size, a focus trap (Tab/Shift+Tab cycling), and restore-focus-to-trigger on close. (Currently unused anywhere in the app — this is its first real call site.)
- `frontend/src/lib/derive.ts` — add `interpretCompassPosition(econ, social)`, a short computed-from-real-numbers description (not invented data), used by compass tooltips/details panel.
- `frontend/src/pages/ResultsDashboardPage.tsx` — remove the inline `CompassChart` function and `CANDIDATE_COLORS` const; compose the new components; move the two charts out of the narrow 340px sidebar into a new full-width "Compare candidates visually" section per the requested layout direction.

**Design notes on the two trickiest requirements:**

1. **Shared selection across two visually separate charts, with only one selector widget rendered:** `useCandidateSelection` is instantiated once in `ResultsDashboardPage` and passed down as props (not context — it's page-scoped, one instance, no need for the indirection). The one `CandidateSelector` panel sits beside the radar chart (matches the spec's explicit radar requirement: "on desktop, place candidate controls in a panel beside the chart"). The compass chart, beside it, gets a smaller `CompassDetailsPanel` (exact values for the active/first-selected candidate) instead of a second full selector — both panels read the *same* lifted `selection` object, so checking/hovering/pinning a candidate anywhere updates both charts immediately. This avoids duplicating the selector UI while still satisfying "shared candidate-selection state."
2. **Radar label overlap vs. compass label overlap are different problems, so they get different fixes:** the radar chart's category labels are static text around a fixed set of ~5-8 axis points — the fix is word-wrap to 2 lines (`PolarAngleAxis` custom `tick` function) plus bigger margins plus a native SVG `<title>` fallback for anything still truncated. The compass problem is *data-dependent* — candidate points can cluster anywhere, including on top of each other — so it needs an actual collision-avoidance pass at render time (`layoutCompassPoints`, a small deterministic iterative separation algorithm), not just static layout; labels themselves are hidden by default (initials-only) and only drawn for the active/pinned candidate, sidestepping the N-labels-collide problem entirely per the spec's own preferred fallback ("show compact initials... full name on hover/focus/selection").

---

### Task 1: Shared candidate color palette

**Files:**
- Create: `frontend/src/lib/candidateColors.ts`

**Interfaces:**
- Consumes: `candidateKey` from `frontend/src/context/appData.tsx` (`candidateKey(office: string, name: string): string`), `Office` type from `frontend/src/api.ts`.
- Produces: `CANDIDATE_PALETTE: string[]`, `buildCandidateColorMap(candidates: { office: Office; name: string }[]): Map<string, string>` — consumed by Task 9.

- [ ] **Step 1: Create the file**

```ts
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
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `candidateColors.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/candidateColors.ts
git commit -m "Add shared candidate color palette for charts"
```

---

### Task 2: Compass geometry helpers + position interpretation text

**Files:**
- Create: `frontend/src/lib/compassGeometry.ts`
- Modify: `frontend/src/lib/derive.ts`

**Interfaces:**
- Produces: `CompassInputPoint`, `CompassLaidOutPoint`, `layoutCompassPoints(points: CompassInputPoint[], voter: { econ: number; social: number }): CompassLaidOutPoint[]` — consumed by Task 7. `interpretCompassPosition(econ: number, social: number): string` in `derive.ts` — consumed by Task 7 and Task 9.

- [ ] **Step 1: Create `compassGeometry.ts`**

```ts
export interface CompassInputPoint {
  key: string
  econ: number
  social: number
}

export interface CompassLaidOutPoint extends CompassInputPoint {
  renderEcon: number
  renderSocial: number
  jittered: boolean
  clusterSize: number
}

const DOMAIN = 120
const NEAR_THRESHOLD = 6
const SEPARATION = 9
const MAX_ITERATIONS = 30

function deterministicAngle(key: string): number {
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0
  return (hash % 360) * (Math.PI / 180)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function separate(
  a: { key: string; renderEcon: number; renderSocial: number },
  b: { key: string; renderEcon: number; renderSocial: number },
): boolean {
  const dx = b.renderEcon - a.renderEcon
  const dy = b.renderSocial - a.renderSocial
  const dist = Math.hypot(dx, dy)
  if (dist >= NEAR_THRESHOLD) return false
  const angle = dist === 0 ? deterministicAngle(a.key + b.key) : Math.atan2(dy, dx)
  const push = (SEPARATION - dist) / 2
  a.renderEcon -= Math.cos(angle) * push
  a.renderSocial -= Math.sin(angle) * push
  b.renderEcon += Math.cos(angle) * push
  b.renderSocial += Math.sin(angle) * push
  return true
}

/**
 * Nudges points that sit almost on top of each other apart, purely for
 * legibility. Callers should keep using the original econ/social values
 * (not renderEcon/renderSocial) for tooltips and any details panel.
 */
export function layoutCompassPoints(
  points: CompassInputPoint[],
  voter: { econ: number; social: number },
): CompassLaidOutPoint[] {
  const anchors = points.map((p) => ({ ...p, renderEcon: p.econ, renderSocial: p.social }))

  for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
    let moved = false
    for (let i = 0; i < anchors.length; i++) {
      for (let j = i + 1; j < anchors.length; j++) {
        if (separate(anchors[i], anchors[j])) moved = true
      }
      const a = anchors[i]
      const dx = a.renderEcon - voter.econ
      const dy = a.renderSocial - voter.social
      const dist = Math.hypot(dx, dy)
      if (dist < NEAR_THRESHOLD) {
        const angle = dist === 0 ? deterministicAngle(a.key) : Math.atan2(dy, dx)
        a.renderEcon += Math.cos(angle) * (SEPARATION - dist)
        a.renderSocial += Math.sin(angle) * (SEPARATION - dist)
        moved = true
      }
    }
    if (!moved) break
  }

  return anchors.map((a) => {
    const clusterSize = 1 + points.filter(
      (p) => p.key !== a.key && Math.hypot(p.econ - a.econ, p.social - a.social) < NEAR_THRESHOLD,
    ).length
    return {
      ...a,
      renderEcon: clamp(a.renderEcon, -DOMAIN, DOMAIN),
      renderSocial: clamp(a.renderSocial, -DOMAIN, DOMAIN),
      jittered: Math.hypot(a.renderEcon - a.econ, a.renderSocial - a.social) > 0.5,
      clusterSize,
    }
  })
}
```

- [ ] **Step 2: Add `interpretCompassPosition` to `derive.ts`**

Append to `frontend/src/lib/derive.ts` (after the existing `CONFIDENCE_LABELS` export):

```ts
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
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/compassGeometry.ts frontend/src/lib/derive.ts
git commit -m "Add compass collision-avoidance geometry and position interpretation"
```

---

### Task 3: Shared candidate-selection hook

**Files:**
- Create: `frontend/src/hooks/useCandidateSelection.ts`

**Interfaces:**
- Produces: `SelectableCandidate { key: string; name: string; matchPct: number | null }`, `UseCandidateSelectionResult` (see below), `useCandidateSelection(candidates: SelectableCandidate[]): UseCandidateSelectionResult` — consumed by Task 9 and read by Tasks 5/6/7 via prop types.

- [ ] **Step 1: Create the file**

```ts
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
  }
}
```

`activeKey` is hover-or-pin: hovering (mouse or focus) temporarily sets it; clicking a candidate (in the selector, or later on a chart mark) toggles a persistent "pin" so touch/keyboard users can highlight without holding hover. Default selection is top-5-by-`matchPct` (naturally 3-5 in practice since races rarely have more candidates than that with real matches); it resets whenever the candidate list changes identity (e.g. after retaking the questionnaire).

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useCandidateSelection.ts
git commit -m "Add shared candidate-selection hook for chart interactivity"
```

---

### Task 4: Harden the shared Modal (expand/zoom support)

**Files:**
- Modify: `frontend/src/components/ui.tsx:154-202`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Modal` now accepts `size?: 'sm' | 'md' | 'lg' | 'xl'` (was `'sm'|'md'|'lg'`); on open, traps Tab focus inside and auto-focuses the first focusable element; on close, restores focus to whatever had focus before opening. Consumed by Task 8.

- [ ] **Step 1: Replace the Modal implementation**

Replace lines 154-202 of `frontend/src/components/ui.tsx` (the `// ─── Modal ───` section) with:

```tsx
// ─── Modal ───────────────────────────────────────────────────────────────────

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const MODAL_SIZES = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-6xl' }

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return

    previouslyFocused.current = document.activeElement as HTMLElement | null
    const dialog = dialogRef.current
    const focusable = dialog?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    if (focusable && focusable.length > 0) focusable[0].focus()
    else dialog?.focus()

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab' || !dialog) return
      const items = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      previouslyFocused.current?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[100] bg-navy/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className={`${MODAL_SIZES[size]} w-full bg-surface rounded-2xl shadow-2xl border border-border overflow-hidden`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 id="modal-title" className="font-semibold text-navy text-base" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            {title}
          </h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-navy hover:bg-soft transition-colors"
            aria-label="Close"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
              <path d="M3.22 3.22a.75.75 0 011.06 0L8 6.94l3.72-3.72a.75.75 0 111.06 1.06L9.06 8l3.72 3.72a.75.75 0 11-1.06 1.06L8 9.06l-3.72 3.72a.75.75 0 01-1.06-1.06L6.94 8 3.22 4.28a.75.75 0 010-1.06z"/>
            </svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
```

No import changes needed — `useRef`, `useEffect` are already imported at the top of `ui.tsx`.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual check**

Run `cd frontend && npm run dev`. `Modal` has no call sites yet, so there is nothing to click through — this step is just confirming the dev server still boots clean (no runtime import errors). Stop the dev server after confirming.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui.tsx
git commit -m "Harden Modal with focus trap, focus restore, and an xl size"
```

---

### Task 5: Candidate selector panel

**Files:**
- Create: `frontend/src/components/charts/CandidateSelector.tsx`

**Interfaces:**
- Consumes: `UseCandidateSelectionResult` from Task 3.
- Produces: `SelectorCandidate { key: string; name: string; matchPct: number | null; color: string }`, `CandidateSelector({ candidates, selection }: { candidates: SelectorCandidate[]; selection: UseCandidateSelectionResult })` — consumed by Task 9.

- [ ] **Step 1: Create the file**

```tsx
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
                  id={`candidate-check-${c.key}`}
                  type="checkbox"
                  checked={checked}
                  onChange={() => selection.toggleSelected(c.key)}
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
                  aria-pressed={active}
                  aria-label={`Highlight ${c.name} in both charts`}
                  className="flex-1 flex items-center justify-between gap-2 min-w-0 text-left"
                >
                  <label htmlFor={`candidate-check-${c.key}`} className="text-xs text-navy truncate pointer-events-none">
                    {c.name}
                  </label>
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
```

Note: the checkbox toggles chart *membership*; clicking the name/row button toggles *pin* (cross-chart highlight) — kept as two separate controls rather than nesting a clickable label inside a button (bad for a11y/event bubbling). The `<label>`'s default click-to-toggle-checkbox behavior is disabled via `pointer-events-none` since the row button already handles clicks; the `htmlFor` association is kept purely so screen readers announce the checkbox's name.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/CandidateSelector.tsx
git commit -m "Add candidate selector panel (search, bulk actions, checkboxes)"
```

---

### Task 6: Radar chart component

**Files:**
- Create: `frontend/src/components/charts/IssueRadarChart.tsx`

**Interfaces:**
- Consumes: Recharts (`RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip, BaseTickContentProps, TooltipProps` from `'recharts'`).
- Produces: `RadarSeriesCandidate { key: string; name: string; color: string }`, `IssueRadarChart(props)` — consumed by Task 9. Props: `data: Record<string, string | number>[]`, `candidates: RadarSeriesCandidate[]`, `selectedKeys: Set<string>`, `activeKey: string | null`, `onHoverCandidate: (key: string | null) => void`, `onTogglePinned: (key: string) => void`, `variant?: 'card' | 'modal'`.

- [ ] **Step 1: Create the file**

```tsx
import type { ReactElement } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip,
} from 'recharts'
import type { BaseTickContentProps, TooltipProps } from 'recharts'

export interface RadarSeriesCandidate {
  key: string
  name: string
  color: string
}

interface IssueRadarChartProps {
  data: Record<string, string | number>[]
  candidates: RadarSeriesCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  onHoverCandidate: (key: string | null) => void
  onTogglePinned: (key: string) => void
  variant?: 'card' | 'modal'
}

function wrapLabel(value: string): string[] {
  const words = value.split(' ')
  const lines: string[] = []
  let current = ''
  for (const word of words) {
    const next = current ? `${current} ${word}` : word
    if (next.length > 14 && current) {
      lines.push(current)
      current = word
    } else {
      current = next
    }
  }
  if (current) lines.push(current)
  if (lines.length > 2) {
    const truncated = lines.slice(0, 2)
    truncated[1] = `${truncated[1].slice(0, 11)}…`
    return truncated
  }
  return lines
}

function renderCategoryTick(props: BaseTickContentProps): ReactElement {
  const { x, y, payload, textAnchor } = props
  const numX = Number(x)
  const numY = Number(y)
  const label = String(payload.value)
  const lines = wrapLabel(label)

  return (
    <text x={numX} y={numY} textAnchor={textAnchor} fill="#6b7a99" fontSize={10} dy={lines.length > 1 ? -4 : 3}>
      <title>{label}</title>
      {lines.map((line, i) => (
        <tspan key={i} x={numX} dy={i === 0 ? 0 : 12}>{line}</tspan>
      ))}
    </text>
  )
}

function RadarTooltipContent({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="bg-surface border border-border rounded-lg shadow-lg px-3 py-2 text-xs max-w-[220px]">
      <p className="font-semibold text-navy mb-1">{label}</p>
      <div className="space-y-0.5">
        {payload.map((entry) => (
          <div key={String(entry.dataKey)} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5 text-navy/80 truncate">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
              {entry.name}
            </span>
            <span className="font-mono text-navy shrink-0">{entry.value ?? '–'}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function IssueRadarChart({
  data, candidates, selectedKeys, activeKey, onHoverCandidate, onTogglePinned, variant = 'card',
}: IssueRadarChartProps) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))

  return (
    <div className={variant === 'modal' ? 'h-[70vh]' : 'h-[300px] sm:h-[340px]'}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 28, right: 48, bottom: 28, left: 48 }}>
          <PolarGrid stroke="#dde3ed" strokeOpacity={0.7} />
          <PolarAngleAxis dataKey="category" tick={renderCategoryTick} />
          <Radar
            name="You"
            dataKey="You"
            stroke="#0f2340"
            strokeDasharray="4 3"
            strokeWidth={1.5}
            fill="none"
            isAnimationActive={false}
          />
          {visible.map((c) => {
            const dimmed = activeKey !== null && activeKey !== c.key
            return (
              <Radar
                key={c.key}
                name={c.name}
                dataKey={c.name}
                stroke={c.color}
                fill={c.color}
                fillOpacity={dimmed ? 0.04 : 0.12}
                strokeOpacity={dimmed ? 0.25 : 1}
                strokeWidth={activeKey === c.key ? 3 : 2}
                onMouseEnter={() => onHoverCandidate(c.key)}
                onMouseLeave={() => onHoverCandidate(null)}
                onClick={() => onTogglePinned(c.key)}
                isAnimationActive={false}
              />
            )
          })}
          <RechartsTooltip content={<RadarTooltipContent />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

The "You" series is always drawn (dashed navy outline, no fill) so the chart is actually comparable at a glance — the original code computed a `You` value per row but never rendered it. Candidate series are drawn only for `selectedKeys` (never all-by-default); when `activeKey` is set, non-active series fade via `fillOpacity`/`strokeOpacity`.

If `content={<RadarTooltipContent />}` produces a `tsc` type error (Recharts' `TooltipContentProps` vs `TooltipProps` generics), change it to `content={(props) => <RadarTooltipContent {...(props as TooltipProps<number, string>)} />}` — functionally identical, just sidesteps the `cloneElement` typing path.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. If there's a Recharts generic mismatch on the `Tooltip content` line, apply the fallback noted above and re-run.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/IssueRadarChart.tsx
git commit -m "Add redesigned issue-by-issue radar chart component"
```

---

### Task 7: Ideological compass chart + details panel

**Files:**
- Create: `frontend/src/components/charts/IdeologicalCompassChart.tsx`

**Interfaces:**
- Consumes: `layoutCompassPoints` from Task 2 (`compassGeometry.ts`), `initialsFor`, `interpretCompassPosition` from `frontend/src/lib/derive.ts`.
- Produces: `CompassCandidate { key: string; name: string; econ: number; social: number; color: string }`, `IdeologicalCompassChart(props)`, `CompassDetailsPanel(props)` — both consumed by Task 9.

- [ ] **Step 1: Create the file**

```tsx
import type { KeyboardEvent } from 'react'
import { layoutCompassPoints } from '../../lib/compassGeometry'
import { initialsFor, interpretCompassPosition } from '../../lib/derive'

export interface CompassCandidate {
  key: string
  name: string
  econ: number
  social: number
  color: string
}

interface IdeologicalCompassChartProps {
  voter: { econ: number; social: number }
  candidates: CompassCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  onHoverCandidate: (key: string | null) => void
  onTogglePinned: (key: string) => void
  variant?: 'card' | 'modal'
}

const DOMAIN = 120
const VB = 400
const PAD = 56

function toSvg(v: number): number {
  return ((v + DOMAIN) / (DOMAIN * 2)) * (VB - PAD * 2) + PAD
}

export function IdeologicalCompassChart({
  voter, candidates, selectedKeys, activeKey, onHoverCandidate, onTogglePinned, variant = 'card',
}: IdeologicalCompassChartProps) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))
  const byKey = new Map(visible.map((c) => [c.key, c]))
  const laidOut = layoutCompassPoints(visible.map((c) => ({ key: c.key, econ: c.econ, social: c.social })), voter)

  const handleKeyDown = (e: KeyboardEvent<SVGGElement>, key: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onTogglePinned(key)
    }
  }

  return (
    <div className={variant === 'modal' ? 'max-w-2xl mx-auto' : 'max-w-md mx-auto'}>
      <svg
        viewBox={`0 0 ${VB} ${VB}`}
        className="w-full h-auto"
        role="img"
        aria-label="Ideological compass showing your position and candidate positions"
      >
        <rect x={PAD} y={PAD} width={(VB - PAD * 2) / 2} height={(VB - PAD * 2) / 2} fill="#eef3fb" opacity="0.5" />
        <rect x={VB / 2} y={VB / 2} width={(VB - PAD * 2) / 2} height={(VB - PAD * 2) / 2} fill="#fdf3e0" opacity="0.4" />

        <line x1={PAD} y1={VB / 2} x2={VB - PAD} y2={VB / 2} stroke="#dde3ed" strokeWidth="1.5" />
        <line x1={VB / 2} y1={PAD} x2={VB / 2} y2={VB - PAD} stroke="#dde3ed" strokeWidth="1.5" />

        <text x={VB / 2} y={PAD - 20} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600">MORE CIVIL LIBERTIES</text>
        <text x={VB / 2} y={VB - PAD + 32} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600">MORE AUTHORITY</text>
        <text x={PAD - 34} y={VB / 2} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600"
          transform={`rotate(-90 ${PAD - 34} ${VB / 2})`}>PUBLIC INVESTMENT</text>
        <text x={VB - PAD + 34} y={VB / 2} textAnchor="middle" fill="#6b7a99" fontSize="11" fontWeight="600"
          transform={`rotate(90 ${VB - PAD + 34} ${VB / 2})`}>MARKETS</text>

        <circle cx={toSvg(voter.econ)} cy={toSvg(-voter.social)} r="9" fill="#c0392b" opacity="0.9" />
        <circle cx={toSvg(voter.econ)} cy={toSvg(-voter.social)} r="15" fill="#c0392b" opacity="0.15" />
        <text x={toSvg(voter.econ)} y={toSvg(-voter.social) - 20} textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="700">YOU</text>

        {laidOut.map((point) => {
          const source = byKey.get(point.key)
          if (!source) return null
          const cx = toSvg(point.renderEcon)
          const cy = toSvg(-point.renderSocial)
          const active = activeKey === point.key
          const dimmed = activeKey !== null && !active

          return (
            <g
              key={point.key}
              tabIndex={0}
              role="button"
              aria-label={`${source.name}: ${interpretCompassPosition(source.econ, source.social)}`}
              aria-pressed={active}
              onMouseEnter={() => onHoverCandidate(point.key)}
              onMouseLeave={() => onHoverCandidate(null)}
              onFocus={() => onHoverCandidate(point.key)}
              onBlur={() => onHoverCandidate(null)}
              onClick={() => onTogglePinned(point.key)}
              onKeyDown={(e) => handleKeyDown(e, point.key)}
              opacity={dimmed ? 0.35 : 1}
              className="cursor-pointer outline-none"
            >
              <title>
                {`${source.name} — economic: ${Math.round(source.econ)}, governance: ${Math.round(source.social)}. ${interpretCompassPosition(source.econ, source.social)}`}
                {point.clusterSize > 1 ? ` Shares this area with ${point.clusterSize - 1} other candidate${point.clusterSize > 2 ? 's' : ''}.` : ''}
              </title>
              {point.jittered && (
                <line
                  x1={toSvg(point.econ)} y1={toSvg(-point.social)} x2={cx} y2={cy}
                  stroke={source.color} strokeWidth="1" strokeDasharray="2 2" opacity="0.6"
                />
              )}
              <circle
                cx={cx} cy={cy} r={active ? 14 : 12} fill={source.color}
                stroke={active ? '#0f2340' : 'white'} strokeWidth={active ? 2.5 : 1.5}
              />
              {point.clusterSize > 1 && (
                <circle cx={cx} cy={cy} r={active ? 18 : 16} fill="none" stroke={source.color} strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
              )}
              <text x={cx} y={cy + 4} textAnchor="middle" fill="white" fontSize="9" fontWeight="700" pointerEvents="none">
                {initialsFor(source.name)}
              </text>
              {active && (
                <text x={cx} y={cy - 20} textAnchor="middle" fill="#0f2340" fontSize="10" fontWeight="600" pointerEvents="none">
                  {source.name}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function CompassDetailsPanel({ candidates, selectedKeys, activeKey, voter }: {
  candidates: CompassCandidate[]
  selectedKeys: Set<string>
  activeKey: string | null
  voter: { econ: number; social: number }
}) {
  const visible = candidates.filter((c) => selectedKeys.has(c.key))
  const focused = visible.find((c) => c.key === activeKey) ?? visible[0] ?? null

  return (
    <div className="bg-soft/60 rounded-xl border border-border p-3.5 text-xs space-y-2.5">
      <div>
        <p className="font-semibold text-navy mb-0.5">You</p>
        <p className="text-muted">
          Economic: <span className="font-mono text-navy">{Math.round(voter.econ)}</span>
          {' · '}
          Governance: <span className="font-mono text-navy">{Math.round(voter.social)}</span>
        </p>
      </div>
      {focused ? (
        <div className="pt-2 border-t border-border/60">
          <p className="font-semibold text-navy mb-0.5 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: focused.color }} aria-hidden="true" />
            {focused.name}
          </p>
          <p className="text-muted">
            Economic: <span className="font-mono text-navy">{Math.round(focused.econ)}</span>
            {' · '}
            Governance: <span className="font-mono text-navy">{Math.round(focused.social)}</span>
          </p>
          <p className="text-muted mt-1 leading-relaxed">{interpretCompassPosition(focused.econ, focused.social)}</p>
        </div>
      ) : (
        <p className="text-muted-light italic pt-2 border-t border-border/60">Hover or select a candidate to see their exact values.</p>
      )}
    </div>
  )
}
```

Sign convention (unchanged from the original `CompassChart`, verified against its axis labels): `econ >= 0` → markets, `econ < 0` → public investment; `social >= 0` → civil liberties, `social < 0` → authority.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/IdeologicalCompassChart.tsx
git commit -m "Add redesigned ideological compass with collision-aware layout"
```

---

### Task 8: Chart card wrapper (Expand → modal)

**Files:**
- Create: `frontend/src/components/charts/ChartCard.tsx`

**Interfaces:**
- Consumes: `Modal` from `frontend/src/components/ui.tsx` (Task 4).
- Produces: `ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: (variant: 'card' | 'modal') => ReactNode })` — consumed by Task 9.

- [ ] **Step 1: Create the file**

```tsx
import { useState, type ReactNode } from 'react'
import { Modal } from '../ui'

interface ChartCardProps {
  title: string
  subtitle: string
  children: (variant: 'card' | 'modal') => ReactNode
}

export function ChartCard({ title, subtitle, children }: ChartCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-surface rounded-2xl border border-border p-5">
      <div className="flex items-start justify-between gap-3 mb-1">
        <h3 className="font-semibold text-navy text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
          {title}
        </h3>
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="shrink-0 text-[11px] font-medium text-civic hover:text-civic-light flex items-center gap-1 transition-colors"
          aria-label={`Expand ${title}`}
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 2H2v4M10 2h4v4M6 14H2v-4M10 14h4v-4" />
          </svg>
          Expand
        </button>
      </div>
      <p className="text-[10px] text-muted mb-2">{subtitle}</p>
      {children('card')}

      <Modal open={expanded} onClose={() => setExpanded(false)} title={title} size="xl">
        <p className="text-xs text-muted mb-3">{subtitle}</p>
        {children('modal')}
      </Modal>
    </div>
  )
}
```

The same chart component instance type is rendered twice (once at `variant="card"` size, once at `variant="modal"` size) from the *same* lifted `selection` state passed in by the caller — so pins/hovers/checked candidates carry over identically between the inline card and the expanded modal, with no extra wiring.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/ChartCard.tsx
git commit -m "Add ChartCard wrapper with Expand-to-modal support"
```

---

### Task 9: Wire the redesign into ResultsDashboardPage

**Files:**
- Modify: `frontend/src/pages/ResultsDashboardPage.tsx` (full-file replacement of the sections described below)

**Interfaces:**
- Consumes: everything from Tasks 1-8 (`buildCandidateColorMap`, `useCandidateSelection`, `CandidateSelector`, `IssueRadarChart`, `IdeologicalCompassChart`, `CompassDetailsPanel`, `ChartCard`).
- Produces: no new exports — this is the integration point.

- [ ] **Step 1: Replace the whole file**

Replace the full contents of `frontend/src/pages/ResultsDashboardPage.tsx` with:

```tsx
import { useEffect, useMemo, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData, candidateKey } from '../context/appData'
import { ConfidenceIndicator } from '../components/Badges'
import { Avatar } from '../components/Cards'
import { Alert, EmptyState } from '../components/ui'
import { ChartCard } from '../components/charts/ChartCard'
import { CandidateSelector } from '../components/charts/CandidateSelector'
import { IssueRadarChart } from '../components/charts/IssueRadarChart'
import { IdeologicalCompassChart, CompassDetailsPanel } from '../components/charts/IdeologicalCompassChart'
import { useCandidateSelection } from '../hooks/useCandidateSelection'
import { buildCandidateColorMap } from '../lib/candidateColors'
import { categoryLabelMap, confidenceBucket, initialsFor } from '../lib/derive'
import type { CandidateResult } from '../api'

// ─── Match card ───────────────────────────────────────────────────────────────

function MatchCard({ result, rank, expanded, onToggle, categoryLabels }: {
  result: CandidateResult
  rank: number
  expanded: boolean
  onToggle: () => void
  categoryLabels: Record<string, string>
}) {
  const { navigate } = useNav()
  const { profiles } = useAppData()
  const profile = profiles[candidateKey(result.office, result.name)]

  const barColor = rank === 1 ? 'bg-teal' : rank === 2 ? 'bg-civic' : 'bg-muted/40'
  const pctColor = rank === 1 ? 'text-teal' : rank === 2 ? 'text-civic' : 'text-muted'
  const pct = result.compatibility.overall_pct

  return (
    <div className={`bg-surface rounded-2xl border overflow-hidden transition-shadow hover:shadow-md
      ${rank === 1 ? 'border-teal/40 shadow-sm shadow-teal/10' : 'border-border'}`}>

      {rank === 1 && pct !== null && (
        <div className="bg-teal px-4 py-1.5 flex items-center gap-2 text-white text-xs font-semibold">
          Closest estimated alignment — not an endorsement. Verify with independent research.
        </div>
      )}

      <div className="p-5">
        <div className="flex items-start gap-3.5">
          <Avatar initials={initialsFor(result.name)} index={rank - 1} size="md" />
          <div className="flex-1">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-navy text-base leading-snug" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                  {result.name}
                </h3>
              </div>
              <div className="text-right shrink-0">
                {pct !== null ? (
                  <>
                    <span className={`text-3xl font-bold font-mono ${pctColor}`}>~{Math.round(pct)}%</span>
                    <p className="text-[10px] text-muted">estimated alignment</p>
                  </>
                ) : (
                  <p className="text-xs text-muted italic max-w-[120px]">No overlapping answered questions</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {pct !== null && (
          <>
            <div className="mt-4 h-2.5 bg-soft-mid rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
            </div>
            <p className="text-[10px] text-muted mt-1 text-right">{result.compatibility.question_count} question{result.compatibility.question_count === 1 ? '' : 's'} used in this estimate</p>
          </>
        )}

        <div className="mt-3 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-muted-light uppercase tracking-wide mb-1.5">Confidence level</p>
            <ConfidenceIndicator level={confidenceBucket(profile)} showLabel />
          </div>
          <button
            onClick={() => navigate('candidate', { office: result.office, name: result.name })}
            className="text-xs text-civic font-medium hover:text-civic-light transition-colors"
          >
            Full profile →
          </button>
        </div>

        {pct !== null && (
          <button
            onClick={onToggle}
            className="mt-4 w-full py-2 rounded-xl border border-border text-xs font-medium text-muted hover:text-navy hover:border-border-strong transition-colors flex items-center justify-center gap-1.5"
          >
            {expanded ? 'Hide' : 'Show'} issue-by-issue breakdown
          </button>
        )}

        {expanded && pct !== null && (
          <div className="mt-4 space-y-1.5 border-t border-border pt-4">
            <div className="grid grid-cols-2 gap-2 text-[10px] text-muted uppercase tracking-wide pb-1 font-medium">
              <span>Category</span><span className="text-right">Alignment</span>
            </div>
            {Object.entries(result.compatibility.by_category).map(([category, score]) => (
              <div key={category} className="grid grid-cols-2 gap-2 items-center py-1.5 border-b border-border/40 last:border-0">
                <span className="text-xs text-navy/70">{categoryLabels[category] ?? category}</span>
                <span className="text-xs font-medium text-navy text-right">{Math.round(score)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── ResultsDashboardPage ─────────────────────────────────────────────────────

export default function ResultsDashboardPage() {
  const { navigate } = useNav()
  const { results, resultsStatus, resultsError, questions, ensureQuestionsLoaded, computeResults } = useAppData()
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [showMethodology, setShowMethodology] = useState(false)
  const [showCompassMethod, setShowCompassMethod] = useState(false)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
  const labels = useMemo(() => categoryLabelMap(questions), [questions])

  const candidateColorMap = useMemo(
    () => buildCandidateColorMap(results?.candidates ?? []),
    [results],
  )

  const chartCandidates = useMemo(() => {
    if (!results) return []
    return results.candidates
      .filter((c) => c.compatibility.question_count > 0 || c.compass !== null)
      .map((c) => {
        const key = candidateKey(c.office, c.name)
        return {
          key,
          name: c.name,
          matchPct: c.compatibility.overall_pct,
          color: candidateColorMap.get(key) ?? '#6b7a99',
        }
      })
  }, [results, candidateColorMap])

  const selection = useCandidateSelection(chartCandidates)

  if (resultsStatus === 'idle') {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-2xl mx-auto px-4 py-16">
        <EmptyState
          title="No results yet"
          description="Take the questionnaire first to see how you compare to local candidates."
          action={<button onClick={() => navigate('quiz')} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Take the questionnaire</button>}
        />
      </div>
    )
  }

  if (resultsStatus === 'loading') {
    return <div className="min-h-screen bg-soft flex items-center justify-center text-muted text-sm">Researching candidates and computing your results…</div>
  }

  if (resultsStatus === 'error' || !results) {
    return (
      <div className="min-h-screen bg-soft page-enter max-w-2xl mx-auto px-4 py-16">
        <EmptyState
          title="Could not compute your results"
          description={resultsError ?? 'Something went wrong.'}
          action={<button onClick={() => void computeResults()} className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors">Try again</button>}
        />
      </div>
    )
  }

  const rankedCandidates = results.candidates.filter((c) => c.compatibility.question_count > 0)
  const unrankedCandidates = results.candidates.filter((c) => c.compatibility.question_count === 0)

  const radarCategories = Object.keys(results.radar)
  const radarData = radarCategories.map((cat) => {
    const row: Record<string, string | number> = { category: labels[cat] ?? cat, You: Math.round(results.radar[cat]) }
    rankedCandidates.forEach((c) => {
      row[c.name] = Math.round(c.compatibility.by_category[cat] ?? 0)
    })
    return row
  })

  const radarSeriesCandidates = rankedCandidates.map((c) => {
    const key = candidateKey(c.office, c.name)
    return { key, name: c.name, color: candidateColorMap.get(key) ?? '#6b7a99' }
  })

  const compassCandidates = results.candidates
    .filter((c): c is CandidateResult & { compass: { econ: number; social: number } } => c.compass !== null)
    .map((c) => {
      const key = candidateKey(c.office, c.name)
      return { key, name: c.name, econ: c.compass.econ, social: c.compass.social, color: candidateColorMap.get(key) ?? '#6b7a99' }
    })

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-navy">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center gap-2 text-xs text-blue-300/70 mb-4">
            <button onClick={() => navigate('home')} className="hover:text-white">Home</button>
            <span>/</span>
            <button onClick={() => navigate('quiz')} className="hover:text-white">Questionnaire</button>
            <span>/</span>
            <span className="text-white">Results</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 leading-tight" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            Your alignment results
          </h1>
          <p className="text-blue-200/80 max-w-xl text-sm sm:text-base leading-relaxed">
            Based on your questionnaire answers and the candidates found for your ZIP code.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <Alert type="warning">
          <strong>These results are estimates.</strong> Match percentages are based on available evidence only and may be incomplete where candidate positions are uncertain or not yet documented. The highest match is not an endorsement. Use these results alongside your own independent research.
        </Alert>

        <div className="mt-8 grid lg:grid-cols-[1fr_340px] gap-8">
          {/* Left column: match cards */}
          <div className="space-y-5">
            <h2 className="font-semibold text-navy text-lg" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Candidate matches
            </h2>

            {results.candidates.length === 0 && (
              <EmptyState title="No candidates researched yet" description="Search for elections and browse a race to research candidates." />
            )}

            {[...rankedCandidates, ...unrankedCandidates].map((result, i) => (
              <MatchCard
                key={candidateKey(result.office, result.name)}
                result={result}
                rank={i + 1}
                expanded={!!expanded[candidateKey(result.office, result.name)]}
                onToggle={() => toggle(candidateKey(result.office, result.name))}
                categoryLabels={labels}
              />
            ))}

            <div className="bg-surface rounded-2xl border border-border overflow-hidden">
              <button
                onClick={() => setShowMethodology(!showMethodology)}
                className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-soft/50 transition-colors"
              >
                <span className="font-semibold text-navy text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                  How this was calculated
                </span>
                <svg viewBox="0 0 16 16" fill="currentColor" className={`w-4 h-4 text-muted transition-transform ${showMethodology ? 'rotate-180' : ''}`}>
                  <path fillRule="evenodd" clipRule="evenodd" d="M4.22 6.22a.75.75 0 011.06 0L8 8.94l2.72-2.72a.75.75 0 111.06 1.06l-3.25 3.25a.75.75 0 01-1.06 0L4.22 7.28a.75.75 0 010-1.06z"/>
                </svg>
              </button>
              {showMethodology && (
                <div className="px-5 pb-6 border-t border-border space-y-3 text-sm text-navy/70 leading-relaxed">
                  <p className="pt-4">Match percentages compare your questionnaire responses to candidate positions on the same 20 questions, using only questions where both you and the candidate have an answer. Each question is weighted by the importance you selected (Low, Medium, or High).</p>
                  <p>Questions you answered "Not Sure" or skipped are excluded. Candidates with zero overlapping answered questions show no percentage rather than a misleading number.</p>
                  <p>Match estimates are <strong>not predictions of future policy</strong> and do not account for positions not yet publicly documented.</p>
                </div>
              )}
            </div>
          </div>

          {/* Right column: actions */}
          <div className="space-y-2.5">
            <button
              onClick={() => navigate('quiz')}
              className="w-full py-3 rounded-xl border border-border text-muted text-sm font-medium hover:text-navy hover:border-border-strong transition-colors"
            >
              Retake questionnaire
            </button>
            <button
              onClick={() => navigate('elections')}
              className="w-full py-3 rounded-xl bg-navy text-white text-sm font-semibold hover:bg-navy-mid transition-colors"
            >
              Back to all races
            </button>
          </div>
        </div>

        {(rankedCandidates.length > 0 || compassCandidates.length > 0) && (
          <div className="mt-10">
            <h2 className="font-semibold text-navy text-lg mb-1" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Compare candidates visually
            </h2>
            <p className="text-sm text-muted leading-relaxed mb-5 max-w-2xl">
              Choose which candidates to compare below — your selection stays in sync between both charts.
            </p>

            <div className="grid lg:grid-cols-2 gap-6">
              {rankedCandidates.length > 0 && (
                <ChartCard title="Issue-by-issue alignment" subtitle="How closely each candidate matches you, by category">
                  {(variant) => (
                    <div className={variant === 'modal' ? 'grid md:grid-cols-[1fr_240px] gap-5 items-start' : 'grid lg:grid-cols-[1fr_220px] gap-4 items-start'}>
                      <IssueRadarChart
                        data={radarData}
                        candidates={radarSeriesCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        onHoverCandidate={selection.setHovered}
                        onTogglePinned={selection.togglePinned}
                        variant={variant}
                      />
                      <CandidateSelector candidates={chartCandidates} selection={selection} />
                    </div>
                  )}
                </ChartCard>
              )}

              {compassCandidates.length > 0 && (
                <ChartCard title="Ideological compass" subtitle="Your estimated position vs. candidates on two axes">
                  {(variant) => (
                    <div className={variant === 'modal' ? 'grid md:grid-cols-[1fr_220px] gap-5 items-start' : 'grid lg:grid-cols-[1fr_200px] gap-4 items-start'}>
                      <IdeologicalCompassChart
                        voter={results.voter_compass}
                        candidates={compassCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        onHoverCandidate={selection.setHovered}
                        onTogglePinned={selection.togglePinned}
                        variant={variant}
                      />
                      <CompassDetailsPanel
                        candidates={compassCandidates}
                        selectedKeys={selection.selectedKeys}
                        activeKey={selection.activeKey}
                        voter={results.voter_compass}
                      />
                    </div>
                  )}
                </ChartCard>
              )}
            </div>

            <div className="mt-4 max-w-2xl">
              <button
                type="button"
                onClick={() => setShowCompassMethod(!showCompassMethod)}
                className="text-xs text-civic hover:text-civic-light font-medium underline underline-offset-2"
              >
                How compass positions are calculated
              </button>
              {showCompassMethod && (
                <p className="text-xs text-muted leading-relaxed mt-2 max-w-lg">
                  Compass positions are estimated from your and each candidate's answers to the same 20 questions. The horizontal axis reflects economic policy (public investment vs. markets); the vertical axis reflects social governance approach (authority vs. civil liberties). These are not measures of partisan affiliation.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. Fix anything that comes up before moving on — likely candidates for mistakes: a missed import, or the Recharts tooltip generic noted in Task 6.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ResultsDashboardPage.tsx
git commit -m "Wire redesigned radar and compass charts into results dashboard"
```

---

### Task 10: Full verification pass

**Files:** none (verification only).

- [ ] **Step 1: Type-check the whole frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean, zero errors.

- [ ] **Step 2: Production build**

Run: `cd frontend && npm run build`
Expected: Vite build succeeds with no errors.

- [ ] **Step 3: Manual check — desktop width**

Run `cd frontend && npm run dev`, open the printed URL, and navigate to a results page with real data (take the questionnaire against a ZIP with researched candidates, or reuse an existing session if `results` is already populated). At a desktop-width browser window (≥1024px):
- Confirm the "Compare candidates visually" section renders below the match-cards/actions grid, full width, radar and compass side by side.
- Confirm the radar chart shows only the default top-3-5 candidates plus a dashed "You" outline, with the selector panel to its right (not a Recharts `<Legend>` inside the plot).
- Hover a candidate row in the selector — its radar polygon and compass point should both visually pop (thicker stroke / larger dot / outline) while others fade.
- Click a candidate's name in the selector — it should "pin" (same highlight, persists without hovering); click again to unpin.
- Confirm category axis labels on the radar wrap onto 2 lines instead of being clipped, and hovering a still-truncated label shows the full name via native tooltip.
- Confirm compass points show only initials by default, with the pinned/hovered candidate's full name appearing near its point, and the `CompassDetailsPanel` showing exact economic/governance numbers for whichever candidate is active.
- Click "Expand" on each chart: confirm a large modal opens, the chart resizes to fill it, all selections/highlights carry over, closing via the X button, clicking outside, and pressing Escape all work, and focus returns to the "Expand" button afterward. Tab through the modal to confirm focus stays trapped inside it.

- [ ] **Step 4: Manual check — mobile width**

Resize the browser (or use device emulation) to ~375px width:
- Confirm the CandidateSelector stacks below the radar chart (not beside it) and no horizontal scrollbar appears anywhere in the section.
- Confirm the compass SVG scales down (via its `viewBox`) without clipping any axis label text, and its details panel stacks below it.
- Confirm the "How compass positions are calculated" disclosure text stays within the viewport width and reads at normal body-copy size.

- [ ] **Step 5: Commit (only if Steps 1-4 required fixes)**

If any fixes were needed during verification, stage and commit them:

```bash
git add frontend/src
git commit -m "Fix issues found during chart redesign verification"
```

If no fixes were needed, skip this step — nothing to commit.

---

## Self-Review

**Spec coverage:**
- Legend outside plot / controls beside-desktop-below-mobile / margins / label wrap / tooltip fallback / reduced whitespace / transparent fills+strokes / subtle gridlines / not-all-candidates-by-default / fade-on-hover / tooltips / chart sizing → Task 6 (`IssueRadarChart`) + Task 9 (layout grid).
- Compass responsiveness / quadrant subtlety / "You" marker / initials-by-default / hover-focus-selection full name / selected-candidate label / collision handling via jitter+leader-lines / cluster indication / tooltips / details panel / mobile readability / axis headings outside plot → Task 7 (`IdeologicalCompassChart` + `CompassDetailsPanel`).
- Shared color, shared selection state, default top 3-5, searchable/scrollable selector with checkboxes + 3 bulk actions, click-to-highlight from selector/legend, hover-to-emphasize/fade, non-color distinction (outline/opacity), accessible tooltips/keyboard controls → Tasks 1, 3, 5, and wired via Task 9.
- Expand button → modal, preserved selections, functional tooltips/controls, correct resize, close button, Escape, focus trap, focus restore → Tasks 4 and 8. Pan/zoom explicitly skipped per the spec's own fallback clause ("a larger responsive modal is enough" when the chart library doesn't support pan/zoom cleanly) — noted as a limitation, no "Reset view" button since there's no zoom/pan to reset.
- Explanation text sizing/width/line-height/placement/collapsible methodology → Task 9 (`showCompassMethod` disclosure, `max-w-lg`, `text-xs`, `leading-relaxed`, directly under the chart grid).
- Desktop/mobile layout direction → Task 9 (new full-width section below the match-cards grid, `grid lg:grid-cols-2` for the two chart cards, each internally `grid lg:grid-cols-[1fr_XXXpx]` for chart+panel, collapsing to a single stacked column below `lg`).
- "Reuse existing data/APIs/matching logic/routing/filters" → confirmed no changes to `api.ts`, `context/appData.tsx`, `context/nav.tsx`, or `App.tsx` anywhere in this plan.

**Placeholder scan:** no TBDs; every step has complete, real code.

**Type consistency:** `candidateKey`, `RadarSeriesCandidate`, `CompassCandidate`, `SelectorCandidate`, `SelectableCandidate`, `UseCandidateSelectionResult` are each defined once and referenced with matching names/shapes across every task that consumes them (cross-checked Task 3 → Tasks 5/6/9, Task 7 → Task 9, Task 1 → Task 9).

## Known limitations (carried into the final summary, not fixed by this plan)

- No test runner exists in this frontend; verification is `tsc --noEmit` + manual browser checks, not automated tests. Adding a test framework was treated as out of scope (new dependency, not requested).
- Pan/zoom inside the expanded modal is not implemented — Recharts has no clean pan/zoom for `RadarChart`, and the compass is hand-rolled SVG, so per the spec's own fallback clause this is left as "a larger responsive modal" only.
- Modal focus-restore relies on `document.activeElement` at open time being the "Expand" button; Safari does not always focus `<button>` elements on click, so focus-restore may occasionally land on `<body>` instead of the button in Safari specifically. Not fixed here (would require passing an explicit trigger ref through `ChartCard`, adding coupling for a single-browser edge case).
- Radar category-label collision handling is wrap-plus-tooltip, not true collision-aware placement (Recharts' `PolarAngleAxis` has no built-in collision API) — acceptable per the spec's own guidance that leader lines/tooltips/side panels are the fallback when true collision avoidance isn't available.

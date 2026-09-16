# Queen Anne's County Pilot (Design)

## Context

`ElectMatch_Queen_Annes_Product_Demo_v19_1.pdf` is a product-demo deck
pitching a curated, hand-verified pilot of ElectMatch scoped to a single
jurisdiction: Queen Anne's County, Maryland, for the November 2026 general
election. It shows a distinct voter flow (ZIP + county confirmation →
categorized ballot → paired candidate-profile race pages → a "how we
source" methodology page → a one-question-per-screen questionnaire → a
results page that hides match percentages until enough verified positions
exist) plus two internal slides describing the pilot's own operating model
(sourcing pipeline, phase 1/2 roadmap).

The existing app (`frontend/`, `backend_api.py`, `election_lookup.py`,
`questionnaire_scoring.py`) is a live, nationwide ZIP-search tool: enter
any US ZIP, get real-time Tavily-searched + Anthropic-synthesized
candidate research, take a 20-question/7-category questionnaire, see
match percentages. State is keyed by `office` (`"mayor" | "county" |
"us_house"`), and assumes exactly one race per office per ZIP search.

Per discussion with the user:
- The QAC pilot is a **real, functioning** experience (not a static
  mockup), built **alongside** the national flow, not replacing it.
- Candidate data should be **actually researched** (real 2026 QAC
  candidates), not the deck's placeholder names, verified against
  authoritative sources the way the deck itself describes (official
  records, campaign sites, meeting minutes, local reporting).
- The questionnaire stays the existing 20-question/7-category flow,
  restyled only where needed — not shortened to the deck's illustrative
  "8".

## Scope

In scope:
- A new, isolated "pilot" data path: one static, hand-curated dataset for
  Queen Anne's County (races, candidates, sourced positions mapped onto
  the *existing* 20 question IDs), served by one new backend endpoint.
- Five new frontend pages implementing the deck's voter-facing screens
  (screens 1-7): find-my-ballot (ZIP + county), ballot (categorized race
  list), race (paired candidate profiles), how-we-source (static
  methodology), and results (per-issue comparison with demo-mode gating).
- Reusing the existing `QuestionnairePage`, `/api/questions`, and
  `/api/results` unchanged in logic; only a small mode-routing addition to
  `QuestionnairePage` so it can send a pilot user back to the pilot
  results page with the pilot's candidate data instead of the national
  results page.
- A "how we source" static content page describing the same sourcing
  pipeline as the deck's screen 5 (candidate interviews, questionnaire,
  campaign sites, meeting minutes, local reporting, official records).

Out of scope (flagged during design review, no objection raised):
- Address-level "private location lookup" precision — ZIP + a county
  radio choice is enough to route into the pilot.
- Real persistence/accounts for "Save my guide" — implemented as a
  client-side print/share action, no backend storage of a voter's guide.
- The deck's screens 8-9 (Phase 1/Phase 2 pilot-ops roadmap, QACTV
  transcription pipeline, expansion gate) — internal pitch content about
  how the ElectMatch team operates, not a screen a voter should see. Not
  built as app pages.
- Any change to the national ZIP-search flow, its data model, or its
  office-keyed state (`useAppData`, `election_lookup.py`'s
  `Literal["mayor", "county", "us_house"]` types) — the pilot reads only,
  via new isolated code paths.
- A generalized "multi-seat / grouped race" concept in the national data
  model (Approach B, rejected — see chat). The pilot's own dataset is free
  to have multiple races that don't map 1:1 to a national `office` value;
  nothing about that leaks into the national flow.

## Data model (backend)

New file `pilot_queen_annes.py`, no dependency on `election_lookup.py`'s
`Literal`-restricted dataclasses (avoids fighting that type; this data
never flows through the live-search code path). Local dataclasses:

```python
@dataclass
class PilotSource:
    url: str
    title: str
    published: str | None = None  # e.g. "2026-06-03" or "2026 Q&A", best-effort

@dataclass
class PilotIssuePosition:
    question_id: str        # must be a valid questionnaire_scoring.QUESTIONS id
    position: int            # 1-5, same scale as voter answers
    confidence: str           # "explicit" | "strong_inference" | "weak_inference" | "speculative"
    summary: str              # one-sentence plain-English statement of the position
    source: PilotSource | None = None   # None only when confidence == "speculative"

@dataclass
class PilotCandidate:
    name: str
    party: str | None          # None for nonpartisan races (e.g. Board of Education)
    incumbent: bool
    bio: str | None            # one paragraph, sourced; None if not publicly available
    priorities: list[str]      # short bullet list of stated campaign priorities
    positions: list[PilotIssuePosition]
    profile_sources: list[PilotSource]  # general bio/priorities sources (not per-issue)

@dataclass
class PilotRace:
    id: str                    # e.g. "county-commissioner-at-large"
    office_label: str          # e.g. "County Commissioner at Large"
    group: str                 # ballot section, e.g. "Countywide"
    description: str           # "What this office controls" -- one sentence, shown on ballot + race page
    election_date: str         # "2026-11-03"
    candidates: list[PilotCandidate]

@dataclass
class PilotBallot:
    jurisdiction_name: str     # "Queen Anne's County, Maryland"
    updated: str                # "2026-09-14", shown as "verified against ... updated <date>"
    races: list[PilotRace]
```

`"Other county offices"` (State's Attorney, Clerk of the Circuit Court,
Register of Wills, Orphans' Court) is **not** one `PilotRace` — it's
several real races, each its own `PilotRace` entry, all sharing
`group == "Countywide"`. The ballot page groups by `group`; within
"Countywide" it additionally clusters races the deck bundled into one
card (see Frontend below) so the UI still shows one summary row for that
cluster while the underlying data — and the race page it links to — stays
per-office-accurate. This keeps the data model honest (never claims
State's Attorney and Clerk are "the same race") while matching the deck's
denser ballot layout.

Position IDs are drawn from the existing `QUESTIONS` list in
`questionnaire_scoring.py` — e.g. a commissioner candidate's stated view
on the county tax rate maps to `taxes_shortfall`; a school-construction
statement maps to `education_funding_levy`; a growth/zoning statement to
`housing_zoning_density`; a roads-funding statement to
`transportation_funding_mechanism`; a farmland/waterways statement to
`environment_climate_resilience` or `environment_parks_vs_development`.
Not every candidate will have a sourced position for every question —
that's expected and is exactly what produces the deck's "Source required"
/ demo-mode states, via the *existing* `confidence == "speculative"` /
`overall_pct == null` handling already in `questionnaire_scoring.py` and
`backend_api.py`. No scoring-logic changes are needed.

### New endpoint

```
GET /api/pilot/queen-annes
```
Returns the whole `PilotBallot` serialized (races → candidates →
positions/sources), following the same `_position_to_dict`-style
serialization pattern already in `backend_api.py`. One call, loaded once
by the frontend on entering the pilot — the dataset is small (a handful
of races, a dozen-ish candidates), so there's no reason to paginate or
split it into per-race requests the way the live-search flow's
`/api/candidates/research` is split (that split exists because live
research is slow and per-race; this data is already fully loaded at
server start).

No new POST endpoints: the questionnaire and results scoring are served
by the *existing* `/api/questions` and `/api/results` — the pilot frontend
just needs to shape its candidates into the same
`{name, office, positions, emphasis}` request body `/api/results` already
accepts. `office` in that request is a free-form label already (see
`questionnaire_scoring.py` — it doesn't touch `office` at all), so pilot
races can pass their own `office_label` string there with no backend
change.

`emphasis` (the OSINT "how much do they talk about this category" 1-5
score) is populated the same way the live pipeline does: derived
per-candidate from how many of their sourced positions fall in each
category, capped at 5. A small helper in `pilot_queen_annes.py` computes
it once at data-authoring time rather than at request time (the dataset
is static, so there's no reason to recompute it per request).

## Frontend

### New context: `PilotDataProvider` / `usePilotData()`

Parallel to `AppDataProvider`, not layered on top of it. Holds:
- `ballot: PilotBallot | null`, `status: FetchStatus` — loaded once via
  `ensureBallotLoaded()`, called from the first pilot page a user hits.
- `computePilotResults(raceId): Promise<void>` — takes the *shared*
  `quizAnswers` / `selectedIssueCategories` from `useAppData()` (the
  questionnaire's answer state stays a single source of truth app-wide;
  only the candidate side of the `/api/results` call differs) and that
  race's candidates, calls `/api/results`, stores the response keyed by
  `raceId` so multiple race results can be viewed without re-computing.
- `results: Record<string, ResultsResponse>`, `resultsStatus`,
  `resultsError` per race id.

`App.tsx` wraps the tree in both providers (`AppDataProvider` stays
exactly as-is; `PilotDataProvider` added alongside it), so pilot pages can
call both `useAppData()` (for quiz state) and `usePilotData()` (for
ballot/results).

### New pages + routes

`types.ts`'s `PageName` union gains: `'qac-find' | 'qac-ballot' |
'qac-race' | 'qac-sourcing' | 'qac-results'`.

1. **`PilotFindBallotPage`** (`qac-find`) — ZIP input + a county radio
   (Queen Anne's County / Kent County, matching the deck's screen 1,
   since QAC ZIPs can cross into Kent County). Selecting a non-QAC county
   shows a short "not available yet" message instead of erroring — this
   pilot only covers Queen Anne's County. On continue, calls
   `ensureBallotLoaded()` and navigates to `qac-ballot`.

2. **`PilotBallotPage`** (`qac-ballot`) — races grouped by `group`
   ("Countywide" today; the data model supports more groups later without
   a code change), styled after the deck's screen 2: colored left-border
   race rows, candidate names, one-line "what this office controls"
   description, "View race" link. The "Other county offices" cluster
   (State's Attorney / Clerk / Register of Wills / Orphans' Court) renders
   as one summary row that expands to a small in-page list of its
   constituent races rather than linking straight to a single race page,
   since there are several distinct races behind it.

3. **`PilotRacePage`** (`qac-race`, param: `raceId`) — mirrors the deck's
   screens 3-4: candidate cards side by side (bio, priorities, sourced
   positions list, "POSITIONS REQUIRE SOURCES" badge when a candidate has
   zero sourced positions), a "Questions used for both candidates" strip
   listing the categories both candidates have at least one sourced
   position in, and a "Compare answers" button that routes to
   `quiz` with a nav param `{ mode: 'qac', raceId }`.

4. **`PilotSourcingPage`** (`qac-sourcing`) — static content, no fetch;
   the deck's screen 5 table (source type → evidence captured → why it
   matters) plus the "AI extracts a proposed position · a reviewer checks
   the source · ElectMatch links the evidence" strip. Linked from the
   race page ("How we source positions") and the ballot page footer.

5. **`PilotResultsPage`** (`qac-results`, param: `raceId`) — mirrors the
   deck's screen 7: per-issue rows (question text, "Your answer",
   candidate position(s) or "Source required", "View source" link when a
   source exists), and a demo-mode banner ("Candidate match percentages
   remain hidden until enough verified positions are available") shown
   whenever `overall_pct` comes back `null` for a candidate in that race
   — reusing the existing null-handling from `/api/results`, no new
   threshold logic invented client-side. A "Save my guide" button
   triggers `window.print()` (a real, working action, scoped honestly —
   no claim of saved/synced state).

### `QuestionnairePage` change (small, additive)

Reads an optional nav param `mode` (`'national' | 'qac'`, default
`'national'`) and `raceId` (when `mode === 'qac'`). The only behavior
that changes: the final "View Results" button calls
`computePilotResults(raceId)` + navigates to `qac-results` (with
`raceId`) instead of the national `computeResults()` + `results`. Every
other part of the questionnaire (categories stage, 20-question stage,
progress header, answer buttons) is untouched — it's the same instrument
either way, which is the point of keeping one questionnaire.

### Nav / discovery

`Nav.tsx` gets one new link, "Queen Anne's Pilot" → `qac-find`, alongside
the existing links. `HomePage` gets a small callout (not a redesign of
the hero) pointing at the pilot, since it's the more complete experience
today.

## Data sourcing plan

Real candidates and positions for the races in scope (County
Commissioner, Board of Education, Sheriff, State's Attorney, Clerk of the
Circuit Court, Register of Wills, Orphans' Court — exact seat counts and
at-large-vs-district structure to be confirmed against Maryland State
Board of Elections filings and QAC's own government site) are being
researched now and will populate `pilot_queen_annes.py` directly as
Python literals — this is hand-curated data, not something the live
Tavily/Anthropic pipeline touches, matching the deck's "AI extracts, a
reviewer checks the source, ElectMatch links the evidence" model (the
"reviewer" here is this implementation pass). Every non-`speculative`
`PilotIssuePosition` must carry a real, checkable `source.url`.

## Testing

- Backend: `test_pilot_queen_annes.py` (new) — dataset integrity (every
  `question_id` used is a real `questionnaire_scoring` question id, every
  non-speculative position has a source, `/api/pilot/queen-annes` returns
  a well-formed payload).
- Frontend: `npx tsc --noEmit && npx vite build` must stay clean; no new
  test framework introduced (none exists for the frontend today beyond
  type-check + build, matching current repo convention).
- Manual: walk the full pilot flow in a running dev server (find → ballot
  → race → sourcing → quiz → results) before calling this done, per the
  project's "test the golden path in a browser" convention.

## Open questions carried into implementation

- Exact QAC 2026 ballot structure (commissioner at-large vs. by-district,
  number of Orphans' Court seats up this cycle, which races are
  contested) is pending confirmation from official/news sources —
  `pilot_queen_annes.py`'s race list is built from that research, not
  assumed from the deck.

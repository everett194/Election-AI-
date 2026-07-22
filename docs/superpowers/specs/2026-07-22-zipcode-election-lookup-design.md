# Zip Code → Local Election Lookup (Design)

## Context

`problemstatement.md` describes a local-election information and
candidate-alignment platform. `datamechanism.md` describes the full target
data architecture: source registry, tiered source authority, verification
rules, contradiction handling, versioning, staleness tracking, and a human
review queue. That document explicitly recommends an "Initial Prototype"
built on fictional data first.

This spec covers a narrower, concrete step: wire `userinterface.py`'s
zip code stub to a real, live lookup. The user asked for real web search
against arbitrary zip codes now, with results that are as accurate as a
single automated pass reasonably can be — not the full versioned,
human-reviewed system datamechanism.md describes long-term. That larger
system remains future work.

## Scope

For a given zip code, find and display, limited to:

- Mayoral race (if the zip's city has one)
- County-level race(s)
- U.S. House race for that district

...whichever is the next election (primary or general) for each. For each
race: candidates running, and a short summary of what each stands for.

Out of scope for this pass: school board, state legislature, judicial
races, ballot measures, alignment questionnaire, persistent database,
recurring recrawl, contradiction resolution workflow, human review queue.
(All of these are real parts of datamechanism.md's long-term vision, just
not this iteration.)

## Architecture

```
userinterface.py (Streamlit UI)
        |
        v
election_lookup.py (search + extraction)
        |
        v
Anthropic API (web search tool enabled)
```

`election_lookup.py` owns all interaction with the Anthropic API and all
parsing of its output into typed records. `userinterface.py` only renders
what it's given. This separation matches datamechanism.md's
discovery/retrieval/extraction split, condensed for a single-pass MVP.

### Data flow

1. User enters a zip code and clicks "Find my elections" (a button, not
   live-on-keystroke, to bound API cost).
2. `election_lookup.find_local_elections(zipcode)` is called once per
   click. Results are cached in `st.session_state` keyed by zip code, so
   re-rendering the page (a Streamlit rerun happens on every widget
   interaction) does not re-trigger a paid API call for the same zip.
3. One Anthropic Messages API call is made with the server-side
   `web_search` tool enabled. The prompt instructs the model to:
   - Resolve the zip code to its city (if it has its own mayor), county,
     and U.S. congressional district, preferring official sources
     (state/county/city election authority sites, house.gov) first.
   - For each of the three race types in scope, find the next election
     (primary or general, whichever is soonest) with its date and type.
   - For each race, list candidates and, for each candidate, 2-4 bullet
     points on stated positions/priorities.
   - For every fact returned, include a confidence level and the source
     URL(s) it came from.
   - Explicitly return nothing (omit the field / leave it null) rather
     than invent a position when no documented source exists.
4. The model's final response is parsed as JSON into the dataclasses
   below. Malformed/unparseable output is treated as a lookup failure,
   shown to the user as an error — never silently swallowed into an
   empty-but-successful result.
5. `userinterface.py` renders three expandable sections (Mayoral / County
   / U.S. House). Each candidate is a card showing name, party (if known),
   incumbency (if known), stance bullets each tagged with a confidence
   badge, and source links. Missing info renders literally as "No
   documented position found."

### Data models (`election_lookup.py`)

Simplified versions of datamechanism.md's `Election`/`Candidate`/
`CandidatePosition`, dropping fields that only make sense with a
persistent versioned database (`lastVerifiedAt`, version history,
`reviewerStatus`, etc. — not applicable to a stateless per-query lookup):

```python
@dataclass
class Source:
    url: str
    title: str | None

@dataclass
class Position:
    summary: str
    confidence: Literal["high", "medium", "low"]
    sources: list[Source]

@dataclass
class Candidate:
    name: str
    party: str | None
    incumbent: bool | None
    positions: list[Position]  # empty list -> "No documented position found"

@dataclass
class Race:
    office: Literal["mayor", "county", "us_house"]
    jurisdiction_name: str
    election_date: str | None  # None if not found
    election_type: Literal["primary", "general"] | None
    candidates: list[Candidate]
    notes: str | None  # e.g. "no mayoral race found for this zip"

@dataclass
class LookupResult:
    zipcode: str
    races: list[Race]
    retrieved_at: str  # ISO timestamp, shown in the UI
```

## Accuracy handling

This is the part that matters most given the user's explicit accuracy
requirement, and directly follows datamechanism.md's own rules rather than
inventing new ones:

- Every position shown carries a confidence label. High confidence only
  when the position is explicit and sourced (candidate's own site,
  official statement, recorded vote) — matching datamechanism.md's
  Verification Rules section.
- No position is ever fabricated to fill a gap. Empty is shown as empty.
- A persistent, non-dismissable disclaimer banner states that results are
  AI-assisted best-effort from a single automated search pass, not
  guaranteed complete or error-free, and that official source links should
  be checked directly — matching datamechanism.md's Final Operating
  Principle.
- Every race and every position displays a "retrieved at" timestamp, so
  staleness is visible even without a recheck/versioning system.

## Configuration

Requires `ANTHROPIC_API_KEY` in the environment at runtime (the user's own
key, billed per search to their account). If unset, the UI shows a clear
setup error instead of failing silently or crashing. The key is never
logged or displayed. `.env` (if used) is gitignored.

## Testing / verification approach

- Unit tests for JSON-parsing/validation logic in `election_lookup.py`
  using fixed, hand-written model-response fixtures (no live API calls in
  automated tests, to keep tests free, fast, and deterministic).
- One real, manual live-API smoke test against a real zip code, with the
  actual output inspected for sanity (plausible race names, dates in the
  future, source URLs that resolve) before calling this done.
- Streamlit headless smoke test (as was done for the original stub) to
  confirm the page still renders without runtime errors.

## Known limitations (stated explicitly, not hidden)

- No persistence: every search is independent; nothing is cached across
  app restarts or shared between users.
- No multi-source contradiction detection: if two sources disagree, the
  model's single pass may only surface one, or may note the disagreement
  inconsistently — this is a known gap versus datamechanism.md's
  Contradiction Handling section.
- No recurring re-verification/staleness tracking beyond the per-query
  "retrieved at" timestamp.
- Zip-to-jurisdiction resolution quality depends on web coverage; small
  or low-coverage jurisdictions may return incomplete results, which
  should render as "not found," not a guess.

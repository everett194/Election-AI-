# Candidate Compass/Radar Mapping (Design)

## Context

`questionnaire.md` (Section 3) already defines voter–candidate compatibility
scoring, and `questionnaire_scoring.compute_candidate_compatibility` already
implements and tests it. `questionnaire_ui.py` currently shows a static
message instead of using it: "Candidate compatibility scoring needs
candidates' own answers to these same 20 questions from a verified source
... That candidate-side data isn't populated yet."

The user asked for exactly that missing piece: for a specific candidate
(e.g. a real candidate in a real race), go find sourced evidence of their
actual positions and plot them on the same radar/compass charts as the
voter's own results — not a guess drawn from party affiliation or general
reputation. `questionnaire.md` Section 5 is explicit about this: candidate
positions must come from sourced, checkable material (direct questionnaire
responses, established third-party candidate questionnaires, voting
records/official statements, reputable local reporting — in that order of
reliability), never invented or inferred, with a visible source citation
per position, and unanswered questions excluded rather than guessed.

This spec covers wiring that up end-to-end: researching one candidate's
answers to the 20 questions with real sources, and plotting the result.

## Scope

In scope:
- A new per-candidate research call that answers as many of the 20
  questionnaire questions as it can find real sourced evidence for.
- An on-demand "map this candidate" trigger in the questionnaire UI,
  scoped to candidates from the race the voter entered the questionnaire
  from.
- Overlaying mapped candidates on the existing compass chart and adding
  their per-category compatibility as a second shape on the existing radar
  chart.
- Showing the overall match %, per-category breakdown, and the sourced
  question-by-question evidence used, per mapped candidate.
- Supporting multiple candidates mapped at once, for side-by-side
  comparison.

Out of scope for this pass: automatically researching every candidate
without a click, researching candidates from races other than the one the
voter entered from, persistent storage across app restarts (session-only,
matching the existing `lookup_cache` pattern), re-verification/staleness
tracking beyond a retrieved-at timestamp, and questions with zero sourced
evidence being scored as neutral (they are excluded, per
`compute_candidate_compatibility`'s existing behavior).

## Architecture

```
questionnaire_ui.py (UI: map button, charts, sourced-evidence display)
        |
        v
election_lookup.py: research_candidate_positions(...)
        |
        v
Anthropic API (web search tool enabled)
        |
        v
questionnaire_scoring.compute_candidate_compatibility (existing, unchanged)
```

`election_lookup.py` gains the new research function and data models,
following its existing pattern (one Anthropic call with the `web_search`
tool, JSON response parsed into typed dataclasses, per-item failure
tolerance). `questionnaire_ui.py` owns triggering it, caching results in
`st.session_state`, and rendering the comparison. No changes to
`questionnaire_scoring.py` — its compatibility math already does exactly
what's needed.

### Data flow

1. Voter opens the questionnaire from a specific race (as today), answers
   all 20 questions, and submits.
2. `userinterface.py` looks up that race's candidates from
   `st.session_state.lookup_cache[from_zip]` (matching `from_office`) and
   passes the candidate list into `render_questionnaire`, in addition to
   the existing `from_office`/`from_zip` strings.
3. Once the voter's results are showing, a new "Compare with candidates"
   section lists each candidate from that race with a "Research and map
   [name]" button.
4. Clicking the button calls
   `research_candidate_positions(zipcode, office, jurisdiction_name,
   candidate, client=None)`:
   - Builds one prompt enumerating all 20 questions (id, text, both
     approaches) from `questionnaire_scoring.QUESTIONS`.
   - Includes what's already known about the candidate (party, incumbent,
     any free-text positions/sources already found during the race
     search) as a head start for the search.
   - Instructs the model to prioritize source tiers in the order
     `questionnaire.md` Section 5 specifies: direct candidate responses to
     this questionnaire > established third-party candidate
     questionnaires (Vote411, Ballotpedia Candidate Connection) > official
     statements/voting records > reputable local reporting > campaign
     materials — and to answer a question on the 1-5 scale only when a
     real source supports it, omitting it otherwise.
   - Uses the `web_search` tool (same `max_uses`-capped, low-effort
     pattern as the existing per-office search) — one call per candidate,
     not one call per question.
5. The response is parsed into a `CandidateIssueProfile` (see Data models)
   and cached in `st.session_state.candidate_profiles`, keyed by
   `(zipcode, office, candidate_name)`, so re-mapping the same candidate in
   the same session is free.
6. `compute_candidate_compatibility` (unchanged) is called with the
   voter's answers/importance and the candidate's `positions` dict to get
   `overall_pct`, `by_category`, and `question_count`.
7. Rendering, per mapped candidate:
   - A card showing overall match %, and "(based on N of 20 questions with
     sourced evidence)" for transparency about coverage.
   - An expandable list of exactly which questions were answered, each
     with its source link — mirroring how existing race-search positions
     already show sources.
   - A point added to the compass chart (`compute_compass_scores` on the
     candidate's `positions`, unchanged function) in a distinct color, with
     a legend.
   - A second polygon added to the radar chart using the candidate's
     `by_category` compatibility percentages (0-100, same scale as the
     voter's own priority polygon), in a distinct color, with a legend
     making clear the two polygons mean different things ("your
     priorities" vs. "compatibility with X").
8. If `question_count` is 0 (no sourced evidence found at all for that
   candidate), show "No sourced positions found for this candidate" instead
   of plotting a point/polygon for them.

### Data models (`election_lookup.py`)

```python
@dataclass
class CandidateIssuePosition:
    question_id: str
    position: int  # 1-5, same scale as the voter's own answers
    confidence: Literal["high", "medium", "low"]
    source: Source  # reuses the existing Source dataclass

@dataclass
class CandidateIssueProfile:
    candidate_name: str
    office: Literal["mayor", "county", "us_house"]
    positions: dict[str, int]  # question_id -> 1-5, feeds compute_candidate_compatibility directly
    sourced_positions: list[CandidateIssuePosition]  # for the sourced-evidence display
```

`positions` is a plain `dict[str, int]` (not wrapped) specifically so it
can be passed straight into
`questionnaire_scoring.compute_candidate_compatibility` and
`compute_compass_scores` without adaptation.

## UI placement

The "Compare with candidates" section appears only after the voter has
submitted their own answers (i.e. `"questionnaire_answers" in
st.session_state`), directly below the existing radar/compass results,
listing candidates from `from_office`'s race only (per the approved scope
decision). Each candidate's "Research and map" button shows a status
indicator while running (same `st.status`/spinner pattern as the main
race search) since this is a real ~30-60s search. Once a candidate's
profile is cached, their button becomes a "Remove from comparison" toggle
(unmapping just hides their chart overlay/card, it does not discard the
cached profile) instead of re-querying the API on every rerun.

## Accuracy handling

Directly follows `questionnaire.md` Section 5, mirroring the accuracy
rules already established in `datamechanism.md` and implemented for race
lookups:

- A position is only recorded when the search finds real, checkable
  evidence; source tier preference matches Section 5's order.
- No fabricated or inferred positions from party/reputation/endorsements.
- Every recorded position carries a confidence label and a source link,
  displayed to the voter.
- Coverage is always shown explicitly ("N of 20 questions") so a thin
  profile reads as thin, not as a complete picture.
- Unanswered questions are excluded from scoring, never defaulted to
  neutral (matches `compute_candidate_compatibility`'s existing,
  tested behavior — no changes needed there).

## Testing / verification approach

- Unit tests for the new JSON-parsing logic in `election_lookup.py`
  (`research_candidate_positions` / response parsing), using fixed
  hand-written fixtures, mocked client — same pattern as
  `test_election_lookup.py`. Cover: partial coverage (some questions
  unanswered), zero coverage, and malformed-response handling.
- No new tests needed for `questionnaire_scoring.py` — its candidate
  compatibility function is already tested and unchanged.
- Manual live-API smoke test against a real candidate/race before calling
  this done, inspecting that returned sources actually resolve and support
  the claimed position.
- Streamlit headless smoke test of the new "Compare with candidates"
  section and chart overlays.

## Known limitations (stated explicitly)

- Coverage depends on web coverage of the specific candidate/race; minor
  local races may yield very few or zero sourced positions, which is
  correct behavior (honest and thin), not a bug.
- No persistence across app restarts — candidate research is session-only,
  matching the existing `lookup_cache` pattern.
- No re-verification/staleness tracking beyond the implicit
  once-per-session cache; a candidate's stated views could change after
  research is cached.
- Only candidates from the race the voter entered the questionnaire from
  can be mapped in this pass (explicit scope decision, not a technical
  limitation) — mapping candidates across races is future work if wanted.

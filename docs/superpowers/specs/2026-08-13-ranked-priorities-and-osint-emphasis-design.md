# Ranked Priorities + Candidate Issue-Emphasis Matching (Design)

## Context

The previous redesign (see `2026-08-13-*` git history / `questionnaire_scoring.build_active_questions`)
compressed the questionnaire to a personalized ~8-12 question flow, driven
by an *unordered* set of 1-4 selected priority categories, with a flat
weight (5 for selected, 2 baseline).

The user now wants two changes on top of that:

1. **Ranking, not just selecting.** Voters should express which of their
   priority issues matters *most*, not just which ones matter. Priorities
   should still never exclude other issues from scoring.
2. **Longer questionnaire again.** The compression traded length for
   personalization; the user now wants more questions answered, with
   ranking driving *weight and order* rather than *which questions appear
   at all*.
3. **Candidates should match "more or less" based on how much they
   actually talk about an issue** — not just whether their sourced
   position agrees with the voter's. This is a new signal, pulled from
   broad OSINT (official sites, social media, campaign materials), that
   should move the match percentage itself, not just be a footnote.

This spec supersedes the "build_active_questions" subsetting design while
keeping everything else from that redesign (results dashboard, candidate
research pipeline shape, evidence/confidence model, compass axis scoring)
intact.

## Scope

In scope:
- Tap-to-rank UI for 1-4 priority categories (Stage 1), replacing
  tap-to-select.
- Always asking all 20 questions, ordered by rank (Stage 2), replacing the
  12-question personalized subset.
- A graduated voter-side weight table (rank 1-4 → 5/4/3/2, unranked → 1)
  replacing the flat 5/2 scheme.
- A graduated priority radar (100/80/60/40/20 by rank, unranked-but-always-
  answered → 20) replacing the flat 100/40/0 scheme.
- A new per-candidate, per-category "emphasis" score (1-5) derived from
  OSINT evidence (official site, X/Twitter, Facebook, Instagram, campaign
  materials), folded into the *existing* broad research pass (no new
  sequential research step — same wall-clock search time).
- Blending that emphasis score into the effective weight used for THAT
  candidate's compatibility score — weight becomes per-candidate, not
  shared across all candidates.
- Updated backend request/response schema, frontend state, and tests.

Out of scope:
- Any UI surfacing of the raw emphasis score in v1 (data flows through the
  API and is stored, but no chart/badge is required this pass).
- Changing the compass scoring (economic/social axes) — untouched.
- Changing the underlying `compatibility = 1 - |voter - candidate| / 4`
  per-question formula — untouched. Only the *weight* applied to each
  question changes.
- Persisting rank/emphasis data server-side beyond the existing
  best-effort `answer_storage`.

## Voter Flow

**Stage 1 — rank your priorities.** Same 7 category cards. Tapping a card
assigns the next rank (①②③④ badge appears); tapping a ranked card again
removes it and renumbers the rest. Still capped at 4 ranked categories,
still optional to rank fewer (1-4), same "every issue still counts, ranked
ones just count more" messaging (copy updated to mention order). Single
Continue button, unchanged mobile/desktop compactness requirement.

**Stage 2 — all 20 questions.** No more subsetting. Every voter answers
every question in the bank, in this order:
1. All questions in the rank-1 category (original within-category order).
2. All questions in the rank-2 category.
3. All questions in the rank-3 category.
4. All questions in the rank-4 category.
5. Every remaining (unranked) category, in `CATEGORY_LABELS`' fixed
   canonical order — so voters who ranked fewer than 4 still get a
   deterministic tail order.

Progress display becomes "Question N of 20." 1-5 scale, Not Sure/Skip,
Previous/Next, "Edit your priorities" link back to Stage 1 — all unchanged
from the previous redesign. Changing ranks mid-flow re-sorts the remaining
question order but never discards already-given answers (every question is
always in the active set now, so no answer can ever become orphaned/
unsubmittable — this actually simplifies the previous redesign's "answers
to removed questions must not be submitted" concern away entirely, since
nothing is ever removed).

**Submission/results** — unchanged mechanically; copy updates from "of 12"
etc. references to "of 20."

## Data Model & Weighting

### Question metadata changes (`questionnaire_scoring.py`)

- Remove `is_core`, `MAX_ACTIVE_QUESTIONS`, `MAX_ADDITIONAL_PER_CATEGORY`,
  and `build_active_questions` — no longer meaningful once every voter
  answers all 20 questions.
- Keep `selection_priority` as a within-category tie-break for the new
  ordering helper (harmless, avoids relitigating a stable order per
  category).
- Keep `research_terms` — still used to build OSINT queries.

### New ordering helper

```python
def order_questions_by_rank(ranked_categories: list[str]) -> list[Question]:
    """All 20 questions, reordered: ranked categories first (in rank
    order, original within-category order), then every remaining category
    in CATEGORY_LABELS' fixed order. `ranked_categories` is 0-4 category
    ids, index 0 = rank 1. Every question always appears exactly once."""
```

### Voter-side rank weight

```python
RANK_WEIGHTS = {1: 5, 2: 4, 3: 3, 4: 2}   # by position in ranked_categories (1-indexed)
BASELINE_WEIGHT = 1                        # unranked category, still always answered
```

`derive_effective_weights(ranked_categories, answered_question_ids)`
returns, per answered question id, `RANK_WEIGHTS.get(rank, BASELINE_WEIGHT)`
— same shape/signature as before, just a graduated lookup instead of a
binary one. Still: skipped/unanswered questions never appear, still never
zero.

### Candidate-side emphasis multiplier

```python
def emphasis_multiplier(emphasis_1_to_5: int | None) -> float:
    if emphasis_1_to_5 is None:
        return 1.0  # no OSINT signal for this category -> neutral, not penalized
    return 0.7 + 0.15 * (emphasis_1_to_5 - 1)   # range 0.7x - 1.3x
```

### Per-candidate effective weight (new)

```python
def derive_candidate_weights(
    ranked_categories: list[str],
    answered_question_ids: Iterable[str],
    candidate_emphasis: dict[str, int],
) -> dict[str, float]:
    base = derive_effective_weights(ranked_categories, answered_question_ids)
    return {
        qid: w * emphasis_multiplier(candidate_emphasis.get(QUESTIONS_BY_ID[qid].category))
        for qid, w in base.items()
    }
```

`compute_candidate_compatibility`'s formula and signature are unchanged —
it still just takes `voter_answers, voter_importance, candidate_positions`.
What changes is that `backend_api.get_results` now calls
`derive_candidate_weights` **once per candidate** (using that candidate's
own `emphasis` dict) instead of computing one shared weight dict for all
candidates.

### Radar (voter priorities only, candidate-independent)

```python
RADAR_SCORE_BY_RANK = {1: 100.0, 2: 80.0, 3: 60.0, 4: 40.0}
RADAR_BASELINE_SCORE = 20.0   # unranked, but >=1 question in it was answered
RADAR_UNREPRESENTED_SCORE = 0.0   # unranked AND every question in it was skipped
```

`compute_radar_scores(ranked_categories, answered_question_ids)` keeps its
signature and its three-tier shape: a **ranked** category always scores its
graduated rank value (100/80/60/40) regardless of whether its questions
were answered — ranking itself expresses the priority. An **unranked**
category scores 20 if the voter answered at least one of its questions
(all 20 are presented, but Not-Sure/Skip is still allowed per-question), or
0 if every question in it was skipped. Since all 20 questions are now
always presented, 0 is rarer than in the previous design but still a real,
reachable case (a voter who skips every question in an unranked category).

## OSINT Emphasis Research

Folded into the **existing always-broad initial pass**
(`research_candidates_via_tavily`) — no new sequential research step, so
total search wall-clock time is unaffected (Tavily queries already run
fully parallel; more queries in the same batch cost money/rate-limit
headroom, not time).

- `_candidate_search_queries` grows from 7 to ~12 per candidate, adding:
  `official website platform issues`, `X Twitter`, `Facebook page`,
  `Instagram`, `campaign social media` variants.
- The single Claude synthesis call per race (already reading all gathered
  evidence, `use_web_search=False`) gets an extended response schema:
  alongside `positions`, each candidate entry also includes
  `"emphasis": [{"category": "<id>", "score": 1-5, "note": "<one line>"}]`
  for every category the evidence supports a judgment on. Missing category
  → absent from the list → treated as `None` (neutral multiplier), not 0.
- New field: `CandidateIssueProfile.emphasis: dict[str, int]`.
- `_profile_to_dict` in `backend_api.py` serializes `emphasis` through to
  the API response (for future UI use; not required to render anything
  new this pass).
- The existing priority-category *gap-filling* pass (for a voter's ranked
  categories missing sourced **positions**) is unaffected — emphasis is
  voter-independent and always computed once, up front, same as positions.
- Speculative/fallback profiles (no real evidence at all) get
  `emphasis = {}` → every category defaults to neutral 1.0×, so a
  candidate with thin overall web presence isn't penalized purely for
  being under-covered rather than actually silent on an issue.

## API Changes

- `ResultsRequest.selected_categories: list[str]` →
  `ResultsRequest.ranked_categories: list[str]` (ordered, index 0 = rank 1,
  max length 4).
- `get_results` now loops per candidate, builds that candidate's weight
  dict via `derive_candidate_weights(body.ranked_categories, body.answers.keys(), candidate.emphasis)`,
  then calls the unchanged `compute_candidate_compatibility`.
- `CandidateResultInput` (the per-candidate payload the frontend already
  sends into `/api/results`) gains `emphasis: dict[str, int] = {}` so the
  frontend can pass through what it already has cached from
  `/api/candidates/research` without a second fetch.
- `/api/candidates/research`'s response `profiles[name]` gains `emphasis`
  in `_profile_to_dict`.
- `/api/questions` response drops `is_core`; keeps `selection_priority`,
  `research_terms`.

## Frontend Changes

- `frontend/src/lib/activeQuestions.ts` → replaced by
  `frontend/src/lib/questionOrder.ts` exporting `orderQuestionsByRank`
  (mirrors the backend helper; used for the Stage 2 flow order and
  progress display only — backend remains authoritative for weights).
- `appData.tsx`: `selectedIssueCategories: string[]` becomes an ordered
  rank array; `toggleIssueCategory` becomes rank-aware (tap ranked card →
  remove + renumber remaining; tap unranked card → append if under 4).
  `computeResults` sends `ranked_categories` and each candidate's cached
  `emphasis` map inside `candidatesForScoring`.
- `QuestionnairePage.tsx`: Stage 1 cards render a rank badge instead of a
  checkmark; Stage 2 walks all 20 questions via `orderQuestionsByRank`;
  progress copy becomes "Question N of 20."
- `ResultsDashboardPage.tsx` / `IssueRadarChart.tsx`: no code change needed
  beyond what already reads `results.radar` — values just come back
  graduated (100/80/60/40/20) instead of (100/40/0).
- `api.ts`: `ApiQuestion` drops `is_core`; `getResults` body takes
  `ranked_categories` and per-candidate `positions` + `emphasis`;
  `CandidateProfile` gains `emphasis: Record<string, number>`.

## Testing

- `test_questionnaire_scoring.py`: rewrite rank-weight tests (5/4/3/2/1
  table), rewrite radar tests (100/80/60/40/20), add
  `order_questions_by_rank` tests (all 20 present exactly once,
  deterministic regardless of nothing since order *is* rank-derived now,
  ranked categories' questions come first in rank order, remaining
  categories in canonical order), add `derive_candidate_weights` /
  `emphasis_multiplier` tests (known emphasis scales weight up/down within
  0.7x-1.3x, missing emphasis → neutral 1.0x, speculative-only profile →
  all neutral).
- `test_election_lookup.py`: assert the broad pass's query list includes
  the new OSINT/platform queries; assert `parse_candidates_evidence_response`
  (or its extended counterpart) parses `emphasis` alongside `positions`;
  assert a candidate entry with no emphasis data in the response still
  produces `emphasis == {}` rather than raising.
- New `backend_api`-level (or `questionnaire_scoring`-level) test: two
  candidates with **identical** sourced positions but different emphasis
  scores on the voter's rank-1 category produce **different**
  `overall_pct`, proving the blend actually moves the number.
- Frontend: `npm run build` + `npx tsc --noEmit` must stay clean; no
  frontend test runner exists in this repo, matching the previous pass's
  finding.

## Migration Notes (removed from the previous redesign)

- `Question.is_core`, `MAX_ACTIVE_QUESTIONS`, `MAX_ADDITIONAL_PER_CATEGORY`,
  `build_active_questions` (Python) and `buildActiveQuestions`,
  `MAX_ACTIVE_QUESTIONS`, `MAX_ADDITIONAL_PER_CATEGORY` (TS) are deleted,
  not deprecated — nothing else in the codebase should reference them
  after this change lands.
- `ResultsRequest.selected_categories` renamed to `ranked_categories`
  (breaking change to the request shape, acceptable since the frontend and
  backend deploy together).

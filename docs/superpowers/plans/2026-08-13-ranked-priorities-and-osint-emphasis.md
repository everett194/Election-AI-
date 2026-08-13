# Ranked Priorities + Candidate Issue-Emphasis Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current "select 1-4 priority categories, answer a personalized ~8-12 question subset" questionnaire flow with "rank 1-4 priority categories, answer all 20 questions ordered/weighted by rank," and make candidate match percentages blend in a new OSINT-derived "how much does this candidate talk about this issue" emphasis score.

**Architecture:** `questionnaire_scoring.py` stays the single authoritative source for weighting/ordering/radar math (pure functions, fully unit-tested); `election_lookup.py` gains a per-category "emphasis" signal folded into its existing single broad Tavily+Claude research pass (no new sequential step); `backend_api.py` wires the two together per-candidate; the React frontend mirrors only the *ordering* rule client-side (never the weighting) and otherwise just passes the ranked list and emphasis data through.

**Tech Stack:** Python 3.12 / FastAPI / pydantic (backend), React 19 / TypeScript / Vite (frontend), pytest, Tavily search API, Anthropic API (`claude-sonnet-5`).

## Global Constraints

- Backend is the sole authority on weights and scores; the frontend never computes a weight or a percentage itself (existing project rule, unchanged).
- Never assign a weight of 0 to any answered question or any category — unranked/nonselected must always still count (existing project rule, unchanged).
- Never fabricate a candidate position or emphasis score without real OSINT evidence; a missing signal must be treated as *unknown* (neutral), never as a negative signal (spec requirement).
- The candidate-research broad pass must keep running immediately after election search, before any voter priorities are known, and must keep covering all 7 categories (spec requirement, unchanged from the prior redesign).
- No new sequential research round-trip: OSINT emphasis queries fold into the existing broad-pass Tavily fan-out and existing single Claude synthesis call — total wall-clock search time must not increase (spec requirement from this round of changes).
- `compute_candidate_compatibility`'s formula (`1 - |voter - candidate| / 4`, then weighted average) and signature are unchanged — only the weight values fed into it change.
- Every step in this plan that touches Python must leave `pytest` green; every step that touches TypeScript must leave `npx tsc --noEmit` and `npm run build` clean.

---

## Task 1: `questionnaire_scoring.py` — remove subsetting, add `order_questions_by_rank`

**Files:**
- Modify: `questionnaire_scoring.py`
- Modify: `test_questionnaire_scoring.py`

**Interfaces:**
- Produces: `order_questions_by_rank(ranked_categories: Iterable[str]) -> list[Question]` — always returns all 20 `Question` objects, ranked categories' questions first (in rank order, `selection_priority` ascending within a category), then every remaining category in `CATEGORY_LABELS`' fixed order.
- Removes: `Question.is_core`, `MAX_ACTIVE_QUESTIONS`, `MAX_ADDITIONAL_PER_CATEGORY`, `build_active_questions`, `RADAR_SELECTED_SCORE`, `RADAR_ANSWERED_SCORE`, `RADAR_UNREPRESENTED_SCORE` (the last three are replaced in Task 2, not here — remove them here since `build_active_questions` and the radar constants are adjacent).

- [ ] **Step 1: Write the failing tests for `order_questions_by_rank`**

Add to `test_questionnaire_scoring.py`, replacing the `# --- Personalized questionnaire builder (build_active_questions) ---` section (lines 39-101, i.e. everything from `def test_exactly_five_questions_are_marked_core():` through `def test_build_active_questions_never_exceeds_twelve_for_all_seven_categories():` and its body) with:

```python
# --- Question ordering (order_questions_by_rank) -----------------------------


def test_order_questions_by_rank_returns_all_20_questions_exactly_once():
    ordered = order_questions_by_rank(["housing", "safety"])
    assert len(ordered) == 20
    assert {q.id for q in ordered} == set(QUESTIONS_BY_ID.keys())


def test_order_questions_by_rank_puts_ranked_categories_first_in_rank_order():
    ordered = order_questions_by_rank(["safety", "housing"])
    ordered_categories = [q.category for q in ordered]
    # All of "safety"'s questions (rank 1) come before all of "housing"'s (rank 2).
    last_safety_index = max(i for i, c in enumerate(ordered_categories) if c == "safety")
    first_housing_index = min(i for i, c in enumerate(ordered_categories) if c == "housing")
    assert last_safety_index < first_housing_index


def test_order_questions_by_rank_puts_unranked_categories_after_ranked_in_canonical_order():
    ordered = order_questions_by_rank(["environment"])
    ordered_categories = [q.category for q in ordered]
    last_environment_index = max(i for i, c in enumerate(ordered_categories) if c == "environment")
    # "housing" is unranked here and comes before "environment" in CATEGORY_LABELS'
    # canonical order, but environment was explicitly ranked, so it must still lead.
    first_housing_index = min(i for i, c in enumerate(ordered_categories) if c == "housing")
    assert last_environment_index < first_housing_index
    # Among the unranked tail, canonical CATEGORY_LABELS order is preserved:
    # housing comes before taxes.
    first_taxes_index = min(i for i, c in enumerate(ordered_categories) if c == "taxes")
    assert first_housing_index < first_taxes_index


def test_order_questions_by_rank_is_empty_ranked_list_safe():
    ordered = order_questions_by_rank([])
    assert len(ordered) == 20
    assert [q.category for q in ordered][0] == "housing"  # falls straight to canonical order


def test_order_questions_by_rank_ignores_unknown_and_duplicate_categories():
    ordered = order_questions_by_rank(["housing", "housing", "not_a_real_category", "taxes"])
    assert len(ordered) == 20
    ordered_categories = [q.category for q in ordered]
    last_housing_index = max(i for i, c in enumerate(ordered_categories) if c == "housing")
    first_taxes_index = min(i for i, c in enumerate(ordered_categories) if c == "taxes")
    assert last_housing_index < first_taxes_index
```

Also update the import block at the top of `test_questionnaire_scoring.py`:

```python
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    QUESTIONS_BY_ID,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
    derive_effective_weights,
    order_questions_by_rank,
)
```

(`MAX_ACTIVE_QUESTIONS`, `MAX_ADDITIONAL_PER_CATEGORY`, `build_active_questions` are removed from the import; `emphasis_multiplier` and `derive_candidate_weights` are added to this import list in Task 3, not here.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_questionnaire_scoring.py -k order_questions_by_rank -v`
Expected: FAIL with `ImportError: cannot import name 'order_questions_by_rank'`

- [ ] **Step 3: Remove `is_core` from `Question` and delete `build_active_questions`**

In `questionnaire_scoring.py`:

1. In the `Question` dataclass, delete this line:
   ```python
       is_core: bool = False  # one of the 5 baseline questions every voter answers
   ```
   (Keep `selection_priority` and `research_terms` as-is.)

2. In the `QUESTIONS` list, delete the `is_core=True,` line from each of these 5 `Question(...)` entries (identify by `id=`): `housing_zoning_density`, `taxes_shortfall`, `safety_police_funding`, `education_funding_levy`, `accountability_public_input`.

3. Delete these two module-level constants (just below `QUESTIONS_BY_ID`):
   ```python
   MAX_ACTIVE_QUESTIONS = 12
   MAX_ADDITIONAL_PER_CATEGORY = 2
   ```

4. Delete the entire `build_active_questions` function (from `def build_active_questions(selected_categories: Iterable[str]) -> list[Question]:` through its closing `return active`).

5. Delete these three constants (currently just above `compute_radar_scores`):
   ```python
   RADAR_SELECTED_SCORE = 100.0
   RADAR_ANSWERED_SCORE = 40.0
   RADAR_UNREPRESENTED_SCORE = 0.0
   ```
   (Task 2 replaces these with graduated equivalents.)

- [ ] **Step 4: Add `order_questions_by_rank`**

Add this function to `questionnaire_scoring.py`, directly below `QUESTIONS_BY_ID`:

```python
def order_questions_by_rank(ranked_categories: Iterable[str]) -> list[Question]:
    """All 20 questions, reordered: the voter's ranked-priority categories'
    questions first (in rank order, `selection_priority` ascending within a
    category), then every remaining category in CATEGORY_LABELS' fixed
    canonical order. `ranked_categories` is the voter's 0-4 ranked category
    ids, index 0 = rank 1 (only the first 4 are used; unknown or duplicate
    category ids are ignored). Every question always appears exactly once --
    ranking never excludes a question, only reorders it.
    """
    ranked = list(ranked_categories)[:4]
    seen_categories: set[str] = set()
    ordered: list[Question] = []

    def questions_in(category: str) -> list[Question]:
        return sorted(
            (q for q in QUESTIONS if q.category == category),
            key=lambda q: q.selection_priority,
        )

    for category in ranked:
        if category in seen_categories or category not in CATEGORY_LABELS:
            continue
        seen_categories.add(category)
        ordered.extend(questions_in(category))

    for category in CATEGORY_LABELS:
        if category in seen_categories:
            continue
        seen_categories.add(category)
        ordered.extend(questions_in(category))

    return ordered
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest test_questionnaire_scoring.py -v`
Expected: The 5 new `order_questions_by_rank` tests PASS. Other tests will currently FAIL (radar/weight tests still reference the old flat scheme) — that's expected and fixed in Task 2; ignore those failures for this step, but confirm no `ImportError`/`AttributeError` about `is_core`/`build_active_questions` remains anywhere (search: `grep -rn "is_core\|build_active_questions\|MAX_ACTIVE_QUESTIONS\|MAX_ADDITIONAL_PER_CATEGORY" questionnaire_scoring.py test_questionnaire_scoring.py` should return nothing).

- [ ] **Step 6: Commit**

```bash
git add questionnaire_scoring.py test_questionnaire_scoring.py
git commit -m "Replace build_active_questions subsetting with order_questions_by_rank"
```

---

## Task 2: `questionnaire_scoring.py` — graduated rank weights and radar

**Files:**
- Modify: `questionnaire_scoring.py`
- Modify: `test_questionnaire_scoring.py`

**Interfaces:**
- Consumes: nothing new (uses `QUESTIONS_BY_ID`, `CATEGORY_LABELS` from Task 1).
- Produces: `derive_effective_weights(ranked_categories: Iterable[str], answered_question_ids: Iterable[str]) -> dict[str, int]` (signature unchanged from before, values now graduated 5/4/3/2/1 instead of flat 5/2); `compute_radar_scores(ranked_categories: Iterable[str], answered_question_ids: Iterable[str]) -> dict[str, float]` (signature unchanged, values now graduated 100/80/60/40/20/0).

- [ ] **Step 1: Write the failing tests**

In `test_questionnaire_scoring.py`, replace the `# --- Effective weight derivation (derive_effective_weights) ---` section (the block from `def test_selected_category_question_gets_weight_five():` through `def test_derive_effective_weights_skips_unknown_question_id():` and its body) with:

```python
# --- Rank-based effective weight derivation (derive_effective_weights) -------


def test_rank_1_category_question_gets_weight_five():
    weights = derive_effective_weights(["housing"], ["housing_zoning_density"])
    assert weights["housing_zoning_density"] == 5


def test_rank_2_category_question_gets_weight_four():
    weights = derive_effective_weights(["taxes", "housing"], ["housing_zoning_density"])
    assert weights["housing_zoning_density"] == 4


def test_rank_3_category_question_gets_weight_three():
    weights = derive_effective_weights(["taxes", "safety", "housing"], ["housing_zoning_density"])
    assert weights["housing_zoning_density"] == 3


def test_rank_4_category_question_gets_weight_two():
    weights = derive_effective_weights(
        ["taxes", "safety", "education", "housing"], ["housing_zoning_density"]
    )
    assert weights["housing_zoning_density"] == 2


def test_unranked_question_gets_baseline_weight_one_not_zero():
    # taxes_shortfall is answered but "taxes" is not in the ranked list.
    weights = derive_effective_weights(["housing"], ["taxes_shortfall"])
    assert weights["taxes_shortfall"] == 1
    assert weights["taxes_shortfall"] != 0


def test_derive_effective_weights_only_uses_first_four_ranked_categories():
    # A 5th ranked category (shouldn't happen from the UI, which caps at 4,
    # but the function itself must not read past index 3) is treated as unranked.
    weights = derive_effective_weights(
        ["taxes", "safety", "education", "accountability", "housing"], ["housing_zoning_density"]
    )
    assert weights["housing_zoning_density"] == 1


def test_derive_effective_weights_ignores_unanswered_question_ids():
    weights = derive_effective_weights(["housing"], ["housing_zoning_density"])
    assert "taxes_shortfall" not in weights
    assert set(weights.keys()) == {"housing_zoning_density"}


def test_derive_effective_weights_skips_unknown_question_id():
    weights = derive_effective_weights(["housing"], ["not_a_real_question"])
    assert weights == {}
```

Also replace the `# --- Priority radar (compute_radar_scores) ---` section (from `def test_radar_score_is_100_for_selected_category():` through `def test_radar_scores_cover_all_seven_categories():` and its body) with:

```python
# --- Graduated priority radar (compute_radar_scores) -------------------------


def test_radar_score_by_rank_is_graduated():
    scores = compute_radar_scores(["housing", "taxes", "safety", "education"], [])
    assert scores["housing"] == pytest.approx(100.0)
    assert scores["taxes"] == pytest.approx(80.0)
    assert scores["safety"] == pytest.approx(60.0)
    assert scores["education"] == pytest.approx(40.0)


def test_radar_score_is_20_for_unranked_but_answered_category():
    scores = compute_radar_scores(["housing"], ["taxes_shortfall"])
    assert scores["taxes"] == pytest.approx(20.0)


def test_radar_score_is_0_for_unranked_and_unanswered_category():
    scores = compute_radar_scores(["housing"], ["taxes_shortfall"])
    assert scores["safety"] == pytest.approx(0.0)


def test_radar_score_ranked_category_wins_even_if_unanswered():
    # Ranking itself expresses the priority -- a ranked category scores its
    # graduated value regardless of whether the voter answered its questions.
    scores = compute_radar_scores(["housing"], [])
    assert scores["housing"] == pytest.approx(100.0)


def test_radar_scores_cover_all_seven_categories():
    scores = compute_radar_scores([], [])
    assert set(scores.keys()) == set(CATEGORY_LABELS)
    assert all(v == pytest.approx(0.0) for v in scores.values())
```

Update the test-file import list to add `derive_effective_weights` is already imported; no new import needed for this step (Task 1 already added `order_questions_by_rank`; `compute_radar_scores`/`derive_effective_weights` were already imported previously).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_questionnaire_scoring.py -k "rank_ or radar_score" -v`
Expected: FAIL — `test_rank_2_category_question_gets_weight_four` etc. fail because `derive_effective_weights` still returns the old flat 5/2 scheme; radar tests fail similarly.

- [ ] **Step 3: Implement graduated weights and radar**

In `questionnaire_scoring.py`, replace the existing `derive_effective_weights` function body with:

```python
RANK_WEIGHTS: dict[int, int] = {1: 5, 2: 4, 3: 3, 4: 2}
BASELINE_WEIGHT = 1


def derive_effective_weights(
    ranked_categories: Iterable[str], answered_question_ids: Iterable[str]
) -> dict[str, int]:
    """The single authoritative source of per-question compatibility weight,
    derived from the voter's ranked priority categories (rank 1 = most
    important) rather than a per-question Low/Medium/High control. Rank 1-4
    map to weights 5/4/3/2; any other answered question gets baseline weight
    1 -- never 0, so unranked categories still count toward a candidate's
    match. Unanswered question ids are simply omitted (skipped/unasked
    questions must not affect compatibility). Only the first 4 entries of
    `ranked_categories` are used.
    """
    rank_by_category = {category: i + 1 for i, category in enumerate(list(ranked_categories)[:4])}
    weights: dict[str, int] = {}
    for question_id in answered_question_ids:
        question = QUESTIONS_BY_ID.get(question_id)
        if question is None:
            continue
        rank = rank_by_category.get(question.category)
        weights[question_id] = RANK_WEIGHTS.get(rank, BASELINE_WEIGHT)
    return weights
```

Replace the existing `compute_radar_scores` function body with:

```python
RADAR_SCORE_BY_RANK: dict[int, float] = {1: 100.0, 2: 80.0, 3: 60.0, 4: 40.0}
RADAR_BASELINE_ANSWERED_SCORE = 20.0
RADAR_UNREPRESENTED_SCORE = 0.0


def compute_radar_scores(
    ranked_categories: Iterable[str], answered_question_ids: Iterable[str]
) -> dict[str, float]:
    """category -> voter-priority score (0-100) for the radar chart.

    This represents how much the voter prioritized each category, NOT their
    directional/ideological lean on it (see compute_compass_scores for
    direction). A ranked category (1st-4th) scores its graduated value
    (100/80/60/40) regardless of whether its questions were answered --
    ranking itself expresses the priority. An unranked category scores 20 if
    the voter answered at least one of its questions, or 0 if every question
    in it was skipped.
    """
    rank_by_category = {category: i + 1 for i, category in enumerate(list(ranked_categories)[:4])}
    answered_categories = {
        QUESTIONS_BY_ID[qid].category for qid in answered_question_ids if qid in QUESTIONS_BY_ID
    }
    scores: dict[str, float] = {}
    for category in CATEGORY_LABELS:
        rank = rank_by_category.get(category)
        if rank is not None:
            scores[category] = RADAR_SCORE_BY_RANK[rank]
        elif category in answered_categories:
            scores[category] = RADAR_BASELINE_ANSWERED_SCORE
        else:
            scores[category] = RADAR_UNREPRESENTED_SCORE
    return scores
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_questionnaire_scoring.py -v`
Expected: All tests pass EXCEPT the end-to-end tests in the `# --- End-to-end: derive_effective_weights feeding compute_candidate_compatibility ---` section, which still assert the old flat-weight numbers — fixed in the next step.

- [ ] **Step 5: Update the end-to-end weight/compatibility tests for the new graduated numbers**

Replace the 4 tests in the `# --- End-to-end: derive_effective_weights feeding compute_candidate_compatibility ---` section at the bottom of `test_questionnaire_scoring.py` with:

```python
def test_unasked_questions_do_not_affect_compatibility():
    answers = {"housing_zoning_density": 5}
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(answers, weights, {"housing_zoning_density": 5})
    assert result["overall_pct"] == pytest.approx(100.0)
    assert result["question_count"] == 1


def test_skipped_question_does_not_affect_compatibility():
    answers = {"housing_zoning_density": 5}  # taxes_shortfall was skipped, never included
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(
        answers, weights, {"housing_zoning_density": 5, "taxes_shortfall": 1}
    )
    assert result["question_count"] == 1


def test_unknown_candidate_position_remains_excluded_even_with_derived_weights():
    answers = {"housing_zoning_density": 5, "taxes_shortfall": 2}
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(answers, weights, {"housing_zoning_density": 5})
    assert result["question_count"] == 1
    assert "taxes" not in result["by_category"]


def test_rank_1_weight_dominates_unranked_in_overall_compatibility():
    # housing ranked 1st (weight 5, mismatched), taxes unranked (weight 1, perfect match) --
    # overall should be pulled toward the mismatch since it's weighted more heavily.
    answers = {"housing_zoning_density": 5, "taxes_shortfall": 2}
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(
        answers, weights, {"housing_zoning_density": 1, "taxes_shortfall": 2}
    )
    # housing: compat=0, weight=5 -> 0; taxes: compat=1, weight=1 -> 1
    # overall = 100 * 1 / 6
    assert result["overall_pct"] == pytest.approx(100 / 6)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest test_questionnaire_scoring.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add questionnaire_scoring.py test_questionnaire_scoring.py
git commit -m "Replace flat priority weight/radar scheme with graduated rank-based scheme"
```

---

## Task 3: `questionnaire_scoring.py` — emphasis multiplier and per-candidate weights

**Files:**
- Modify: `questionnaire_scoring.py`
- Modify: `test_questionnaire_scoring.py`

**Interfaces:**
- Consumes: `derive_effective_weights`, `QUESTIONS_BY_ID` (from Tasks 1-2).
- Produces: `emphasis_multiplier(emphasis_score: int | None) -> float`; `derive_candidate_weights(ranked_categories: Iterable[str], answered_question_ids: Iterable[str], candidate_emphasis: dict[str, int]) -> dict[str, float]`. Both are consumed by `backend_api.py` in Task 6 and by `election_lookup.py`'s callers only indirectly (election_lookup never imports scoring weight functions).

- [ ] **Step 1: Write the failing tests**

Add this section to `test_questionnaire_scoring.py`, directly after the rank-weight tests from Task 2 (before the radar section):

```python
# --- Candidate emphasis blending (emphasis_multiplier, derive_candidate_weights) ---


def test_emphasis_multiplier_score_one_is_point_seven():
    assert emphasis_multiplier(1) == pytest.approx(0.7)


def test_emphasis_multiplier_score_three_is_neutral_one():
    assert emphasis_multiplier(3) == pytest.approx(1.0)


def test_emphasis_multiplier_score_five_is_point_thirteen():
    assert emphasis_multiplier(5) == pytest.approx(1.3)


def test_emphasis_multiplier_none_is_neutral_one():
    assert emphasis_multiplier(None) == pytest.approx(1.0)


def test_derive_candidate_weights_scales_rank_weight_by_emphasis():
    # housing ranked 1st -> base weight 5; candidate emphasis on housing = 5 -> 1.3x -> 6.5
    weights = derive_candidate_weights(
        ["housing"], ["housing_zoning_density"], candidate_emphasis={"housing": 5}
    )
    assert weights["housing_zoning_density"] == pytest.approx(6.5)


def test_derive_candidate_weights_low_emphasis_reduces_weight():
    # housing ranked 1st -> base weight 5; candidate emphasis on housing = 1 -> 0.7x -> 3.5
    weights = derive_candidate_weights(
        ["housing"], ["housing_zoning_density"], candidate_emphasis={"housing": 1}
    )
    assert weights["housing_zoning_density"] == pytest.approx(3.5)


def test_derive_candidate_weights_missing_emphasis_is_neutral():
    weights = derive_candidate_weights(
        ["housing"], ["housing_zoning_density"], candidate_emphasis={}
    )
    assert weights["housing_zoning_density"] == pytest.approx(5.0)


def test_derive_candidate_weights_two_candidates_get_different_weights_same_question():
    # This is the core new behavior: the SAME voter question gets a DIFFERENT
    # effective weight depending on which candidate's emphasis is applied.
    high_emphasis = derive_candidate_weights(
        ["housing"], ["housing_zoning_density"], candidate_emphasis={"housing": 5}
    )
    low_emphasis = derive_candidate_weights(
        ["housing"], ["housing_zoning_density"], candidate_emphasis={"housing": 1}
    )
    assert high_emphasis["housing_zoning_density"] != low_emphasis["housing_zoning_density"]


def test_derive_candidate_weights_blend_moves_overall_compatibility():
    # End-to-end: two candidates with IDENTICAL positions but different
    # emphasis on the voter's rank-1 category must produce DIFFERENT overall_pct.
    answers = {"housing_zoning_density": 5}
    identical_positions = {"housing_zoning_density": 3}  # same for both candidates

    weights_high = derive_candidate_weights(["housing"], answers.keys(), {"housing": 5})
    weights_low = derive_candidate_weights(["housing"], answers.keys(), {"housing": 1})

    result_high = compute_candidate_compatibility(answers, weights_high, identical_positions)
    result_low = compute_candidate_compatibility(answers, weights_low, identical_positions)

    # Weight alone doesn't change a single-question overall_pct (it's the only
    # question, so weighted average == its own compatibility regardless of
    # weight) -- so prove the effect with a second, unranked question where
    # the two candidates diverge in compatibility, and show the weighted
    # blend differs between them.
    answers_multi = {"housing_zoning_density": 5, "taxes_shortfall": 2}
    candidate_a_positions = {"housing_zoning_density": 3, "taxes_shortfall": 2}  # matches on taxes
    candidate_b_positions = {"housing_zoning_density": 3, "taxes_shortfall": 5}  # mismatches on taxes

    weights_a = derive_candidate_weights(["housing"], answers_multi.keys(), {"housing": 5})  # high housing emphasis
    weights_b = derive_candidate_weights(["housing"], answers_multi.keys(), {"housing": 1})  # low housing emphasis

    result_a = compute_candidate_compatibility(answers_multi, weights_a, candidate_a_positions)
    result_b = compute_candidate_compatibility(answers_multi, weights_b, candidate_b_positions)

    assert result_a["overall_pct"] != result_b["overall_pct"]
```

Update the import list at the top of `test_questionnaire_scoring.py` to add `derive_candidate_weights` and `emphasis_multiplier`:

```python
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    QUESTIONS_BY_ID,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
    derive_candidate_weights,
    derive_effective_weights,
    emphasis_multiplier,
    order_questions_by_rank,
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_questionnaire_scoring.py -k "emphasis" -v`
Expected: FAIL with `ImportError: cannot import name 'emphasis_multiplier'`

- [ ] **Step 3: Implement `emphasis_multiplier` and `derive_candidate_weights`**

Add to `questionnaire_scoring.py`, directly below `derive_effective_weights`:

```python
def emphasis_multiplier(emphasis_score: int | None) -> float:
    """0.7x-1.3x multiplier derived from a candidate's 1-5 OSINT "how much
    do they talk about this issue" emphasis score for one category (see
    election_lookup.CandidateIssueProfile.emphasis). None means no OSINT
    signal was found for this category (e.g. a purely speculative profile,
    or a category the gathered evidence simply never touched on) -- that is
    treated as neutral (1.0x), never as a penalty, since absence of a
    measured signal isn't the same as confirmed silence on the issue.
    """
    if emphasis_score is None:
        return 1.0
    return 0.7 + 0.15 * (emphasis_score - 1)


def derive_candidate_weights(
    ranked_categories: Iterable[str],
    answered_question_ids: Iterable[str],
    candidate_emphasis: dict[str, int],
) -> dict[str, float]:
    """Per-candidate effective weight: the voter's rank-based weight (see
    derive_effective_weights) scaled by THIS candidate's emphasis on that
    question's category. Two candidates can therefore get different weights
    for the exact same voter question -- intentional: a candidate who talks
    more about a voter's priority issue counts that issue more heavily in
    their own match score, and one who's relatively silent on it counts it
    somewhat less (never zero).
    """
    base_weights = derive_effective_weights(ranked_categories, answered_question_ids)
    return {
        question_id: base_weight * emphasis_multiplier(candidate_emphasis.get(QUESTIONS_BY_ID[question_id].category))
        for question_id, base_weight in base_weights.items()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_questionnaire_scoring.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add questionnaire_scoring.py test_questionnaire_scoring.py
git commit -m "Add OSINT emphasis multiplier and per-candidate weight derivation"
```

---

## Task 4: `election_lookup.py` — `CandidateIssueProfile.emphasis` field + OSINT queries

**Files:**
- Modify: `election_lookup.py`
- Modify: `test_election_lookup.py`

**Interfaces:**
- Produces: `CandidateIssueProfile.emphasis: dict[str, int]` (new field, default `{}`); `_candidate_search_queries(candidate_name, office, jurisdiction_name) -> list[str]` now returns 12 queries instead of 7 (adds 5 OSINT/platform-targeted queries).

- [ ] **Step 1: Write the failing tests**

Add to `test_election_lookup.py`, directly after the existing `test_candidate_issue_profile_covered_axes_none_covered` test:

```python
def test_candidate_issue_profile_emphasis_defaults_to_empty_dict():
    profile = CandidateIssueProfile(candidate_name="Jane Doe", office="mayor", positions={})
    assert profile.emphasis == {}


def test_candidate_issue_profile_accepts_explicit_emphasis():
    profile = CandidateIssueProfile(
        candidate_name="Jane Doe", office="mayor", positions={}, emphasis={"housing": 4}
    )
    assert profile.emphasis == {"housing": 4}
```

Add this near the existing `_candidate_search_queries` test coverage (search the file for where `_candidate_search_queries` behavior is implicitly tested via `research_candidates_via_tavily`'s `len(search_calls[0]) == 7` assertion in `test_research_candidates_via_tavily_adds_priority_pass_for_missing_category` — that assertion is updated in Task 5, not here). Add a new direct unit test for the query builder itself, right after the `test_priority_search_queries_returns_five_variants_using_research_terms` test:

```python
def test_candidate_search_queries_returns_twelve_queries_including_osint_platforms():
    queries = election_lookup._candidate_search_queries("Jane Doe", "mayor", "Springfield")
    assert len(queries) == 12
    joined = " | ".join(queries).lower()
    assert "twitter" in joined
    assert "facebook" in joined
    assert "instagram" in joined
    assert "official campaign website" in joined
    assert all("Jane Doe" in q and "Springfield" in q for q in queries)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_election_lookup.py -k "emphasis or twelve_queries" -v`
Expected: FAIL — `emphasis` is an unexpected keyword argument to `CandidateIssueProfile`; query count is 7, not 12.

- [ ] **Step 3: Add the `emphasis` field and OSINT queries**

In `election_lookup.py`, update the `CandidateIssueProfile` dataclass:

```python
@dataclass
class CandidateIssueProfile:
    candidate_name: str
    office: Literal["mayor", "county", "us_house"]
    positions: dict[str, int]  # question_id -> 1-5; feeds compute_candidate_compatibility directly
    sourced_positions: list[CandidateIssuePosition] = field(default_factory=list)
    emphasis: dict[str, int] = field(default_factory=dict)  # category -> 1-5 OSINT "how much do they talk about this" score
```

Update `_candidate_search_queries`:

```python
def _candidate_search_queries(candidate_name: str, office: str, jurisdiction_name: str) -> "list[str]":
    """12 broad queries covering every category AND general OSINT platforms
    (official site, X/Twitter, Facebook, Instagram, campaign social media),
    not just any one issue -- this is the initial pass that runs
    automatically in the background for every candidate as soon as a race is
    found (not something the user is blocked waiting on), so it can afford
    real thoroughness: more distinct source types means more genuine
    "explicit"/"strong_inference" position evidence AND a fuller picture of
    how much the candidate actually talks about each topic (see
    CandidateIssueProfile.emphasis), without loosening how evidence gets
    classified."""
    office_label = _OFFICE_LABELS.get(office, office)
    return [
        f"{candidate_name} {jurisdiction_name} {office_label} Ballotpedia",
        f"{candidate_name} {jurisdiction_name} {office_label} Vote411 voter guide",
        f"{candidate_name} {jurisdiction_name} {office_label} official statement voting record",
        f"{candidate_name} {jurisdiction_name} {office_label} campaign positions priorities",
        f"{candidate_name} {jurisdiction_name} {office_label} candidate questionnaire survey",
        f"{candidate_name} {jurisdiction_name} {office_label} news interview",
        f"{candidate_name} {jurisdiction_name} {office_label} endorsement forum debate",
        f"{candidate_name} {jurisdiction_name} {office_label} official campaign website platform issues",
        f"{candidate_name} {jurisdiction_name} {office_label} X Twitter",
        f"{candidate_name} {jurisdiction_name} {office_label} Facebook page",
        f"{candidate_name} {jurisdiction_name} {office_label} Instagram",
        f"{candidate_name} {jurisdiction_name} {office_label} campaign social media posts",
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_election_lookup.py -v`
Expected: The 4 new tests PASS. Other tests that assert `len(search_calls[0]) == 7` (in `test_research_candidates_via_tavily_adds_priority_pass_for_missing_category`) now FAIL — expected, fixed in Task 5.

- [ ] **Step 5: Commit**

```bash
git add election_lookup.py test_election_lookup.py
git commit -m "Add CandidateIssueProfile.emphasis field and OSINT platform queries"
```

---

## Task 5: `election_lookup.py` — parse and wire emphasis through the research pipeline

**Files:**
- Modify: `election_lookup.py`
- Modify: `test_election_lookup.py`

**Interfaces:**
- Consumes: `CandidateIssueProfile.emphasis` (Task 4).
- Produces: `parse_candidates_evidence_response` now also populates `profile.emphasis` from the response JSON's new `"emphasis"` array per candidate; `research_candidates_via_tavily` sets `emphasis` from the broad pass only (never overwritten by the gap-fill pass); `research_candidates_for_race_with_fallback` carries `emphasis` through to its final merged profile.

- [ ] **Step 1: Write the failing tests**

Add to `test_election_lookup.py`, directly after `CANDIDATES_EVIDENCE_JSON` and its `test_parses_candidates_evidence_response` test:

```python
CANDIDATES_EVIDENCE_WITH_EMPHASIS_JSON = """
{
  "candidates": [
    {
      "name": "Jane Doe",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 4,
         "confidence": "explicit", "source_url": "https://example.com/jane-vote411"}
      ],
      "emphasis": [
        {"category": "housing", "score": 5},
        {"category": "taxes", "score": 2}
      ]
    }
  ]
}
"""


def test_parses_candidates_evidence_response_with_emphasis():
    profiles = parse_candidates_evidence_response("mayor", ["Jane Doe"], CANDIDATES_EVIDENCE_WITH_EMPHASIS_JSON)
    assert profiles["Jane Doe"].emphasis == {"housing": 5, "taxes": 2}


def test_parses_candidates_evidence_response_missing_emphasis_key_defaults_empty():
    profiles = parse_candidates_evidence_response("mayor", ["Jane Doe"], CANDIDATES_EVIDENCE_JSON)
    assert profiles["Jane Doe"].emphasis == {}


def test_candidates_evidence_response_skips_invalid_emphasis_entries():
    raw = (
        '{"candidates": [{"name": "Jane Doe", "positions": [], "emphasis": ['
        '{"category": "not_a_real_category", "score": 3}, '
        '{"category": "housing", "score": 9}, '
        '{"category": "housing", "score": "high"}, '
        '{"category": "taxes", "score": 4}'
        ']}]}'
    )
    profiles = parse_candidates_evidence_response("mayor", ["Jane Doe"], raw)
    assert profiles["Jane Doe"].emphasis == {"taxes": 4}
```

Now update the one existing test that asserts an exact broad-query count, since the broad pass grew from 7 to 12 queries (Task 4). Find and replace in `test_research_candidates_via_tavily_adds_priority_pass_for_missing_category`:

```python
    assert len(search_calls[0]) == 7
```
→
```python
    assert len(search_calls[0]) == 12
```

Add a new integration test proving emphasis flows through the broad pass and survives the gap-fill merge unchanged, directly after `test_research_candidates_via_tavily_skips_priority_pass_when_fully_covered`:

```python
def test_research_candidates_via_tavily_keeps_broad_pass_emphasis_through_gap_fill():
    fake_client = MagicMock()
    broad_with_emphasis = """
    {"candidates": [{"name": "Jane Doe", "positions": [
      {"question_id": "housing_zoning_density", "position": 4, "confidence": "explicit",
       "source_url": "https://example.com/jane-housing"}
    ], "emphasis": [{"category": "housing", "score": 4}]}]}
    """
    gap_fill_response = """
    {"candidates": [{"name": "Jane Doe", "positions": [
      {"question_id": "safety_police_funding", "position": 2, "confidence": "explicit",
       "source_url": "https://example.com/jane-safety"}
    ], "emphasis": [{"category": "safety", "score": 1}]}]}
    """
    fake_client.messages.create.side_effect = [
        _mock_response(broad_with_emphasis),
        _mock_response(gap_fill_response),
    ]
    candidates = [Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])]

    with patch(
        "election_lookup.tavily_search.search_many", side_effect=_fake_search_many_echo
    ):
        profiles = research_candidates_via_tavily(
            "62704",
            "mayor",
            "Springfield",
            candidates,
            client=fake_client,
            selected_categories=["housing", "safety"],
        )

    # Emphasis always comes from the broad pass, even though the gap-fill
    # pass also returned an (ignored) emphasis entry for "safety".
    assert profiles["Jane Doe"].emphasis == {"housing": 4}
```

Add a fallback-carries-emphasis test after `test_fallback_skips_speculation_for_a_fully_sourced_candidate`:

```python
def test_fallback_carries_emphasis_through_to_final_merged_profile():
    fake_client = MagicMock()
    evidence_with_emphasis = """
    {"candidates": [{"name": "Jane Doe", "positions": [
      {"question_id": "housing_zoning_density", "position": 4, "confidence": "explicit",
       "source_url": "https://example.com/jane"}
    ], "emphasis": [{"category": "housing", "score": 5}]}]}
    """

    def fake_create(*args, **kwargs):
        content = kwargs["messages"][0]["content"]
        if "analyzing pre-gathered web search" in content:
            return _mock_response(evidence_with_emphasis)
        # speculative fallback fills the remaining questions
        remaining_json = ",".join(
            f'{{"question_id": "{q.id}", "position": 3}}'
            for q in QUESTIONS
            if q.id != "housing_zoning_density"
        )
        return _mock_response(f'{{"candidates": [{{"name": "Jane Doe", "positions": [{remaining_json}]}}]}}')

    fake_client.messages.create.side_effect = fake_create
    candidates = [Candidate(name="Jane Doe", party="Independent", incumbent=True, positions=[])]

    with patch("election_lookup.tavily_search.search_many", side_effect=_empty_evidence_search_many):
        profiles = research_candidates_for_race_with_fallback(
            "62704", "mayor", "Springfield", candidates, client=fake_client
        )

    assert profiles["Jane Doe"].emphasis == {"housing": 5}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_election_lookup.py -v`
Expected: FAIL — `emphasis` key not parsed yet (stays `{}` for all new tests); the `12` query-count assertion still fails until Task 4's change is confirmed present (it should already pass from Task 4 — if not, re-check Task 4 landed).

- [ ] **Step 3: Implement emphasis parsing and wiring**

In `election_lookup.py`, add a category-list constant and parser near `_parse_evidence_positions`:

```python
def _parse_emphasis(emphasis_data: "list") -> "dict[str, int]":
    emphasis: dict[str, int] = {}
    for entry in emphasis_data:
        if not isinstance(entry, dict):
            continue
        category = entry.get("category")
        if not isinstance(category, str) or category not in CATEGORY_LABELS:
            continue
        score = entry.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not (1 <= score <= 5):
            continue
        emphasis[category] = score
    return emphasis
```

Update `parse_candidates_evidence_response` (replace the loop body where `profiles[name] = CandidateIssueProfile(...)` is built):

```python
def parse_candidates_evidence_response(
    office: str, candidate_names: "list[str]", raw_text: str
) -> "dict[str, CandidateIssueProfile]":
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "candidates" not in data or not isinstance(data["candidates"], list):
        raise ValueError("Model response JSON is missing a 'candidates' array")

    valid_names = set(candidate_names)
    profiles: dict[str, CandidateIssueProfile] = {}
    for cand_data in data["candidates"]:
        if not isinstance(cand_data, dict):
            continue
        name = cand_data.get("name")
        if not isinstance(name, str) or name not in valid_names or name in profiles:
            continue
        positions_data = cand_data.get("positions")
        if not isinstance(positions_data, list):
            continue
        positions_by_id, sourced_positions = _parse_evidence_positions(positions_data)
        emphasis_data = cand_data.get("emphasis")
        emphasis = _parse_emphasis(emphasis_data) if isinstance(emphasis_data, list) else {}
        profiles[name] = CandidateIssueProfile(
            candidate_name=name,
            office=office,
            positions=positions_by_id,
            sourced_positions=sourced_positions,
            emphasis=emphasis,
        )

    return profiles
```

Update the prompt template so the model actually returns emphasis. Replace `CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE` in full with:

```python
CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE = """You are analyzing pre-gathered web search \
evidence to determine {candidate_count} candidates' likely positions on a set of local-policy \
questions, for a nonpartisan voter-education tool. Use ONLY the evidence provided below for each \
candidate -- do not use outside knowledge, and do not search further.

For each candidate and each question, classify your answer's confidence as exactly one of:
- "explicit": the evidence contains a direct, specific statement from or about the candidate on \
this exact question.
- "strong_inference": the evidence strongly implies a position (e.g. a closely related vote, \
statement, or documented record) even without an exact direct quote on this precise question.
- "weak_inference": ANY plausible, evidence-grounded connection between something the candidate \
has actually said or done and this question's general subject -- a related campaign priority, a \
broader platform statement that touches this topic, a single loosely-related remark, or a general \
policy stance that the question's topic falls under. Be generous here: err toward answering rather \
than skipping when there's some real, candidate-specific evidence to reason from, even if it \
doesn't address this exact question precisely.

The one line that stays firm: do NOT answer a question if the ONLY basis would be the candidate's \
party affiliation alone with no candidate-specific evidence at all, an endorsement alone, \
demographic assumptions alone, or the simple absence of information -- these can support an \
answer when combined with SOME real evidence about the candidate, but never substitute for it \
entirely. If there is truly no candidate-specific evidence at all connecting them to a question's \
subject, leave that question out for that candidate.

In addition to positions, for each candidate rate how much they EMPHASIZE each of the 7 policy \
categories below across all the evidence (their own website, social media, campaign materials, \
news coverage, and any other source) -- this is about how much they talk about the general \
subject, not whether they take a clear position on any one question within it. Score each \
category the evidence supports a judgment on from 1 to 5: 1 = never or almost never mentioned, \
3 = mentioned occasionally alongside other topics, 5 = a clear, recurring campaign priority they \
discuss often. Only include a category if the evidence actually reflects something about that \
candidate discussing it, even loosely -- omit a category entirely for a candidate rather than \
guessing if the evidence says nothing connecting them to it at all.

Categories: {category_ids}

Race: {office_description} ({jurisdiction_name}, zip code {zipcode})

Evidence found for each candidate:

{evidence_block}

For each of the following {question_count} questions, a candidate's position is on a 1-5 scale, \
where 1 means they fully favor the first approach, 5 means they fully favor the second approach, \
and 3 means a genuinely mixed/moderate position supported by the evidence.

{questions_block}

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in exactly \
this shape, with one entry per candidate listed above (using their name exactly as given), \
including a question only when the evidence meets at least "weak_inference", citing the specific \
URL from the evidence above that supports each answer, and including an emphasis entry only for a \
category the evidence supports a judgment on:

{{
  "candidates": [
    {{
      "name": "<one of the candidate names above, exactly as given>",
      "positions": [
        {{
          "question_id": "<one of the question ids above>",
          "position": 1 | 2 | 3 | 4 | 5,
          "confidence": "explicit" | "strong_inference" | "weak_inference",
          "source_url": "<one of the URLs from the evidence above>"
        }}
      ],
      "emphasis": [
        {{"category": "<one of the category ids above>", "score": 1 | 2 | 3 | 4 | 5}}
      ]
    }}
  ]
}}
"""
```

Update the two `.format(...)` call sites for this template inside `research_candidates_via_tavily` (both the broad-pass `prompt = CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE.format(...)` and the gap-fill `gap_prompt = CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE.format(...)`) to add the new `category_ids` argument:

```python
        category_ids=", ".join(CATEGORY_LABELS),
```

(add this as a new keyword argument alongside the existing `candidate_count=`, `office_description=`, etc. in both `.format(...)` calls).

Now make emphasis always come from the broad pass, never the gap-fill pass. In `research_candidates_via_tavily`, update the merge loop at the bottom (the `for name, gap_profile in gap_profiles.items():` block):

```python
    for name, gap_profile in gap_profiles.items():
        base = profiles.get(name)
        if base is None:
            profiles[name] = gap_profile
            continue
        merged_positions = dict(base.positions)
        merged_sourced = list(base.sourced_positions)
        for position in gap_profile.sourced_positions:
            if position.question_id in merged_positions:
                continue  # broad pass already sourced this question -- keep it
            merged_positions[position.question_id] = position.position
            merged_sourced.append(position)
        profiles[name] = CandidateIssueProfile(
            candidate_name=name,
            office=office,
            positions=merged_positions,
            sourced_positions=merged_sourced,
            emphasis=base.emphasis,  # emphasis always comes from the broad pass, never the narrower gap pass
        )
```

Finally, in `research_candidates_for_race_with_fallback`, update the final merge (the `merged[candidate.name] = CandidateIssueProfile(...)` at the end of the function) to carry `emphasis` through:

```python
        merged[candidate.name] = CandidateIssueProfile(
            candidate_name=candidate.name,
            office=office,
            positions=positions,
            sourced_positions=sourced_positions,
            emphasis=sourced.emphasis if sourced else {},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_election_lookup.py test_questionnaire_scoring.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add election_lookup.py test_election_lookup.py
git commit -m "Parse and wire candidate emphasis through the research pipeline"
```

---

## Task 6: `backend_api.py` — ranked_categories rename, emphasis passthrough, per-candidate weights

**Files:**
- Modify: `backend_api.py`

**Interfaces:**
- Consumes: `derive_candidate_weights`, `compute_radar_scores` (Tasks 1-3); `CandidateIssueProfile.emphasis` (Task 4).
- Produces: `/api/results` request body field `ranked_categories` (renamed from `selected_categories`); `/api/candidates/research` request body field `ranked_categories` (renamed from `selected_categories`); `/api/questions` response drops `is_core`; `/api/candidates/research` response `profiles[name]` gains `emphasis`.

There is no new pure-Python logic here (it's all pydantic schema + wiring already-tested functions together), so this task is verified by updating and running the existing pytest suite plus a manual smoke check rather than new unit tests — `backend_api.py` currently has no dedicated test file (confirmed: only `test_election_lookup.py`, `test_questionnaire_scoring.py`, `test_tavily_search.py` exist).

- [ ] **Step 1: Update `_question_to_dict`**

In `backend_api.py`, remove the `is_core` line from `_question_to_dict`:

```python
def _question_to_dict(question) -> dict:
    return {
        "id": question.id,
        "category": question.category,
        "category_label": CATEGORY_LABELS[question.category],
        "econ_weight": question.econ_weight,
        "social_weight": question.social_weight,
        "text": question.text,
        "approach_1": question.approach_1,
        "approach_2": question.approach_2,
        "selection_priority": question.selection_priority,
        "research_terms": list(question.research_terms),
    }
```

- [ ] **Step 2: Add `emphasis` to `_profile_to_dict`**

```python
def _profile_to_dict(profile: "election_lookup.CandidateIssueProfile") -> dict:
    econ, social = compute_compass_scores(profile.positions)
    has_econ, has_social = profile.covered_axes()
    sourced_count = sum(1 for p in profile.sourced_positions if p.confidence != "speculative")
    return {
        "candidate_name": profile.candidate_name,
        "office": profile.office,
        "positions": profile.positions,
        "sourced_positions": [_issue_position_to_dict(p) for p in profile.sourced_positions],
        "coverage": {
            "total_questions": len(QUESTIONS),
            "answered": len(profile.positions),
            "sourced": sourced_count,
            "speculative": len(profile.sourced_positions) - sourced_count,
        },
        "categories_covered": sorted(profile.covered_categories()),
        "compass": {"econ": econ, "social": social, "has_econ": has_econ, "has_social": has_social},
        "emphasis": profile.emphasis,
    }
```

- [ ] **Step 3: Rename `CandidateResearchRequest.selected_categories` to `ranked_categories`**

```python
class CandidateResearchRequest(BaseModel):
    zipcode: str
    office: str
    jurisdiction_name: str
    candidates: list[CandidateInput]
    # Voter's ranked priority categories, if chosen already -- optional so
    # existing callers (e.g. the background research kicked off right after
    # an election search, before the voter has answered anything) keep
    # working unchanged. See election_lookup.research_candidates_for_race_with_fallback.
    ranked_categories: list[str] | None = None
```

Update the call site inside `research_candidates`:

```python
    try:
        profiles = election_lookup.research_candidates_for_race_with_fallback(
            body.zipcode,
            body.office,
            body.jurisdiction_name,
            candidates,
            selected_categories=body.ranked_categories,
        )
```

(The keyword stays `selected_categories=` because that's `election_lookup.research_candidates_for_race_with_fallback`'s own internal parameter name from Task 5 — only the public request-body field name changes.)

- [ ] **Step 4: Rename `ResultsRequest.selected_categories` to `ranked_categories`, add `emphasis` to `CandidateResultInput`, compute per-candidate weights**

```python
class CandidateResultInput(BaseModel):
    name: str
    office: str
    positions: dict[str, int]
    emphasis: dict[str, int] = {}


class ResultsRequest(BaseModel):
    answers: dict[str, int]
    # The voter's ranked (1st-4th) priority category ids from Stage 1 of the
    # questionnaire, index 0 = rank 1. Effective per-candidate compatibility
    # weight is derived from this plus each candidate's own emphasis
    # server-side (see derive_candidate_weights) -- the frontend never sends
    # a weight or importance number directly.
    ranked_categories: list[str] = []
    candidates: list[CandidateResultInput] = []


@app.post("/api/results")
def get_results(body: ResultsRequest) -> dict:
    answer_storage.save_submission(body.answers, body.ranked_categories)

    radar = compute_radar_scores(body.ranked_categories, body.answers.keys())
    voter_econ, voter_social = compute_compass_scores(body.answers)

    candidate_results = []
    for candidate in body.candidates:
        weights = derive_candidate_weights(body.ranked_categories, body.answers.keys(), candidate.emphasis)
        compatibility = compute_candidate_compatibility(body.answers, weights, candidate.positions)
        has_any_position = bool(candidate.positions)
        econ = social = None
        if has_any_position:
            econ, social = compute_compass_scores(candidate.positions)
        candidate_results.append(
            {
                "name": candidate.name,
                "office": candidate.office,
                "compass": {"econ": econ, "social": social} if has_any_position else None,
                "compatibility": compatibility,
            }
        )

    # Rank by overall_pct descending; candidates with no qualifying questions
    # (overall_pct is None) sort last rather than being excluded outright.
    candidate_results.sort(
        key=lambda r: (r["compatibility"]["overall_pct"] is None, -(r["compatibility"]["overall_pct"] or 0))
    )

    return {
        "radar": radar,
        "voter_compass": {"econ": voter_econ, "social": voter_social},
        "candidates": candidate_results,
    }
```

- [ ] **Step 5: Update the import line**

```python
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
    derive_candidate_weights,
)
```

(`derive_effective_weights` is no longer imported directly here — `get_results` now calls `derive_candidate_weights`, which internally uses `derive_effective_weights`.)

- [ ] **Step 6: Run the full backend test suite and a manual smoke check**

Run: `pytest -v`
Expected: All tests PASS (no test file imports from `backend_api.py` directly today, so this mainly re-confirms `questionnaire_scoring.py`/`election_lookup.py` are still green after the rename).

Then manually smoke-test the endpoint:

```bash
python3 -c "import backend_api"  # confirms no syntax/import errors
uvicorn backend_api:app --port 8000 &
sleep 2
curl -s -X POST localhost:8000/api/results -H "Content-Type: application/json" -d '{
  "answers": {"housing_zoning_density": 5, "taxes_shortfall": 2},
  "ranked_categories": ["housing"],
  "candidates": [
    {"name": "Candidate A", "office": "mayor", "positions": {"housing_zoning_density": 3, "taxes_shortfall": 2}, "emphasis": {"housing": 5}},
    {"name": "Candidate B", "office": "mayor", "positions": {"housing_zoning_density": 3, "taxes_shortfall": 2}, "emphasis": {"housing": 1}}
  ]
}'
kill %1
```

Expected: HTTP 200, and `candidate.compatibility.overall_pct` differs between "Candidate A" and "Candidate B" despite identical `positions` (proves the emphasis blend is live end-to-end through the HTTP layer, not just in unit tests).

- [ ] **Step 7: Commit**

```bash
git add backend_api.py
git commit -m "Rename selected_categories to ranked_categories and wire per-candidate emphasis weighting into /api/results"
```

---

## Task 7: Frontend — `lib/questionOrder.ts` replacing `lib/activeQuestions.ts`

**Files:**
- Delete: `frontend/src/lib/activeQuestions.ts`
- Create: `frontend/src/lib/questionOrder.ts`

**Interfaces:**
- Produces: `orderQuestionsByRank(questions: ApiQuestion[], rankedCategories: string[]): ApiQuestion[]`; `MIN_RANKED_CATEGORIES = 1`; `MAX_RANKED_CATEGORIES = 4`; `RECOMMENDED_RANKED_CATEGORIES = 3`. Consumed by Task 9 (`appData.tsx`) and Task 10 (`QuestionnairePage.tsx`).

There's no frontend test runner in this repo (confirmed in the prior redesign pass — `frontend/package.json` has no `test` script and no vitest/jest devDependency), so this task is verified via `npx tsc --noEmit` plus a small inline manual check rather than a unit test file.

- [ ] **Step 1: Delete the old file and create the new one**

```bash
rm frontend/src/lib/activeQuestions.ts
```

Create `frontend/src/lib/questionOrder.ts`:

```typescript
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
```

- [ ] **Step 2: Verify with a throwaway inline check**

Run this from the `frontend/` directory (requires the backend running on port 8000 per the existing dev workflow, or just verify the TypeScript compiles — the logic is a direct mirror of the already-tested Python version from Task 1, so a compile-clean check is sufficient here):

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (the file isn't imported by anything yet at this point in the plan, so this just checks the new file's own syntax/types are valid in isolation — `grep -n "activeQuestions" frontend/src -r` should return nothing except stale references in files not yet updated, which Tasks 8-10 fix).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/questionOrder.ts
git rm frontend/src/lib/activeQuestions.ts
git commit -m "Replace lib/activeQuestions.ts with lib/questionOrder.ts (order, not subset)"
```

---

## Task 8: Frontend — `api.ts` type and field updates

**Files:**
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces: `ApiQuestion` (drops `is_core`); `CandidateProfile` (gains `emphasis: Record<string, number>`); `researchCandidates(body)` (renames `selected_categories?` to `ranked_categories?`); `getResults(body)` (renames `selected_categories` to `ranked_categories`, candidates gain `emphasis`).

- [ ] **Step 1: Update `ApiQuestion`**

```typescript
export interface ApiQuestion {
  id: string
  category: string
  category_label: string
  econ_weight: number
  social_weight: number
  text: string
  approach_1: string
  approach_2: string
  selection_priority: number
  research_terms: string[]
}
```

(`is_core: boolean` line removed.)

- [ ] **Step 2: Update `CandidateProfile`**

```typescript
export interface CandidateProfile {
  candidate_name: string
  office: Office
  positions: Record<string, number>
  sourced_positions: IssuePosition[]
  coverage: { total_questions: number; answered: number; sourced: number; speculative: number }
  categories_covered: string[]
  compass: { econ: number; social: number; has_econ: boolean; has_social: boolean }
  emphasis: Record<string, number>
}
```

- [ ] **Step 3: Update `researchCandidates` and `getResults`**

```typescript
export function researchCandidates(body: {
  zipcode: string
  office: Office
  jurisdiction_name: string
  candidates: { name: string; party: string | null; incumbent: boolean | null }[]
  ranked_categories?: string[]
}): Promise<ResearchResponse> {
  return request('/api/candidates/research', { method: 'POST', body: JSON.stringify(body) })
}

export function getResults(body: {
  answers: Record<string, number>
  ranked_categories: string[]
  candidates: { name: string; office: Office; positions: Record<string, number>; emphasis: Record<string, number> }[]
}): Promise<ResultsResponse> {
  return request('/api/results', { method: 'POST', body: JSON.stringify(body) })
}
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc --noEmit`
Expected: Errors will appear in `appData.tsx`, `QuestionnairePage.tsx` (files not yet updated) referencing `is_core`, `selected_categories`, `buildActiveQuestions`, `MAX_SELECTED_CATEGORIES` — this is expected at this point in the plan; confirm the errors are ONLY in those two files and nowhere else, then proceed (fixed in Tasks 9-10).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api.ts
git commit -m "Rename API request fields to ranked_categories and add emphasis to candidate types"
```

---

## Task 9: Frontend — `context/appData.tsx` rank-aware state

**Files:**
- Modify: `frontend/src/context/appData.tsx`

**Interfaces:**
- Consumes: `orderQuestionsByRank`, `MAX_RANKED_CATEGORIES` (Task 7); renamed `api.researchCandidates`/`api.getResults` fields (Task 8).
- Produces: `AppDataContextType.orderedQuestions: ApiQuestion[]` (renamed from `activeQuestions`); `selectedIssueCategories: string[]` (unchanged name, now semantically an ordered rank list — index 0 = rank 1); `toggleIssueCategory` (unchanged behavior — array append/remove already IS rank-correct); `computeResults` now sends `ranked_categories` and per-candidate `emphasis`, and no longer filters answers by an active-question set (every answered question is always valid now).

- [ ] **Step 1: Update the import line**

Replace:
```typescript
import { buildActiveQuestions, MAX_SELECTED_CATEGORIES } from '../lib/activeQuestions'
```
with:
```typescript
import { orderQuestionsByRank, MAX_RANKED_CATEGORIES } from '../lib/questionOrder'
```

- [ ] **Step 2: Rename `activeQuestions` to `orderedQuestions` in the context type and provider**

In the `AppDataContextType` interface, replace:
```typescript
  selectedIssueCategories: string[]
  toggleIssueCategory: (categoryId: string) => void
  activeQuestions: ApiQuestion[]
```
with:
```typescript
  selectedIssueCategories: string[]
  toggleIssueCategory: (categoryId: string) => void
  orderedQuestions: ApiQuestion[]
```

In `AppDataProvider`, replace:
```typescript
  const activeQuestions = useMemo(
    () => buildActiveQuestions(questions, selectedIssueCategories),
    [questions, selectedIssueCategories],
  )
```
with:
```typescript
  const orderedQuestions = useMemo(
    () => orderQuestionsByRank(questions, selectedIssueCategories),
    [questions, selectedIssueCategories],
  )
```

- [ ] **Step 3: Update `toggleIssueCategory`'s cap constant**

Replace:
```typescript
  const toggleIssueCategory = useCallback((categoryId: string) => {
    setSelectedIssueCategories((prev) => {
      if (prev.includes(categoryId)) return prev.filter((c) => c !== categoryId)
      if (prev.length >= MAX_SELECTED_CATEGORIES) return prev
      return [...prev, categoryId]
    })
  }, [])
```
with:
```typescript
  const toggleIssueCategory = useCallback((categoryId: string) => {
    setSelectedIssueCategories((prev) => {
      // Array order IS rank order (index 0 = rank 1) -- removing an item
      // naturally shifts every later category up a rank with no separate
      // renumbering step needed.
      if (prev.includes(categoryId)) return prev.filter((c) => c !== categoryId)
      if (prev.length >= MAX_RANKED_CATEGORIES) return prev
      return [...prev, categoryId]
    })
  }, [])
```

- [ ] **Step 4: Update `researchRace`'s request body key**

Replace:
```typescript
        ...(selectedCategories && selectedCategories.length > 0 ? { selected_categories: selectedCategories } : {}),
```
with:
```typescript
        ...(selectedCategories && selectedCategories.length > 0 ? { ranked_categories: selectedCategories } : {}),
```

- [ ] **Step 5: Simplify `computeResults` (no more active-question filtering) and send `ranked_categories` + `emphasis`**

Replace the entire `computeResults` function body:

```typescript
  const computeResults = useCallback(async () => {
    setResultsStatus('loading')
    setResultsError(null)
    try {
      await ensureAllRacesResearched()
      await ensurePriorityResearch()

      const answerEntries = Object.entries(quizAnswers).filter(
        (entry): entry is [string, number] => entry[1] !== null && entry[1] !== undefined,
      )

      const candidatesForScoring = elections.races.flatMap((race) =>
        race.candidates.map((c) => {
          const profile = profiles[candidateKey(race.office, c.name)]
          return {
            name: c.name,
            office: race.office,
            positions: profile?.positions ?? {},
            emphasis: profile?.emphasis ?? {},
          }
        }),
      )

      const response = await api.getResults({
        answers: Object.fromEntries(answerEntries),
        ranked_categories: selectedIssueCategories,
        candidates: candidatesForScoring,
      })
      setResults(response)
      setResultsStatus('loaded')
    } catch (err) {
      setResultsStatus('error')
      setResultsError(err instanceof api.ApiError ? err.message : 'Could not compute your results.')
    }
  }, [
    ensureAllRacesResearched,
    ensurePriorityResearch,
    elections.races,
    profiles,
    quizAnswers,
    selectedIssueCategories,
  ])
```

(Note: `orderedQuestions` is intentionally NOT in this dependency array or used inside — every answered question is always part of the always-full 20-question set now, so the previous "filter to only active question ids" step is removed entirely, not just renamed.)

- [ ] **Step 6: Update the `value` object and its dependency array**

In the final `useMemo` that builds the context `value`, replace both occurrences of `activeQuestions,` (once in the returned object, once in the dependency array) with `orderedQuestions,`.

- [ ] **Step 7: Verify**

Run: `cd frontend && npx tsc --noEmit`
Expected: Errors remaining only in `QuestionnairePage.tsx` (referencing `activeQuestions`, `MAX_SELECTED_CATEGORIES` from the old import path, `q.is_core`) — fixed in Task 10.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/context/appData.tsx
git commit -m "Rename activeQuestions to orderedQuestions and send ranked_categories + emphasis to /api/results"
```

---

## Task 10: Frontend — `QuestionnairePage.tsx` rank badges and all-20 flow

**Files:**
- Modify: `frontend/src/pages/QuestionnairePage.tsx`

**Interfaces:**
- Consumes: `orderedQuestions`, `selectedIssueCategories`, `toggleIssueCategory` (Task 9); `MIN_RANKED_CATEGORIES`, `MAX_RANKED_CATEGORIES`, `RECOMMENDED_RANKED_CATEGORIES` (Task 7).

- [ ] **Step 1: Update imports**

Replace:
```typescript
import type { ApiQuestion } from '../api'
import { MAX_SELECTED_CATEGORIES, MIN_SELECTED_CATEGORIES, RECOMMENDED_SELECTED_CATEGORIES } from '../lib/activeQuestions'
```
with:
```typescript
import type { ApiQuestion } from '../api'
import { MAX_RANKED_CATEGORIES, MIN_RANKED_CATEGORIES, RECOMMENDED_RANKED_CATEGORIES } from '../lib/questionOrder'
```

- [ ] **Step 2: Replace `CategoryCard` to show a rank badge instead of a checkmark**

Replace the entire `CategoryCard` function:

```typescript
function CategoryCard({ option, rank, disabled, onToggle }: {
  option: CategoryOption
  rank: number | null
  disabled: boolean
  onToggle: () => void
}) {
  const selected = rank !== null
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      disabled={disabled}
      className={`text-left px-4 py-3.5 rounded-xl border-2 transition-all duration-150 flex items-start gap-3
        ${selected ? 'border-civic bg-civic-pale shadow-sm' : 'border-border bg-surface hover:border-civic/40 hover:bg-civic-pale/30'}
        ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors text-[11px] font-bold
        ${selected ? 'bg-civic border-civic text-white' : 'border-border-strong text-transparent'}`}>
        {selected ? rank : ''}
      </span>
      <span className="text-sm font-medium text-navy leading-snug">{option.label}</span>
    </button>
  )
}
```

- [ ] **Step 3: Update `CategoryStage` to compute rank from array order and update copy**

Replace the entire `CategoryStage` function:

```typescript
function CategoryStage({ options, ranked, onToggle, onContinue }: {
  options: CategoryOption[]
  ranked: string[]
  onToggle: (id: string) => void
  onContinue: () => void
}) {
  const { navigate } = useNav()
  const count = ranked.length
  const canContinue = count >= MIN_RANKED_CATEGORIES
  const rankOf = (id: string): number | null => {
    const index = ranked.indexOf(id)
    return index === -1 ? null : index + 1
  }

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-surface border-b border-border sticky top-[60px] z-40">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted">
              <button onClick={() => navigate('home')} className="hover:text-civic">Home</button>
              <span>/</span>
              <span className="text-navy font-medium">Rank your priorities</span>
            </div>
            <span className="text-xs text-muted font-mono">{count} of {MAX_RANKED_CATEGORIES} ranked</span>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <div className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
          <div className="px-6 sm:px-8 pt-7 pb-4">
            <p className="text-xl sm:text-2xl font-semibold text-navy leading-snug" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Which issues matter most to you?
            </p>
            <p className="mt-2 text-sm text-muted leading-relaxed">
              Tap issues in the order you care about them — first tap is your top priority. Rank {MIN_RANKED_CATEGORIES}-{MAX_RANKED_CATEGORIES}, we recommend {RECOMMENDED_RANKED_CATEGORIES}. Every issue still counts toward your results; ranked ones just count more.
            </p>
          </div>

          <div className="px-6 sm:px-8 pb-7 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {options.map((option) => {
              const rank = rankOf(option.id)
              const disabled = rank === null && count >= MAX_RANKED_CATEGORIES
              return (
                <CategoryCard
                  key={option.id}
                  option={option}
                  rank={rank}
                  disabled={disabled}
                  onToggle={() => onToggle(option.id)}
                />
              )
            })}
          </div>

          <div className="px-6 sm:px-8 py-5 border-t border-border">
            <button
              onClick={onContinue}
              disabled={!canContinue}
              className="w-full py-3 rounded-xl bg-civic text-white font-semibold hover:bg-civic-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Update the main component to use `orderedQuestions` and drop the `is_core` badge**

In `QuestionnairePage`, replace the destructured `useAppData()` call:

```typescript
  const {
    questions, questionsStatus, ensureQuestionsLoaded,
    selectedIssueCategories, toggleIssueCategory, orderedQuestions,
    quizAnswers, setQuizAnswer, resetQuiz,
    computeResults, resultsStatus, resultsError,
  } = useAppData()
```

Replace the `useEffect` that clamps `step`:
```typescript
  useEffect(() => {
    setStep((prev) => (orderedQuestions.length === 0 ? 0 : Math.min(prev, orderedQuestions.length - 1)))
  }, [orderedQuestions.length])
```

Replace both `<CategoryStage ... />` render call sites (the `stage === 'categories'` branch and the `if (!q)` fallback branch) to pass `ranked={selectedIssueCategories}` instead of `selected={selectedIssueCategories}`:

```typescript
  if (stage === 'categories') {
    return (
      <CategoryStage
        options={categoryOptions}
        ranked={selectedIssueCategories}
        onToggle={toggleIssueCategory}
        onContinue={() => { setStep(0); setStage('questions') }}
      />
    )
  }

  const total = orderedQuestions.length
  const q: ApiQuestion | undefined = orderedQuestions[step]
  const answeredCount = orderedQuestions.filter((question) => quizAnswers[question.id] !== undefined).length

  if (!q) {
    // Shouldn't happen (all 20 questions are always active once loaded), but
    // fall back to the priority picker rather than rendering a blank page.
    return (
      <CategoryStage
        options={categoryOptions}
        ranked={selectedIssueCategories}
        onToggle={toggleIssueCategory}
        onContinue={() => { setStep(0); setStage('questions') }}
      />
    )
  }
```

Replace the `q.is_core` badge block:

```typescript
            <div className="flex items-center gap-2">
              <CategoryBadge id={q.category} label={q.category_label} />
              {questionRank !== null && (
                <span className="text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full border border-civic/30 text-civic uppercase tracking-widest">
                  Priority #{questionRank}
                </span>
              )}
            </div>
```

Add the `questionRank` computation right above where `answerValue`/`isAnswered` are computed (after the `if (!q) { ... }` block, before `const answerValue = quizAnswers[q.id]`):

```typescript
  const rankIndex = selectedIssueCategories.indexOf(q.category)
  const questionRank = rankIndex === -1 ? null : rankIndex + 1
```

Replace every remaining reference to `activeQuestions` in the rest of the component (the jump-dots `.map`, e.g. `{activeQuestions.map((question, i) => {`) with `orderedQuestions`.

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Both clean, zero errors, zero references to `is_core`/`activeQuestions`/`MAX_SELECTED_CATEGORIES`/`lib/activeQuestions` anywhere in `frontend/src` — confirm with:

```bash
grep -rn "is_core\|activeQuestions\|MAX_SELECTED_CATEGORIES\|lib/activeQuestions" frontend/src
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/QuestionnairePage.tsx
git commit -m "Add rank badges to priority picker and switch questionnaire flow to all 20 questions"
```

---

## Task 11: Full-suite verification and manual browser smoke test

**Files:** none (verification only).

- [ ] **Step 1: Run the full backend test suite**

Run: `pytest -v`
Expected: All tests pass (should be ~140+ tests given ~30 new tests added across Tasks 1-5 on top of the existing 116).

- [ ] **Step 2: Run the full frontend build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Both clean.

- [ ] **Step 3: Manual browser walkthrough**

Start both servers:
```bash
uvicorn backend_api:app --port 8000 &
cd frontend && VITE_API_BASE_URL=http://localhost:8000 npm run dev &
```

Using the browser: navigate to the questionnaire, verify:
1. Stage 1 cards show numbered rank badges (①②③) in tap order, not checkmarks, and a card tapped again removes its badge and renumbers the rest correctly.
2. Copy reads "Rank {MIN}-{MAX}" / "N of 4 ranked" language, not "selected."
3. Stage 2 now shows "Question 1 of 20" (not "of 11" or "of 12"), and the first several questions belong to the rank-1 category, then rank-2, etc.
4. Questions whose category was ranked show a "Priority #N" badge next to the category badge; questions from unranked categories show no such badge.
5. Submission screen shows "X of 20 answered."
6. Results page still renders without errors (candidates will be empty without a real zip-code election search + API keys, matching the previous redesign's smoke-test limitation — that's expected, not a regression).

Kill both background servers when done.

- [ ] **Step 4: Fix any issues found, re-run Steps 1-2, then final commit if anything changed**

If Step 3 surfaces any bug, fix it in the relevant file from Tasks 1-10, re-run `pytest -v` and `npx tsc --noEmit && npm run build`, then:

```bash
git add -A
git commit -m "Fix issues found in manual verification of ranked-priorities flow"
```

If nothing needed fixing, no commit is needed for this task.

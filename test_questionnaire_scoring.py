import pytest

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


def test_all_20_questions_present_with_valid_categories():
    assert len(QUESTIONS) == 20
    assert len(QUESTIONS_BY_ID) == 20
    valid_categories = {
        "housing",
        "taxes",
        "safety",
        "education",
        "transportation",
        "environment",
        "accountability",
    }
    for question in QUESTIONS:
        assert question.category in valid_categories
        assert 0 <= question.econ_weight <= 2
        assert 0 <= question.social_weight <= 2


def _housing_question_ids():
    return [q.id for q in QUESTIONS if q.category == "housing"]


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


def test_all_question_ids_are_unique():
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))


# --- Effective weight derivation (derive_effective_weights) ------------------


def test_selected_category_question_gets_weight_five():
    weights = derive_effective_weights(["housing"], ["housing_zoning_density"])
    assert weights["housing_zoning_density"] == 5


def test_nonselected_core_question_gets_baseline_weight_two_not_zero():
    # taxes_shortfall is a core question but "taxes" was not selected here.
    weights = derive_effective_weights(["housing"], ["taxes_shortfall"])
    assert weights["taxes_shortfall"] == 2
    assert weights["taxes_shortfall"] != 0


def test_derive_effective_weights_ignores_unanswered_question_ids():
    weights = derive_effective_weights(["housing"], ["housing_zoning_density"])
    assert "taxes_shortfall" not in weights
    assert set(weights.keys()) == {"housing_zoning_density"}


def test_derive_effective_weights_skips_unknown_question_id():
    weights = derive_effective_weights(["housing"], ["not_a_real_question"])
    assert weights == {}


# --- Priority radar (compute_radar_scores) -----------------------------------


def test_radar_score_is_100_for_selected_category():
    scores = compute_radar_scores(["housing"], [])
    assert scores["housing"] == pytest.approx(100.0)


def test_radar_score_is_40_for_nonselected_but_answered_category():
    scores = compute_radar_scores(["housing"], ["taxes_shortfall"])
    assert scores["taxes"] == pytest.approx(40.0)


def test_radar_score_is_0_for_completely_unrepresented_category():
    scores = compute_radar_scores(["housing"], ["taxes_shortfall"])
    assert scores["safety"] == pytest.approx(0.0)


def test_radar_score_selected_category_wins_over_answered_baseline():
    # A category that's both selected AND answered still scores 100, not 40.
    scores = compute_radar_scores(["housing"], ["housing_zoning_density"])
    assert scores["housing"] == pytest.approx(100.0)


def test_radar_scores_cover_all_seven_categories():
    scores = compute_radar_scores([], [])
    assert set(scores.keys()) == set(CATEGORY_LABELS)
    assert all(v == pytest.approx(0.0) for v in scores.values())


def test_compass_econ_score_at_positive_extreme():
    # housing_zoning_density has econ_weight=2; answer=5 fully favors approach 2 (market side)
    econ, social = compute_compass_scores({"housing_zoning_density": 5})
    assert econ == pytest.approx(100.0)
    assert social == pytest.approx(0.0)


def test_compass_econ_score_at_negative_extreme():
    econ, _ = compute_compass_scores({"housing_zoning_density": 1})
    assert econ == pytest.approx(-100.0)


def test_compass_score_is_zero_for_neutral_answer():
    econ, _ = compute_compass_scores({"housing_zoning_density": 3})
    assert econ == pytest.approx(0.0)


def test_compass_score_is_zero_when_no_weighted_questions_answered():
    econ, social = compute_compass_scores({})
    assert econ == pytest.approx(0.0)
    assert social == pytest.approx(0.0)


def test_compass_combines_multiple_weighted_questions():
    # housing_zoning_density: econ_weight=2, answer=5 -> position=1, contribution=2
    # housing_affordable_mandate: econ_weight=1, answer=1 -> position=-1, contribution=-1
    # weighted_sum = 1, weight_total = 3 -> raw = 1/3 -> scaled = 100/3
    econ, _ = compute_compass_scores(
        {"housing_zoning_density": 5, "housing_affordable_mandate": 1}
    )
    assert econ == pytest.approx(100 / 3)


def test_compass_social_axis_independent_of_econ_only_questions():
    # safety_lowlevel_response has social_weight=2, econ_weight=0
    econ, social = compute_compass_scores({"safety_lowlevel_response": 5})
    assert econ == pytest.approx(0.0)
    assert social == pytest.approx(100.0)


def test_compatibility_perfect_match():
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5},
        voter_importance={"housing_zoning_density": 5},
        candidate_positions={"housing_zoning_density": 5},
    )
    assert result["overall_pct"] == pytest.approx(100.0)
    assert result["question_count"] == 1


def test_compatibility_complete_mismatch():
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5},
        voter_importance={"housing_zoning_density": 5},
        candidate_positions={"housing_zoning_density": 1},
    )
    assert result["overall_pct"] == pytest.approx(0.0)


def test_compatibility_partial_match():
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5},
        voter_importance={"housing_zoning_density": 5},
        candidate_positions={"housing_zoning_density": 3},
    )
    # compatibility_i = 1 - (2/4) = 0.5 -> 50%
    assert result["overall_pct"] == pytest.approx(50.0)


def test_compatibility_excludes_questions_missing_candidate_position():
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5, "taxes_shortfall": 2},
        voter_importance={"housing_zoning_density": 5, "taxes_shortfall": 5},
        candidate_positions={"housing_zoning_density": 5},  # no taxes_shortfall position
    )
    assert result["question_count"] == 1
    assert result["overall_pct"] == pytest.approx(100.0)


def test_compatibility_returns_none_with_no_overlapping_questions():
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5},
        voter_importance={"housing_zoning_density": 5},
        candidate_positions={},
    )
    assert result["overall_pct"] is None
    assert result["by_category"] == {}
    assert result["question_count"] == 0


def test_compatibility_by_category_weighted_average():
    # Two housing questions: one perfect match weighted high, one mismatch weighted low
    result = compute_candidate_compatibility(
        voter_answers={"housing_zoning_density": 5, "housing_affordable_mandate": 5},
        voter_importance={"housing_zoning_density": 5, "housing_affordable_mandate": 1},
        candidate_positions={"housing_zoning_density": 5, "housing_affordable_mandate": 1},
    )
    # q1: compat=1, importance=5 -> weight*compat = 5
    # q2: compat=0, importance=1 -> weight*compat = 0
    # category avg = (5+0)/(5+1) = 0.8333 -> 83.33%
    assert result["by_category"]["housing"] == pytest.approx(500 / 6)


# --- End-to-end: derive_effective_weights feeding compute_candidate_compatibility ---


def test_unasked_questions_do_not_affect_compatibility():
    # Only the answered question is ever in voter_answers, so derive_effective_weights
    # never produces a weight for an unasked question, and compute_candidate_compatibility
    # never sees it -- adding more QUESTIONS to the bank can't change this result.
    answers = {"housing_zoning_density": 5}
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(answers, weights, {"housing_zoning_density": 5})
    assert result["overall_pct"] == pytest.approx(100.0)
    assert result["question_count"] == 1


def test_skipped_question_does_not_affect_compatibility():
    # A "Not Sure / Skip" answer is simply never added to voter_answers by the
    # frontend, so it behaves identically to an unasked question here.
    answers = {"housing_zoning_density": 5}  # taxes_shortfall was skipped, never included
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(
        answers, weights, {"housing_zoning_density": 5, "taxes_shortfall": 1}
    )
    assert result["question_count"] == 1


def test_unknown_candidate_position_remains_excluded_even_with_derived_weights():
    answers = {"housing_zoning_density": 5, "taxes_shortfall": 2}
    weights = derive_effective_weights(["housing"], answers.keys())
    # Candidate has no documented position on taxes_shortfall at all.
    result = compute_candidate_compatibility(answers, weights, {"housing_zoning_density": 5})
    assert result["question_count"] == 1
    assert "taxes" not in result["by_category"]


def test_selected_category_weight_dominates_nonselected_in_overall_compatibility():
    # housing selected (weight 5, mismatched), taxes nonselected (weight 2, perfect match) --
    # overall should be pulled toward the mismatch since it's weighted more heavily.
    answers = {"housing_zoning_density": 5, "taxes_shortfall": 2}
    weights = derive_effective_weights(["housing"], answers.keys())
    result = compute_candidate_compatibility(
        answers, weights, {"housing_zoning_density": 1, "taxes_shortfall": 2}
    )
    # housing: compat=0, weight=5 -> 0; taxes: compat=1, weight=2 -> 2
    # overall = 100 * 2 / 7
    assert result["overall_pct"] == pytest.approx(200 / 7)

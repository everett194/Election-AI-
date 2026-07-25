import pytest

from questionnaire_scoring import (
    QUESTIONS,
    QUESTIONS_BY_ID,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
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


def test_radar_score_is_100_when_all_answers_in_category_are_top_importance():
    housing_ids = _housing_question_ids()
    importance = {qid: 5 for qid in housing_ids}
    scores = compute_radar_scores(importance)
    assert scores["housing"] == pytest.approx(100.0)


def test_radar_score_is_0_when_all_answers_in_category_are_lowest_importance():
    housing_ids = _housing_question_ids()
    importance = {qid: 1 for qid in housing_ids}
    scores = compute_radar_scores(importance)
    assert scores["housing"] == pytest.approx(0.0)


def test_radar_score_is_50_for_moderate_importance():
    housing_ids = _housing_question_ids()
    importance = {qid: 3 for qid in housing_ids}
    scores = compute_radar_scores(importance)
    assert scores["housing"] == pytest.approx(50.0)


def test_radar_score_is_0_for_unanswered_category():
    scores = compute_radar_scores({})
    assert scores["taxes"] == pytest.approx(0.0)
    assert set(scores.keys()) == {
        "housing",
        "taxes",
        "safety",
        "education",
        "transportation",
        "environment",
        "accountability",
    }


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

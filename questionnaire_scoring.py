"""
Pure scoring logic for the 20-question local-election questionnaire, implementing
the exact formulas in questionnaire.md / questionsfinal.md:

- compute_radar_scores: how much the voter prioritizes each of 7 policy categories.
- compute_compass_scores: voter placement on the economic and social/institutional axes.
- compute_candidate_compatibility: voter-candidate match, using only questions where a
  real candidate position exists -- never a fabricated or inferred one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    econ_weight: int
    social_weight: int
    text: str
    approach_1: str
    approach_2: str


CATEGORY_LABELS: dict[str, str] = {
    "housing": "Housing, zoning & development",
    "taxes": "Taxes, budgets & public spending",
    "safety": "Public safety & criminal justice",
    "education": "Education & youth services",
    "transportation": "Transportation & infrastructure",
    "environment": "Environment, land use & public spaces",
    "accountability": "Government accountability & community participation",
}

QUESTIONS: list[Question] = [
    Question(
        id="housing_zoning_density",
        category="housing",
        econ_weight=2,
        social_weight=0,
        text="Should more apartments and duplexes be allowed?",
        approach_1="No—protect existing neighborhoods.",
        approach_2="Yes—allow more housing.",
    ),
    Question(
        id="housing_affordable_mandate",
        category="housing",
        econ_weight=1,
        social_weight=0,
        text="Should developers be required to build affordable housing?",
        approach_1="Yes—require affordable units.",
        approach_2="No—use incentives instead.",
    ),
    Question(
        id="housing_preservation_redevelopment",
        category="housing",
        econ_weight=2,
        social_weight=0,
        text="Should older buildings be easier to redevelop?",
        approach_1="No—protect historic buildings.",
        approach_2="Yes—make redevelopment easier.",
    ),
    Question(
        id="taxes_shortfall",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="Should taxes rise to protect public services?",
        approach_1="Yes—maintain public services.",
        approach_2="No—keep taxes lower.",
    ),
    Question(
        id="taxes_business_incentives",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="Should businesses receive local tax breaks?",
        approach_1="No—spend money elsewhere.",
        approach_2="Yes—attract businesses and jobs.",
    ),
    Question(
        id="taxes_capital_debt",
        category="taxes",
        econ_weight=1,
        social_weight=0,
        text="Should local government borrow for major projects?",
        approach_1="No—save and pay gradually.",
        approach_2="Yes—complete projects sooner.",
    ),
    Question(
        id="safety_lowlevel_response",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="How should minor offenses be handled?",
        approach_1="More arrests and prosecution.",
        approach_2="More treatment and alternatives.",
    ),
    Question(
        id="safety_police_funding",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="Where should public-safety funding go?",
        approach_1="More police funding.",
        approach_2="More community and crisis programs.",
    ),
    Question(
        id="safety_bail_pretrial",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="Should people accused of nonviolent crimes have to pay bail?",
        approach_1="Yes—use cash bail or detention.",
        approach_2="No—use non-cash release options.",
    ),
    Question(
        id="education_funding_levy",
        category="education",
        econ_weight=2,
        social_weight=0,
        text="Should school funding rise if taxes must rise?",
        approach_1="Yes—fund schools more.",
        approach_2="No—keep school taxes lower.",
    ),
    Question(
        id="education_choice_vs_traditional",
        category="education",
        econ_weight=1,
        social_weight=1,
        text="Should families have more school choices?",
        approach_1="No—focus on neighborhood public schools.",
        approach_2="Yes—expand school-choice options.",
    ),
    Question(
        id="education_youth_services",
        category="education",
        econ_weight=1,
        social_weight=0,
        text="Should local government spend more on youth programs?",
        approach_1="Yes—expand youth services.",
        approach_2="No—keep spending lower.",
    ),
    Question(
        id="transportation_mode_priority",
        category="transportation",
        econ_weight=0,
        social_weight=0,
        text="What should transportation funding prioritize?",
        approach_1="Roads, parking, and cars.",
        approach_2="Transit, bikes, and walking.",
    ),
    Question(
        id="transportation_funding_mechanism",
        category="transportation",
        econ_weight=1,
        social_weight=0,
        text="Who should pay for roads and infrastructure?",
        approach_1="All taxpayers.",
        approach_2="Users and developers.",
    ),
    Question(
        id="environment_regulation_cost",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should development face stricter environmental rules?",
        approach_1="Yes—stronger environmental protections.",
        approach_2="No—fewer development restrictions.",
    ),
    Question(
        id="environment_parks_vs_development",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should open land be preserved or developed?",
        approach_1="Preserve parks and open space.",
        approach_2="Allow more private development.",
    ),
    Question(
        id="environment_climate_resilience",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should local government spend more to prepare for extreme weather?",
        approach_1="Yes—invest in protection now.",
        approach_2="No—prioritize other needs.",
    ),
    Question(
        id="accountability_neighborhood_control",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="Who should control neighborhood decisions?",
        approach_1="City or county leaders.",
        approach_2="Neighborhoods and community boards.",
    ),
    Question(
        id="accountability_public_input",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="Should major decisions require more public input?",
        approach_1="No—make decisions faster.",
        approach_2="Yes—allow more public input.",
    ),
    Question(
        id="accountability_elected_vs_appointed",
        category="accountability",
        econ_weight=0,
        social_weight=1,
        text="Should more local boards be elected?",
        approach_1="No—keep boards appointed.",
        approach_2="Yes—let voters choose.",
    ),
]

QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}


def compute_radar_scores(importance_by_id: dict[str, int]) -> dict[str, float]:
    """category -> 0..100 score representing how much the voter prioritizes that category.

    Unanswered categories score 0 rather than being omitted, so every radar axis is defined.
    """
    values_by_category: dict[str, list[int]] = {category: [] for category in CATEGORY_LABELS}
    for question in QUESTIONS:
        if question.id in importance_by_id:
            values_by_category[question.category].append(importance_by_id[question.id])

    scores: dict[str, float] = {}
    for category, values in values_by_category.items():
        if not values:
            scores[category] = 0.0
            continue
        avg_importance = sum(values) / len(values)
        scores[category] = 100 * (avg_importance - 1) / 4
    return scores


def _axis_score(answer_by_id: dict[str, int], weight_attr: str) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for question in QUESTIONS:
        weight = getattr(question, weight_attr)
        if weight == 0 or question.id not in answer_by_id:
            continue
        position = (answer_by_id[question.id] - 3) / 2
        weighted_sum += weight * position
        weight_total += weight
    if weight_total == 0:
        return 0.0
    return (weighted_sum / weight_total) * 100


def compute_compass_scores(answer_by_id: dict[str, int]) -> tuple[float, float]:
    """Returns (economic_score, social_score), each rescaled to -100..100.

    Uses only questions with a non-zero weight on that axis, per the framework.
    """
    econ_score = _axis_score(answer_by_id, "econ_weight")
    social_score = _axis_score(answer_by_id, "social_weight")
    return econ_score, social_score


def compute_candidate_compatibility(
    voter_answers: dict[str, int],
    voter_importance: dict[str, int],
    candidate_positions: dict[str, int],
) -> dict:
    """Voter-candidate compatibility using only questions where BOTH a voter answer and a
    verified candidate position exist. A missing candidate position is excluded, never
    treated as neutral -- per the framework's explicit instruction not to penalize or
    credit candidates for positions that are simply unknown.

    Returns {"overall_pct": float | None, "by_category": dict[str, float], "question_count": int}.
    overall_pct is None when there are zero qualifying questions.
    """
    per_question: list[tuple[Question, float, int]] = []
    for question in QUESTIONS:
        if question.id not in voter_answers or question.id not in candidate_positions:
            continue
        voter_value = voter_answers[question.id]
        candidate_value = candidate_positions[question.id]
        importance = voter_importance.get(question.id, 3)
        compatibility = 1 - (abs(voter_value - candidate_value) / 4)
        per_question.append((question, compatibility, importance))

    if not per_question:
        return {"overall_pct": None, "by_category": {}, "question_count": 0}

    weight_total = sum(importance for _, _, importance in per_question)
    overall_pct = 100 * sum(
        compatibility * importance for _, compatibility, importance in per_question
    ) / weight_total

    grouped: dict[str, list[tuple[float, int]]] = {}
    for question, compatibility, importance in per_question:
        grouped.setdefault(question.category, []).append((compatibility, importance))

    by_category: dict[str, float] = {}
    for category, values in grouped.items():
        category_weight_total = sum(importance for _, importance in values)
        by_category[category] = 100 * sum(
            compatibility * importance for compatibility, importance in values
        ) / category_weight_total

    return {
        "overall_pct": overall_pct,
        "by_category": by_category,
        "question_count": len(per_question),
    }

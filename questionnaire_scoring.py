"""
Pure scoring logic for the 20-question local-election questionnaire, implementing
the exact formulas in questionnaire.md / questionsfinal.md:

- compute_radar_scores: how much the voter prioritizes each of 7 policy categories.
- compute_compass_scores: voter placement on the economic and social/institutional axes.
- compute_candidate_compatibility: voter-candidate match, using only questions where a
  real candidate position exists -- never a fabricated or inferred one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    econ_weight: int
    social_weight: int
    text: str
    approach_1: str
    approach_2: str
    selection_priority: int = 0  # lower = picked first in ranked categories
    research_terms: tuple[str, ...] = field(default_factory=tuple)  # extra Tavily query terms


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
        selection_priority=1,
        research_terms=("zoning reform", "upzoning", "duplexes", "multifamily housing"),
    ),
    Question(
        id="housing_affordable_mandate",
        category="housing",
        econ_weight=1,
        social_weight=0,
        text="Should developers be required to build affordable housing?",
        approach_1="Yes—require affordable units.",
        approach_2="No—use incentives instead.",
        selection_priority=1,
        research_terms=("affordable housing mandate", "inclusionary zoning"),
    ),
    Question(
        id="housing_preservation_redevelopment",
        category="housing",
        econ_weight=2,
        social_weight=0,
        text="Should older buildings be easier to redevelop?",
        approach_1="No—protect historic buildings.",
        approach_2="Yes—make redevelopment easier.",
        selection_priority=2,
        research_terms=("historic preservation", "redevelopment"),
    ),
    Question(
        id="taxes_shortfall",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="Should taxes rise to protect public services?",
        approach_1="Yes—maintain public services.",
        approach_2="No—keep taxes lower.",
        selection_priority=1,
        research_terms=("property tax levy", "tax increase"),
    ),
    Question(
        id="taxes_business_incentives",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="Should businesses receive local tax breaks?",
        approach_1="No—spend money elsewhere.",
        approach_2="Yes—attract businesses and jobs.",
        selection_priority=1,
        research_terms=("business tax incentives", "tax abatement"),
    ),
    Question(
        id="taxes_capital_debt",
        category="taxes",
        econ_weight=1,
        social_weight=0,
        text="Should local government borrow for major projects?",
        approach_1="No—save and pay gradually.",
        approach_2="Yes—complete projects sooner.",
        selection_priority=2,
        research_terms=("municipal bond", "capital borrowing"),
    ),
    Question(
        id="safety_lowlevel_response",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="How should minor offenses be handled?",
        approach_1="More arrests and prosecution.",
        approach_2="More treatment and alternatives.",
        selection_priority=1,
        research_terms=("diversion program", "alternatives to arrest"),
    ),
    Question(
        id="safety_police_funding",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="Where should public-safety funding go?",
        approach_1="More police funding.",
        approach_2="More community and crisis programs.",
        selection_priority=1,
        research_terms=("police budget", "public safety funding"),
    ),
    Question(
        id="safety_bail_pretrial",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="Should people accused of nonviolent crimes have to pay bail?",
        approach_1="Yes—use cash bail or detention.",
        approach_2="No—use non-cash release options.",
        selection_priority=2,
        research_terms=("cash bail", "pretrial release"),
    ),
    Question(
        id="education_funding_levy",
        category="education",
        econ_weight=2,
        social_weight=0,
        text="Should school funding rise if taxes must rise?",
        approach_1="Yes—fund schools more.",
        approach_2="No—keep school taxes lower.",
        selection_priority=1,
        research_terms=("school funding levy", "education budget"),
    ),
    Question(
        id="education_choice_vs_traditional",
        category="education",
        econ_weight=1,
        social_weight=1,
        text="Should families have more school choices?",
        approach_1="No—focus on neighborhood public schools.",
        approach_2="Yes—expand school-choice options.",
        selection_priority=1,
        research_terms=("school choice", "charter schools"),
    ),
    Question(
        id="education_youth_services",
        category="education",
        econ_weight=1,
        social_weight=0,
        text="Should local government spend more on youth programs?",
        approach_1="Yes—expand youth services.",
        approach_2="No—keep spending lower.",
        selection_priority=2,
        research_terms=("youth programs funding",),
    ),
    Question(
        id="transportation_mode_priority",
        category="transportation",
        econ_weight=0,
        social_weight=0,
        text="What should transportation funding prioritize?",
        approach_1="Roads, parking, and cars.",
        approach_2="Transit, bikes, and walking.",
        selection_priority=1,
        research_terms=("transit funding", "bike lanes", "road funding"),
    ),
    Question(
        id="transportation_funding_mechanism",
        category="transportation",
        econ_weight=1,
        social_weight=0,
        text="Who should pay for roads and infrastructure?",
        approach_1="All taxpayers.",
        approach_2="Users and developers.",
        selection_priority=2,
        research_terms=("infrastructure funding", "impact fees"),
    ),
    Question(
        id="environment_regulation_cost",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should development face stricter environmental rules?",
        approach_1="Yes—stronger environmental protections.",
        approach_2="No—fewer development restrictions.",
        selection_priority=1,
        research_terms=("environmental regulation", "development restrictions"),
    ),
    Question(
        id="environment_parks_vs_development",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should open land be preserved or developed?",
        approach_1="Preserve parks and open space.",
        approach_2="Allow more private development.",
        selection_priority=2,
        research_terms=("parks preservation", "open space"),
    ),
    Question(
        id="environment_climate_resilience",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should local government spend more to prepare for extreme weather?",
        approach_1="Yes—invest in protection now.",
        approach_2="No—prioritize other needs.",
        selection_priority=3,
        research_terms=("climate resilience", "extreme weather preparedness"),
    ),
    Question(
        id="accountability_neighborhood_control",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="Who should control neighborhood decisions?",
        approach_1="City or county leaders.",
        approach_2="Neighborhoods and community boards.",
        selection_priority=1,
        research_terms=("neighborhood councils", "community boards"),
    ),
    Question(
        id="accountability_public_input",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="Should major decisions require more public input?",
        approach_1="No—make decisions faster.",
        approach_2="Yes—allow more public input.",
        selection_priority=1,
        research_terms=("public input", "community engagement"),
    ),
    Question(
        id="accountability_elected_vs_appointed",
        category="accountability",
        econ_weight=0,
        social_weight=1,
        text="Should more local boards be elected?",
        approach_1="No—keep boards appointed.",
        approach_2="Yes—let voters choose.",
        selection_priority=2,
        research_terms=("elected boards", "appointed commissions"),
    ),
]

QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}


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

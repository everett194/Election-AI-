"""
Pure scoring logic for the 20-question local-election questionnaire, implementing
the exact formulas in questionnaire.md / local-election-questionnaire.pdf:

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
        text="When it comes to zoning in residential neighborhoods, which approach should the city or county prioritize?",
        approach_1="Maintain current limits on multi-family and higher-density housing to preserve existing neighborhood character.",
        approach_2="Loosen zoning restrictions to allow more apartments, duplexes, and multi-family homes to be built.",
    ),
    Question(
        id="housing_affordable_mandate",
        category="housing",
        econ_weight=1,
        social_weight=0,
        text="How should local government try to increase the supply of affordable housing?",
        approach_1="Require developers to set aside a share of affordable units in new residential projects (mandatory inclusionary zoning).",
        approach_2="Rely on tax incentives, expedited permitting, or public-private partnerships to encourage, not require, affordable units.",
    ),
    Question(
        id="housing_preservation_redevelopment",
        category="housing",
        econ_weight=2,
        social_weight=0,
        text="Should the city or county make it easier or harder to redevelop older buildings and lots, including through historic-preservation or design-review rules?",
        approach_1="Strengthen preservation and design-review requirements to protect existing buildings and neighborhood character.",
        approach_2="Ease preservation and design-review requirements to make redevelopment and new construction faster and less costly.",
    ),
    Question(
        id="taxes_shortfall",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="If local government faced a budget shortfall, which should it prioritize?",
        approach_1="Raise local taxes or fees to maintain current service levels.",
        approach_2="Cut spending or reduce services to avoid raising local taxes or fees.",
    ),
    Question(
        id="taxes_business_incentives",
        category="taxes",
        econ_weight=2,
        social_weight=0,
        text="Should local government offer tax breaks or subsidies to attract new businesses and development?",
        approach_1="Limit or reduce tax breaks and subsidies for businesses, relying on general revenue for community priorities instead.",
        approach_2="Continue or expand tax breaks and incentives to attract businesses and development.",
    ),
    Question(
        id="taxes_capital_debt",
        category="taxes",
        econ_weight=1,
        social_weight=0,
        text="How should local government pay for large capital projects, such as a new fire station or major road project?",
        approach_1="Fund projects gradually through the regular budget or reserves, even if it means delaying projects.",
        approach_2="Borrow through bonds or debt financing to complete projects sooner, even if it costs more in interest over time.",
    ),
    Question(
        id="safety_lowlevel_response",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="How should local government respond to low-level, nonviolent offenses such as minor drug possession or public disorder?",
        approach_1="Prioritize arrest, citation, and prosecution as the primary response.",
        approach_2="Prioritize diversion programs, treatment referrals, or civil citations instead of arrest and prosecution.",
    ),
    Question(
        id="safety_police_funding",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="Should local government increase or decrease funding and staffing for police relative to other public-safety approaches?",
        approach_1="Increase police funding and staffing as the priority.",
        approach_2="Redirect funding toward non-police approaches, such as mental-health crisis teams or violence-interruption programs.",
    ),
    Question(
        id="safety_bail_pretrial",
        category="safety",
        econ_weight=0,
        social_weight=2,
        text="How should the local criminal justice system handle pretrial release for people awaiting trial on non-violent charges?",
        approach_1="Rely on cash bail and pretrial detention to help ensure court appearance and public safety.",
        approach_2="Expand non-monetary release options, such as personal recognizance or supervised release, to reduce pretrial detention.",
    ),
    Question(
        id="education_funding_levy",
        category="education",
        econ_weight=2,
        social_weight=0,
        text="Should local school funding be increased, even if it requires higher local property taxes or a school levy?",
        approach_1="Increase school funding and programs, even if it requires higher local taxes or a levy.",
        approach_2="Hold the line on local school taxes, even if it limits funding for new programs.",
    ),
    Question(
        id="education_choice_vs_traditional",
        category="education",
        econ_weight=1,
        social_weight=1,
        text="Should local education policy prioritize expanding school-choice options, or prioritize investment in traditional neighborhood public schools?",
        approach_1="Prioritize investment in traditional neighborhood public schools.",
        approach_2="Prioritize expanding school-choice options, such as charter schools or open enrollment.",
    ),
    Question(
        id="education_youth_services",
        category="education",
        econ_weight=1,
        social_weight=0,
        text="Should local government expand funding for youth services outside of school, such as after-school programs, libraries, or recreation centers?",
        approach_1="Expand funding for after-school and youth recreation or library programs, even if it requires new spending.",
        approach_2="Keep youth-services spending at current levels and rely on schools, nonprofits, or families to fill gaps.",
    ),
    Question(
        id="transportation_mode_priority",
        category="transportation",
        econ_weight=0,
        social_weight=0,
        text="When local government has limited transportation funding, which should it prioritize?",
        approach_1="Expanding and maintaining road capacity for cars, including new lanes, parking, and road repair.",
        approach_2="Expanding public transit, bike lanes, and pedestrian infrastructure.",
    ),
    Question(
        id="transportation_funding_mechanism",
        category="transportation",
        econ_weight=1,
        social_weight=0,
        text="How should local road and infrastructure improvements be funded?",
        approach_1="Fund improvements through general local taxes shared across all residents.",
        approach_2="Fund improvements through user fees, tolls, or charges tied to specific developments or users.",
    ),
    Question(
        id="environment_regulation_cost",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should local government adopt stricter environmental rules for local development and business, even if it raises costs for developers or businesses?",
        approach_1="Adopt stricter local environmental rules, even if it raises costs for development or business.",
        approach_2="Limit local environmental rules to reduce costs and regulatory burden on development and business.",
    ),
    Question(
        id="environment_parks_vs_development",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="When land becomes available, should local government prioritize acquiring or preserving it as parks and open space, or prioritize allowing private development?",
        approach_1="Prioritize acquiring or preserving land as parks and public open space.",
        approach_2="Prioritize allowing private development of available land.",
    ),
    Question(
        id="environment_climate_resilience",
        category="environment",
        econ_weight=2,
        social_weight=0,
        text="Should local government invest in climate-resilience projects, such as flood control, stormwater upgrades, or extreme-heat preparedness, even if it requires new spending or fees?",
        approach_1="Invest in climate-resilience projects now, even if it requires new local spending or fees.",
        approach_2="Limit new spending on climate-resilience projects unless required, prioritizing other budget needs.",
    ),
    Question(
        id="accountability_neighborhood_control",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="For decisions that affect specific neighborhoods, such as zoning changes or new development, how much power should neighborhoods or community boards have relative to citywide government?",
        approach_1="Centralize authority with the city or county government to ensure consistent, citywide standards.",
        approach_2="Give neighborhoods, community boards, or local advisory councils more direct authority over decisions that affect them.",
    ),
    Question(
        id="accountability_public_input",
        category="accountability",
        econ_weight=0,
        social_weight=2,
        text="Should local government be required to hold more extensive public-comment periods before major decisions, even if it slows down decision-making?",
        approach_1="Streamline decision-making with fewer or shorter public-input requirements.",
        approach_2="Require more extensive public comment and community input, even if it slows decisions.",
    ),
    Question(
        id="accountability_elected_vs_appointed",
        category="accountability",
        econ_weight=0,
        social_weight=1,
        text="Should more local oversight bodies, such as police oversight boards, planning commissions, or utility boards, be filled by direct election rather than appointment?",
        approach_1="Keep these positions appointed by elected officials, to preserve accountability through the existing chain of command.",
        approach_2="Make more of these positions directly elected, to increase independent accountability to voters.",
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

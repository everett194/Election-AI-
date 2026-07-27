"""
questionnaire_ui.py

Rendering for the 20-question local-issues questionnaire from
local-election-questionnaire.pdf / questionnaire.md. Called inline from
streamlitrun.py -- not a separate page. Computes the voter's 7-category
radar chart and 2-axis ideological compass from their own answers, then
overlays every candidate found for the zip code using sourced, real-search
positions (election_lookup.research_candidates_via_tavily -- a parallel
Tavily search fan-out per candidate, then one Claude call per race that
reads only that evidence, tagging each answer "explicit" / "strong_inference"
/ "weak_inference" -- never from party/endorsements/demographics alone)
so the voter gets a visual comparison without waiting on one search per
candidate.
"""

import math

import altair as alt
import pandas as pd
import streamlit as st

from election_lookup import CandidateIssueProfile, Race, research_candidates_via_tavily
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    QUESTIONS_BY_ID,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
)

IMPORTANCE_LABELS = [
    "Not important to me",
    "Slightly important",
    "Moderately important",
    "Very important",
    "One of my top priorities",
]

CHART_DOMAIN = [-140, 140]

CANDIDATE_COLORS = ["#9D755D", "#54A24B", "#F58518", "#B279A2", "#72B7B2"]

OFFICE_LABELS = {
    "mayor": "Mayoral",
    "county": "County",
    "us_house": "U.S. House",
}


def _candidate_cache_key(zipcode: str, office: str, candidate_name: str) -> tuple[str, str, str]:
    return (zipcode, office, candidate_name)


def _pending_candidates(from_zip: str, race: Race) -> list:
    return [
        candidate
        for candidate in race.candidates
        if _candidate_cache_key(from_zip, race.office, candidate.name)
        not in st.session_state.candidate_profiles
    ]


def _auto_research_candidates(from_zip: str | None, races: list[Race] | None) -> None:
    """Automatically research every not-yet-researched candidate across all
    races found for this zip code, and cache the results, so the voter
    doesn't have to trigger it per candidate. Per race: a parallel Tavily
    search fan-out gathers real evidence for every candidate in that race,
    then one Claude call reads only that evidence and answers the 20
    questions -- fast because Claude isn't running its own search loop, the
    evidence is already in hand.

    Each race's results are committed to session state immediately after its
    search returns, with no other Streamlit call in between -- so
    interrupting one race's search (e.g. by clicking something else) never
    loses an already-completed race's results. The next rerun just resumes
    with whatever races still have a candidate missing a profile.
    """
    if not (from_zip and races):
        return

    pending_races = [race for race in races if _pending_candidates(from_zip, race)]
    if not pending_races:
        return

    with st.status(
        "Researching candidates' sourced positions on the 20 questions...",
        expanded=True,
    ) as status:
        st.write(
            "Running a parallel search fan-out per race (covering every "
            "candidate in that race at once), across every race found for "
            "this zip code."
        )
        for race in pending_races:
            candidates = _pending_candidates(from_zip, race)
            try:
                researched_by_name = research_candidates_via_tavily(
                    from_zip, race.office, race.jurisdiction_name, candidates
                )
            except Exception as exc:
                researched_by_name = {}
                status.write(f"Could not research candidates for the {race.office} race: {exc}")

            for candidate in candidates:
                key = _candidate_cache_key(from_zip, race.office, candidate.name)
                profile = researched_by_name.get(candidate.name) or CandidateIssueProfile(
                    candidate_name=candidate.name,
                    office=race.office,
                    positions={},
                    sourced_positions=[],
                )
                st.session_state.candidate_profiles[key] = profile
                if profile.positions:
                    st.session_state.mapped_candidates.add(key)

            if researched_by_name:
                status.write(f"Researched {len(candidates)} candidate(s) for the {race.office} race.")
        status.update(label="Candidate research complete", state="complete", expanded=False)


def _radar_chart(
    scores_by_category: dict[str, float],
    candidate_series: list[tuple[str, dict[str, float], str]] | None = None,
) -> alt.LayerChart:
    categories = list(CATEGORY_LABELS.keys())
    angle_step = 2 * math.pi / len(categories)

    def to_point(series_name: str, category: str, index: int, radius: float) -> dict:
        angle = -math.pi / 2 + index * angle_step
        return {
            "series": series_name,
            "category": CATEGORY_LABELS[category],
            "x": radius * math.cos(angle),
            "y": radius * math.sin(angle),
        }

    voter_points = [
        to_point("Your priorities", category, i, scores_by_category.get(category, 0.0))
        for i, category in enumerate(categories)
    ]
    voter_points.append(voter_points[0])
    voter_df = pd.DataFrame(voter_points)

    all_series = [("Your priorities", scores_by_category, "#4C78A8")] + list(candidate_series or [])
    polygon_rows: list[dict] = []
    for series_name, scores, _color in all_series:
        covered_indices = [i for i, category in enumerate(categories) if category in scores]
        points = [
            to_point(series_name, categories[i], i, scores[categories[i]])
            for i in covered_indices
        ]
        if points:
            points.append(points[0])
        polygon_rows.extend(points)
    polygon_df = pd.DataFrame(polygon_rows)

    names = [name for name, _scores, _color in all_series]
    colors = [color for _name, _scores, color in all_series]

    label_points = pd.DataFrame([to_point("labels", c, i, 118) for i, c in enumerate(categories)])

    ring_angles = [i * (2 * math.pi / 72) for i in range(73)]
    ring_df = pd.DataFrame(
        [{"x": 100 * math.cos(t), "y": 100 * math.sin(t)} for t in ring_angles]
    )

    x_enc = alt.X("x:Q", axis=None, scale=alt.Scale(domain=CHART_DOMAIN))
    y_enc = alt.Y("y:Q", axis=None, scale=alt.Scale(domain=CHART_DOMAIN))
    color_enc = alt.Color(
        "series:N",
        scale=alt.Scale(domain=names, range=colors),
        legend=alt.Legend(title=None) if candidate_series else None,
    )

    ring = alt.Chart(ring_df).mark_line(color="#cccccc", strokeDash=[2, 2]).encode(x=x_enc, y=y_enc)
    area = alt.Chart(voter_df).mark_area(opacity=0.25, color="#4C78A8").encode(x=x_enc, y=y_enc)
    line = alt.Chart(polygon_df).mark_line().encode(x=x_enc, y=y_enc, color=color_enc)
    points = alt.Chart(polygon_df).mark_point(filled=True).encode(
        x=x_enc, y=y_enc, color=color_enc, tooltip=["series:N", "category:N"]
    )
    labels = alt.Chart(label_points).mark_text(fontSize=11).encode(x=x_enc, y=y_enc, text="category:N")

    return (ring + area + line + points + labels).properties(width=420, height=420)


def _compass_chart(
    econ_score: float,
    social_score: float,
    candidate_points: list[tuple[str, float, float, str]] | None = None,
) -> alt.LayerChart:
    rows = [{"series": "You", "econ": econ_score, "social": social_score}]
    colors = ["#E45756"]
    for name, econ, social, color in candidate_points or []:
        rows.append({"series": name, "econ": econ, "social": social})
        colors.append(color)
    point_df = pd.DataFrame(rows)
    names = [row["series"] for row in rows]

    x_enc = alt.X(
        "econ:Q",
        scale=alt.Scale(domain=[-110, 110]),
        title="Economic axis (public investment <-> markets/private)",
    )
    y_enc = alt.Y(
        "social:Q",
        scale=alt.Scale(domain=[-110, 110]),
        title="Social axis (enforcement/centralized <-> civil liberties/decentralized)",
    )
    color_enc = alt.Color(
        "series:N",
        scale=alt.Scale(domain=names, range=colors),
        legend=alt.Legend(title=None) if candidate_points else None,
    )
    hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cccccc").encode(y="y:Q")
    vline = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#cccccc").encode(x="x:Q")
    point = alt.Chart(point_df).mark_point(size=200, filled=True).encode(
        x=x_enc, y=y_enc, color=color_enc, tooltip=["series:N"]
    )
    return (hline + vline + point).properties(width=420, height=420)


def render_questionnaire(
    from_office: str | None = None,
    from_zip: str | None = None,
    races: list[Race] | None = None,
) -> None:
    """Renders the full questionnaire section inline on the current page."""
    st.divider()
    st.header("Local issues questionnaire")
    st.write(
        "Answer where you stand on 20 local-policy questions. This produces a radar "
        "chart of which issues matter most to you and a two-axis compass showing your "
        "overall lean. Everything shown is computed only from your own answers below."
    )
    if from_office and from_zip:
        st.caption(f"Started from the {from_office} race for zip {from_zip}.")

    with st.form("questionnaire_form"):
        form_answers: dict[str, int] = {}
        form_importance: dict[str, int] = {}

        for category, label in CATEGORY_LABELS.items():
            category_questions = [q for q in QUESTIONS if q.category == category]
            with st.expander(label, expanded=False):
                for question in category_questions:
                    st.markdown(f"**{question.text}**")
                    col1, col2 = st.columns(2)
                    col1.caption(f"1-2: {question.approach_1}")
                    col2.caption(f"4-5: {question.approach_2}")
                    form_answers[question.id] = st.slider(
                        "Your position",
                        min_value=1,
                        max_value=5,
                        value=3,
                        key=f"pos_{question.id}",
                        label_visibility="collapsed",
                    )
                    importance_label = st.select_slider(
                        "How important is this to you?",
                        options=IMPORTANCE_LABELS,
                        value=IMPORTANCE_LABELS[2],
                        key=f"imp_{question.id}",
                    )
                    form_importance[question.id] = IMPORTANCE_LABELS.index(importance_label) + 1
                    st.divider()

        submitted = st.form_submit_button("See my results")

    if submitted:
        st.session_state.questionnaire_answers = form_answers
        st.session_state.questionnaire_importance = form_importance

    if "questionnaire_answers" not in st.session_state:
        return

    if "candidate_profiles" not in st.session_state:
        st.session_state.candidate_profiles = {}
    if "mapped_candidates" not in st.session_state:
        st.session_state.mapped_candidates = set()

    _auto_research_candidates(from_zip, races)

    st.subheader("Your results")
    radar_scores = compute_radar_scores(st.session_state.questionnaire_importance)
    econ_score, social_score = compute_compass_scores(st.session_state.questionnaire_answers)

    candidate_series: list[tuple[str, dict[str, float], str]] = []
    candidate_points: list[tuple[str, float, float, str]] = []
    if from_zip and races:
        color_index = 0
        for race in races:
            for candidate in race.candidates:
                key = _candidate_cache_key(from_zip, race.office, candidate.name)
                if key not in st.session_state.mapped_candidates:
                    continue
                profile = st.session_state.candidate_profiles.get(key)
                if profile is None or not profile.positions:
                    continue
                compatibility = compute_candidate_compatibility(
                    st.session_state.questionnaire_answers,
                    st.session_state.questionnaire_importance,
                    profile.positions,
                )
                if compatibility["question_count"] == 0:
                    continue
                color = CANDIDATE_COLORS[color_index % len(CANDIDATE_COLORS)]
                color_index += 1
                office_label = OFFICE_LABELS.get(race.office, race.office)
                candidate_series.append(
                    (
                        f"Compatibility with {candidate.name} ({office_label})",
                        compatibility["by_category"],
                        color,
                    )
                )
                has_econ, has_social = profile.covered_axes()
                if has_econ and has_social:
                    econ, social = compute_compass_scores(profile.positions)
                    candidate_points.append((f"{candidate.name} ({office_label})", econ, social, color))

    col_radar, col_compass = st.columns(2)
    with col_radar:
        st.markdown("**What matters most to you**")
        st.altair_chart(_radar_chart(radar_scores, candidate_series), width="stretch")
    with col_compass:
        st.markdown("**Your ideological compass**")
        st.altair_chart(_compass_chart(econ_score, social_score, candidate_points), width="stretch")
        st.caption(
            f"Economic axis: {econ_score:.0f} (negative = more public investment/"
            f"regulation, positive = markets/private development/lower taxation). "
            f"Social axis: {social_score:.0f} (negative = more enforcement/authority/"
            f"centralization, positive = civil liberties/rehabilitation/decentralization)."
        )

    _render_candidate_comparison(from_zip, races)


def _render_candidate_comparison(from_zip: str | None, races: list[Race] | None) -> None:
    st.subheader("Compare with candidates")
    non_empty_races = [race for race in (races or []) if race.candidates]
    if not (from_zip and non_empty_races):
        st.info(
            "Candidate compatibility scoring needs candidates' own answers to these same "
            "20 questions from a verified source (official records, direct questionnaire "
            "responses, or clearly sourced campaign statements) -- not a guess drawn from "
            "general search results. No candidates were found for this zip code's races."
        )
        return

    st.caption(
        "Candidates from every race found for this zip code are researched "
        "automatically above; use the buttons below to control which ones show "
        "up on your charts."
    )

    for race in non_empty_races:
        st.markdown(f"#### {OFFICE_LABELS.get(race.office, race.office)}")
        for index, candidate in enumerate(race.candidates):
            key = _candidate_cache_key(from_zip, race.office, candidate.name)
            profile = st.session_state.candidate_profiles.get(key)
            is_mapped = key in st.session_state.mapped_candidates

            with st.container(border=True):
                header = candidate.name
                if candidate.party:
                    header += f" ({candidate.party})"
                st.markdown(f"**{header}**")

                if profile is None:
                    # Auto-research above always populates this before we get here;
                    # skip defensively rather than crash on an unexpected gap.
                    continue

                coverage = len(profile.positions)
                if coverage == 0:
                    st.write("No sourced positions found for this candidate.")
                    continue

                compatibility = compute_candidate_compatibility(
                    st.session_state.questionnaire_answers,
                    st.session_state.questionnaire_importance,
                    profile.positions,
                )

                toggle_label = (
                    "Remove from comparison" if is_mapped else f"Add {candidate.name} to comparison"
                )
                if st.button(toggle_label, key=f"toggle_{index}_{key}"):
                    if is_mapped:
                        st.session_state.mapped_candidates.discard(key)
                    else:
                        st.session_state.mapped_candidates.add(key)
                    st.rerun()

                if compatibility["overall_pct"] is not None:
                    st.write(
                        f"Overall match: {compatibility['overall_pct']:.0f}% "
                        f"(based on {coverage} of {len(QUESTIONS)} questions with sourced evidence)"
                    )
                else:
                    st.write(
                        f"({coverage} of {len(QUESTIONS)} questions have sourced evidence, but "
                        "none overlap with the questions you answered.)"
                    )

                if is_mapped:
                    covered_categories = set(compatibility["by_category"].keys())
                    missing_categories = [
                        CATEGORY_LABELS[category]
                        for category in CATEGORY_LABELS
                        if category not in covered_categories
                    ]
                    if missing_categories:
                        st.caption(
                            "No sourced positions for: " + ", ".join(missing_categories) +
                            " -- not shown on the radar chart."
                        )

                    has_econ, has_social = profile.covered_axes()
                    if not (has_econ and has_social):
                        missing_axes = [
                            axis
                            for axis, covered in (("economic", has_econ), ("social", has_social))
                            if not covered
                        ]
                        st.caption(
                            "Not plotted on the compass -- no sourced positions cover the "
                            + " or ".join(missing_axes)
                            + " axis" + ("es" if len(missing_axes) > 1 else "") + "."
                        )

                with st.expander(f"Sourced positions for {candidate.name}"):
                    for sourced in profile.sourced_positions:
                        question = QUESTIONS_BY_ID[sourced.question_id]
                        badge = {
                            "explicit": "🟢",
                            "strong_inference": "🟡",
                            "weak_inference": "🔴",
                        }.get(sourced.confidence, "⚪")
                        confidence_label = sourced.confidence.replace("_", " ")
                        st.write(f"{badge} **{question.text}** _(confidence: {confidence_label})_")
                        st.markdown(
                            f"  - [{sourced.source.title or sourced.source.url}]({sourced.source.url})"
                        )

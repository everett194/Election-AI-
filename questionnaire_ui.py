"""
questionnaire_ui.py

Rendering for the 20-question local-issues questionnaire from
local-election-questionnaire.pdf / questionnaire.md. Called inline from
userinterface.py -- not a separate page. Computes the voter's 7-category
radar chart and 2-axis ideological compass from their own answers only; no
candidate data is invented or inferred here.
"""

import math

import altair as alt
import pandas as pd
import streamlit as st

from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
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

CANDIDATE_COLORS = ["#E45756", "#54A24B", "#F58518", "#B279A2", "#72B7B2"]


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
        points = [
            to_point(series_name, category, i, scores.get(category, 0.0))
            for i, category in enumerate(categories)
        ]
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


def render_questionnaire(from_office: str | None = None, from_zip: str | None = None) -> None:
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

    if "questionnaire_answers" in st.session_state:
        st.subheader("Your results")
        radar_scores = compute_radar_scores(st.session_state.questionnaire_importance)
        econ_score, social_score = compute_compass_scores(st.session_state.questionnaire_answers)

        col_radar, col_compass = st.columns(2)
        with col_radar:
            st.markdown("**What matters most to you**")
            st.altair_chart(_radar_chart(radar_scores), width="stretch")
        with col_compass:
            st.markdown("**Your ideological compass**")
            st.altair_chart(_compass_chart(econ_score, social_score), width="stretch")
            st.caption(
                f"Economic axis: {econ_score:.0f} (negative = more public investment/"
                f"regulation, positive = markets/private development/lower taxation). "
                f"Social axis: {social_score:.0f} (negative = more enforcement/authority/"
                f"centralization, positive = civil liberties/rehabilitation/decentralization)."
            )

        st.info(
            "Candidate compatibility scoring needs candidates' own answers to these same "
            "20 questions from a verified source (official records, direct questionnaire "
            "responses, or clearly sourced campaign statements) -- not a guess drawn from "
            "general search results. That candidate-side data isn't populated yet, so no "
            "per-candidate match score is shown here."
        )

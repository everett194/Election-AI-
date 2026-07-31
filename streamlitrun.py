"""
streamlitrun.py

Entry point and Streamlit UI for the whole app. Run with:
    streamlit run streamlitrun.py

Requires two API keys in the environment (never commit them, never paste
them into a chat -- export them yourself in your own terminal):
    export ANTHROPIC_API_KEY=sk-ant-...    # https://console.anthropic.com
    export TAVILY_API_KEY=tvly-...         # https://tavily.com

Architecture, so the full picture is visible from this one file:
- streamlitrun.py (this file): the only Streamlit UI. Collects a US zip
  code, renders the mayoral/county/U.S. House race search results, and
  hosts the inline questionnaire section.
- election_lookup.py: all Anthropic API calls for race/candidate research
  (`web_search` tool), response parsing into typed dataclasses
  (Race, Candidate, Position, CandidateIssueProfile, ...), the resumable
  per-office search generator (`iter_local_elections`), and the
  Tavily-backed evidence pipeline (`research_candidates_via_tavily`) used
  for candidate-vs-questionnaire mapping.
- tavily_search.py: thin wrapper around the Tavily search API -- runs
  several search queries in parallel per candidate (safe here, unlike
  concurrent Anthropic calls; see git history) and returns real evidence
  (title/url/content) for election_lookup to hand to Claude.
- questionnaire_scoring.py: pure scoring logic for the 20-question
  framework -- no I/O, no Streamlit, no Anthropic/Tavily calls. Radar/
  compass/compatibility math and the question bank itself.
- questionnaire_ui.py: renders the 20-question form, the voter's own
  radar/compass charts, and the "Compare with candidates" section
  (triggers election_lookup.research_candidates_via_tavily automatically
  per race, caches results in st.session_state).
- test_election_lookup.py / test_questionnaire_scoring.py /
  test_tavily_search.py: pytest coverage for the non-UI modules above
  (mocked Anthropic/Tavily clients, no real network calls). streamlitrun.py
  and questionnaire_ui.py have no pytest coverage by convention -- verified
  via manual/headless Streamlit smoke tests instead.

A "Take the issues questionnaire" button under each race reveals the
20-question questionnaire inline, further down this same page.
"""

import re
from datetime import datetime, timezone

import streamlit as st

from election_lookup import LookupResult, Race, iter_local_elections
from questionnaire_ui import render_questionnaire

ZIP_PATTERN = re.compile(r"^\d{5}$")

OFFICES = ("mayor", "county", "us_house")

OFFICE_LABELS = {
    "mayor": "Mayoral",
    "county": "County",
    "us_house": "U.S. House",
}


def is_valid_zipcode(zipcode: str) -> bool:
    """Return True if zipcode is a 5-digit US zip code."""
    return bool(ZIP_PATTERN.match(zipcode.strip()))


def render_race(office: str, race: Race | None, zipcode: str) -> None:
    with st.expander(OFFICE_LABELS[office], expanded=True):
        if race is None:
            st.write("No information found for this race type.")
            return

        if race.election_date:
            st.write(f"**{race.jurisdiction_name}** — {race.election_date} ({race.election_type})")
        else:
            st.write(f"**{race.jurisdiction_name}**")

        if race.notes:
            st.info(race.notes)

        if not race.candidates:
            st.write("No candidates found.")
        else:
            for candidate in race.candidates:
                header = candidate.name
                if candidate.party:
                    header += f" ({candidate.party})"
                if candidate.incumbent:
                    header += " — incumbent"
                st.markdown(f"**{header}**")

                if not candidate.positions:
                    st.write("No documented position found.")
                    continue

                for position in candidate.positions:
                    badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(position.confidence, "⚪")
                    st.write(f"{badge} {position.summary} _(confidence: {position.confidence})_")
                    for source in position.sources:
                        st.markdown(f"  - [{source.title or source.url}]({source.url})")

        if st.button("Take the issues questionnaire", key=f"take_quiz_{office}"):
            st.session_state.show_questionnaire = True
            st.session_state.questionnaire_from_office = office
            st.session_state.questionnaire_from_zip = zipcode


def render_result(result: LookupResult) -> None:
    st.caption(f"Retrieved at {result.retrieved_at}")
    by_office = {race.office: race for race in result.races}
    for office in OFFICES:
        render_race(office, by_office.get(office), result.zipcode)


st.title("ElectMatch")
st.write(
    "ElectMatch finds the local elections on your next ballot -- mayor, county, "
    "and U.S. House -- for any U.S. zip code, researches what's publicly known "
    "about each candidate's positions, and lets you take a 20-question issues "
    "questionnaire to see how your own views compare to every candidate running, "
    "side by side on a radar chart and an ideological compass."
)
st.warning(
    "Results are AI-assisted best-effort research from a single automated web "
    "search and are not guaranteed complete or error-free. Verify anything "
    "important via the linked official sources."
)
st.write("Enter your zip code to find your next local elections.")

zipcode = st.text_input("Zip code", placeholder="e.g. 90210", max_chars=5)
search_clicked = st.button("Find my elections")

if "lookup_cache" not in st.session_state:
    st.session_state.lookup_cache = {}
if "lookup_complete" not in st.session_state:
    st.session_state.lookup_complete = set()

rendered_live = False

if zipcode and not is_valid_zipcode(zipcode):
    st.error("Please enter a valid 5-digit zip code (e.g. 90210).")
elif search_clicked and zipcode and zipcode not in st.session_state.lookup_cache:
    st.session_state.lookup_cache[zipcode] = LookupResult(
        zipcode=zipcode, races=[], retrieved_at=datetime.now(timezone.utc).isoformat()
    )

if zipcode in st.session_state.lookup_cache and zipcode not in st.session_state.lookup_complete:
    # Interacting with any widget (e.g. "Take the issues questionnaire") while
    # this search is still running for other offices cancels the in-flight
    # script run before it would normally finish. Progress already appended
    # to `result.races` below survives that cancellation, and this branch
    # resumes the search on the next run instead of losing everything found
    # so far -- otherwise the whole result set (and the click) disappears.
    result = st.session_state.lookup_cache[zipcode]
    # Defensively collapse to one race per office in case a duplicate was
    # ever recorded (e.g. by an interrupted run under an older version of
    # this code) -- otherwise re-rendering below raises a duplicate widget
    # key error for that office's button.
    deduped_by_office: dict[str, Race] = {}
    for race in result.races:
        deduped_by_office[race.office] = race
    result.races = [deduped_by_office[office] for office in OFFICES if office in deduped_by_office]

    st.caption(f"Retrieved at {result.retrieved_at}")
    placeholders = {office: st.empty() for office in OFFICES}
    progress_labels = {"mayor": "mayoral", "county": "county", "us_house": "U.S. House"}

    for race in result.races:
        with placeholders[race.office].container():
            render_race(race.office, race, zipcode)

    already_found = set(deduped_by_office)
    remaining_offices = tuple(office for office in OFFICES if office not in already_found)

    if st.session_state.get("show_questionnaire"):
        # The voter already clicked "Take the issues questionnaire" under one
        # of the races rendered above -- don't make them wait for the
        # remaining offices before it opens. Continuing this search is
        # deferred rather than resumed automatically; whatever was found
        # already stays visible.
        if remaining_offices:
            remaining_labels = ", ".join(progress_labels[office] for office in remaining_offices)
            st.caption(
                f"Skipped finishing the search for: {remaining_labels} -- you "
                "already moved on to the questionnaire below."
            )
    else:
        with st.status(
            "Searching official sources for mayoral, county, and U.S. House races...",
            expanded=True,
        ) as status:
            st.write(
                "Running three scoped searches (mayoral, county, U.S. House), one "
                "at a time. Results appear above as each one finishes; this "
                "commonly takes a minute or two in total."
            )
            try:
                for race in iter_local_elections(zipcode, offices=remaining_offices):
                    if race.office not in already_found:
                        result.races.append(race)
                        already_found.add(race.office)
                    with placeholders[race.office].container():
                        render_race(race.office, race, zipcode)
                    status.write(f"Found the {progress_labels[race.office]} race.")
            except Exception as exc:
                status.update(label="Search failed", state="error")
                st.error(f"Search failed: {exc}")
            else:
                st.session_state.lookup_complete.add(zipcode)
                status.update(label="Search complete", state="complete", expanded=False)
    rendered_live = True

if not rendered_live and zipcode in st.session_state.lookup_cache:
    render_result(st.session_state.lookup_cache[zipcode])

if st.session_state.get("show_questionnaire"):
    from_office = st.session_state.get("questionnaire_from_office")
    from_zip = st.session_state.get("questionnaire_from_zip")
    races = None
    if from_zip and from_zip in st.session_state.lookup_cache:
        races = st.session_state.lookup_cache[from_zip].races
    render_questionnaire(from_office=from_office, from_zip=from_zip, races=races)

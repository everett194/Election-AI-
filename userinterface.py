"""
userinterface.py

Streamlit front end, single page. Collects a US zip code and looks up the
next mayoral, county, and U.S. House elections via election_lookup.py. A
"Take the issues questionnaire" button under each race reveals the 20-question
questionnaire inline, further down this same page.

Run with:
    streamlit run userinterface.py
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


st.title("Election AI - User Interface")
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

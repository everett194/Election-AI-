"""
userinterface.py

Streamlit front end that collects a US zip code and looks up the next
mayoral, county, and U.S. House elections for it via election_lookup.py.

Run with:
    streamlit run userinterface.py
"""

import re

import streamlit as st

from election_lookup import LookupResult, find_local_elections

ZIP_PATTERN = re.compile(r"^\d{5}$")

OFFICE_LABELS = {
    "mayor": "Mayoral",
    "county": "County",
    "us_house": "U.S. House",
}


def is_valid_zipcode(zipcode: str) -> bool:
    """Return True if zipcode is a 5-digit US zip code."""
    return bool(ZIP_PATTERN.match(zipcode.strip()))


def render_result(result: LookupResult) -> None:
    st.caption(f"Retrieved at {result.retrieved_at}")
    by_office = {race.office: race for race in result.races}

    for office in ("mayor", "county", "us_house"):
        race = by_office.get(office)
        with st.expander(OFFICE_LABELS[office], expanded=True):
            if race is None:
                st.write("No information found for this race type.")
                continue

            if race.election_date:
                st.write(f"**{race.jurisdiction_name}** — {race.election_date} ({race.election_type})")
            else:
                st.write(f"**{race.jurisdiction_name}**")

            if race.notes:
                st.info(race.notes)

            if not race.candidates:
                st.write("No candidates found.")
                continue

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


def main() -> None:
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

    if zipcode and not is_valid_zipcode(zipcode):
        st.error("Please enter a valid 5-digit zip code (e.g. 90210).")
        return

    if search_clicked and zipcode:
        if zipcode not in st.session_state.lookup_cache:
            with st.spinner("Searching official sources..."):
                try:
                    st.session_state.lookup_cache[zipcode] = find_local_elections(zipcode)
                except Exception as exc:
                    st.error(f"Search failed: {exc}")
                    return

    if zipcode in st.session_state.lookup_cache:
        render_result(st.session_state.lookup_cache[zipcode])


if __name__ == "__main__":
    main()

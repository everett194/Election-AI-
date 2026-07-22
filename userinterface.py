"""
userinterface.py

Standalone Streamlit front end that collects a US zip code from the user.

This is a stub: it validates and echoes back the zip code but does not yet
look anything up. There is no zip-code-keyed dataset in this repo yet
(app.py's election data is keyed by Australian electorate name, e.g.
"Sydney", "Melbourne" -- not by zip/postcode). Once a real zip-code-to-
district/electorate data source is chosen, wire it in at the marked spot
below.

Run with:
    streamlit run userinterface.py
"""

import re

import streamlit as st

ZIP_PATTERN = re.compile(r"^\d{5}$")


def is_valid_zipcode(zipcode: str) -> bool:
    """Return True if zipcode is a 5-digit US zip code."""
    return bool(ZIP_PATTERN.match(zipcode.strip()))


def main() -> None:
    st.title("Election AI - User Interface")
    st.write("Enter your zip code to get started.")

    zipcode = st.text_input("Zip code", placeholder="e.g. 90210", max_chars=5)

    if zipcode:
        if is_valid_zipcode(zipcode):
            st.success(f"Zip code {zipcode} received.")

            # --- Future data wiring goes here ---
            # Once a zip-code-to-district/electorate dataset exists, look up
            # the corresponding row(s) here and hand off to app.py's
            # prediction/display logic, e.g.:
            #
            #   district = lookup_district(zipcode)
            #   st.write(f"Your district: {district}")
            #
            st.info("Lookup logic is not implemented yet -- this is a stub.")
        else:
            st.error("Please enter a valid 5-digit zip code (e.g. 90210).")


if __name__ == "__main__":
    main()

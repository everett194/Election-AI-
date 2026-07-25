"""
userinterface.py

Entry point / router for the multipage Streamlit app. Pages live under
app_pages/.

Run with:
    streamlit run userinterface.py
"""

import streamlit as st

pages = st.navigation(
    [
        st.Page("app_pages/lookup.py", title="Find my elections", default=True),
        st.Page("app_pages/questionnaire.py", title="Issues questionnaire"),
    ]
)
pages.run()

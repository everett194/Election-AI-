import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import pydeck as pdk

# --- Load subset geojson ---
@st.cache
def load_geo():
    # Replace "aus_divisions_2022_subset.geojson" with your file of subset boundaries
    return gpd.read_file("aus_divisions_2022_subset.geojson")

@st.cache
def load_results():
    # Replace or upload this file to your repo
    from io import StringIO
    csv = """electorate,Labor,Coalition,Greens,Independent
Sydney,50,30,15,5
Melbourne,40,20,30,10
Brisbane,48,32,12,8
Perth,38,40,15,7
Adelaide,42,33,15,10
"""
    return pd.read_csv(StringIO(csv))

def predict_winner(row, swings, parties):
    shares = {p: row[p] for p in parties}
    for p in parties:
        if p in swings:
            shares[p] = max(0, shares[p] + swings[p])
    return max(shares.items(), key=lambda x: x[1])[0]

st.title("Australia 2022 Seat Predictor (Demo Subset)")
parties = ["Labor", "Coalition", "Greens", "Independent"]
st.sidebar.header("Adjust National Swing (%)")
swings = {}
for p in parties:
    swings[p] = st.sidebar.slider(f"{p} swing", -20, 20, 0)

geo = load_geo()
results = load_results()
results["predicted_winner"] = results.apply(lambda r: predict_winner(r, swings, parties), axis=1)
merged = geo.merge(results, left_on="electorate", right_on="electorate", how="left")

party_colors = {
    "Labor":"#E53210",
    "Coalition":"#0055A4",
    "Greens":"#00A550",
    "Independent":"#666666"
}
merged["color"] = merged["predicted_winner"].map(party_colors).fillna("#CCCCCC")

st.subheader("Predicted Seats")
st.bar_chart(results["predicted_winner"].value_counts())

st.subheader("Map")
layer = pdk.Layer(
    "GeoJsonLayer",
    data=merged.__geo_interface__,
    get_fill_color="color",
    pickable=True,
    auto_highlight=True,
    get_line_color=[255,255,255]
)
view = pdk.ViewState(latitude=-33.5, longitude=151, zoom=5)
deck = pdk.Deck(layers=[layer], initial_view_state=view, tooltip={"text":"{electorate}: {predicted_winner}"})
st.pydeck_chart(deck)

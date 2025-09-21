import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

# --- Step 1: Hardcode the polling data into the app ---
csv_data = """date,party,percentage
2017-06-05,Conservative,42
2017-06-05,Labour,35
2017-06-05,Liberal Democrats,10
2017-06-05,UKIP,5
2017-06-05,Green,2
2017-06-06,Conservative,44
2017-06-06,Labour,36
2017-06-06,Liberal Democrats,7
2017-06-06,UKIP,4
2017-06-06,Green,2
2017-06-07,Conservative,46
2017-06-07,Labour,33
2017-06-07,Liberal Democrats,8
2017-06-07,UKIP,5
2017-06-07,Green,3
2017-06-08,Conservative,44
2017-06-08,Labour,36
2017-06-08,Liberal Democrats,7
2017-06-08,UKIP,4
2017-06-08,Green,2
"""

# Load the CSV data into a dataframe
df = pd.read_csv(StringIO(csv_data))

# --- Step 2: Define the prediction function ---
def predict(adjustments=None):
    latest = df.groupby("party")["percentage"].mean()
    if adjustments:
        for party, adj in adjustments.items():
            if party in latest:
                latest[party] = max(0, latest[party] + adj)

    results = {}
    for party, avg in latest.items():
        sims = np.random.normal(loc=avg, scale=2, size=10000)
        results[party] = (sims > 50).mean()
    return latest, results

# --- Step 3: Build the Streamlit app ---
st.title("2017 UK Election AI Modeller")
st.write("Simple demo based on polling averages with user adjustments")

st.header("Adjust Party Support")
con_adj = st.slider("Conservative adjustment (%)", -10, 10, 0)
lab_adj = st.slider("Labour adjustment (%)", -10, 10, 0)
lib_adj = st.slider("Liberal Democrat adjustment (%)", -10, 10, 0)
ukip_adj = st.slider("UKIP adjustment (%)", -10, 10, 0)
green_adj = st.slider("Green adjustment (%)", -10, 10, 0)

adjustments = {
    "Conservative": con_adj,
    "Labour": lab_adj,
    "Liberal Democrats": lib_adj,
    "UKIP": ukip_adj,
    "Green": green_adj
}

latest, results = predict(adjustments=adjustments)

st.subheader("Adjusted Polling Averages")
st.bar_chart(latest)

st.subheader("Estimated Win Probabilities (simplified)")
for party, prob in results.items():
    st.write(f"{party}: {prob*100:.1f}% chance of >50% support")

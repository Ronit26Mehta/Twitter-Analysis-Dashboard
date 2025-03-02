import streamlit as st
import requests
import pandas as pd
from PIL import Image
import io

# Base URL of the FastAPI backend
BASE_URL = "http://localhost:8000"

st.title("Twitter Data Analysis Dashboard")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Select Page", 
                            ["Home", "Tweets", "Report", "Maps", "Visualizations", "Operations"])

if page == "Home":
    st.header("Welcome")
    st.markdown("""
    This dashboard provides insights from the Twitter data analysis.
    Use the sidebar to navigate between pages:
    
    - **Tweets:** View the enriched tweet dataset.
    - **Report:** Read the comprehensive analysis report.
    - **Maps:** Explore user and tweet location maps.
    - **Visualizations:** Browse various analysis visualizations.
    - **Operations:** Review the operations performed during analysis.
    """)
    
elif page == "Tweets":
    st.header("Enriched Tweets Data")
    try:
        response = requests.get(f"{BASE_URL}/tweets")
        response.raise_for_status()
        tweets = response.json()
        if tweets:
            df = pd.DataFrame(tweets)
            st.dataframe(df)
        else:
            st.write("No tweet data found.")
    except Exception as e:
        st.error(f"Error fetching tweets: {e}")

elif page == "Report":
    st.header("Analysis Report")
    try:
        response = requests.get(f"{BASE_URL}/report")
        response.raise_for_status()
        report = response.text
        st.markdown(report)
    except Exception as e:
        st.error(f"Error fetching report: {e}")

elif page == "Maps":
    st.header("Maps")
    map_option = st.selectbox("Select Map", ["User Locations", "Tweet Time Series"])
    if map_option == "User Locations":
        map_url = f"{BASE_URL}/maps/user_locations"
    else:
        map_url = f"{BASE_URL}/maps/tweet_timeseries"
    
    st.markdown("### Map View")
    st.components.v1.iframe(map_url, height=600, scrolling=True)

elif page == "Visualizations":
    st.header("Visualizations")
    viz_options = ["wordcloud", "cooccurrence_heatmap", "sentiment_trend", 
                   "daily_tweet_count_trend", "top_languages", "top_mentions", 
                   "political_distribution", "sentiment_vs_politics"]
    viz_choice = st.selectbox("Select Visualization", viz_options)
    viz_url = f"{BASE_URL}/visualizations/{viz_choice}"
    
    st.markdown("### Visualization")
    try:
        viz_response = requests.get(viz_url)
        viz_response.raise_for_status()
        image = Image.open(io.BytesIO(viz_response.content))
        st.image(image, caption=viz_choice.replace("_", " ").title())
    except Exception as e:
        st.error(f"Error fetching visualization: {e}")

elif page == "Operations":
    st.header("Operations Performed")
    try:
        response = requests.get(f"{BASE_URL}/operations")
        response.raise_for_status()
        operations = response.json()
        for key, value in operations.items():
            st.markdown(f"**{key}.** {value}")
    except Exception as e:
        st.error(f"Error fetching operations: {e}")

# Optional: if you want to run this file as a script with `streamlit run streamlit_app.py`
if __name__ == "__main__":
    st.write("Streamlit UI is running. Use 'streamlit run streamlit_app.py' to view the dashboard.")

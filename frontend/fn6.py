import streamlit as st
import requests
import pandas as pd
from PIL import Image
import io

# Base URL of your FastAPI backend
BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Twitter Data Analysis Dashboard", layout="wide")
st.title("Twitter Data Analysis Dashboard")

# Sidebar Navigation
pages = ["Home", "Tweets", "Report", "Maps", "Visualizations", "Operations", 
         "Query Scrape", "Semantic Visualization", "Term Co-occurrence Analysis"]
page = st.sidebar.selectbox("Select Page", pages)

if page == "Home":
    st.markdown("""
    ## Welcome!
    
    This dashboard provides access to Twitter data analysis, including:
    
    - **Tweets:** View enriched tweet data.
    - **Report:** Read the AI-generated analysis report.
    - **Maps & Visualizations:** Explore interactive maps and images.
    - **Operations:** See the list of operations performed during analysis.
    - **Query Scrape:** Scrape Twitter with a keyword (hard/soft mode).
    - **Semantic Visualization:** Perform topic modeling on tweets filtered by a keyword.
    - **Term Co-occurrence Analysis:** Analyze term co-occurrence networks with AI analysis and interactive visualization.
    
    Use the sidebar to navigate.
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
    st.header("AI-Generated Analysis Report")
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
        for key, op in operations.items():
            st.markdown(f"**{key}.** {op}")
    except Exception as e:
        st.error(f"Error fetching operations: {e}")

elif page == "Query Scrape":
    st.header("Twitter Query Scrape")
    st.markdown("""
    **Query Scrape** allows you to scrape Twitter using a keyword.  
    Choose a scraping mode:
    - **Hard:** Limited scraping (max_scrolls=5)
    - **Soft:** Extensive scraping (max_scrolls=200)
    """)
    query = st.text_input("Enter Keyword", value="example")
    mode = st.radio("Select Mode", options=["hard", "soft"])
    if st.button("Run Query Scrape"):
        with st.spinner("Running query scrape..."):
            payload = {"userquery": query, "mode": mode}
            try:
                response = requests.post(f"{BASE_URL}/query", json=payload)
                response.raise_for_status()
                result = response.json()
                st.success("Query scraping complete!")
                st.subheader("Scraping Results")
                st.json(result.get("results", {}))
                st.markdown(f"**Message:** {result.get('message', '')}")
            except Exception as e:
                st.error(f"Error during query scrape: {e}")

elif page == "Semantic Visualization":
    st.header("Semantic Visualization via Topic Modeling")
    st.markdown("""
    **Semantic Visualization** filters tweets by a given keyword and performs topic modeling using LDA.  
    The output includes the extracted topics along with top words for each topic.
    """)
    keyword = st.text_input("Enter Keyword", value="example")
    n_topics = st.number_input("Number of Topics", min_value=1, value=5, step=1)
    if st.button("Run Semantic Visualization"):
        with st.spinner("Performing topic modeling..."):
            try:
                params = {"keyword": keyword, "n_topics": n_topics}
                response = requests.get(f"{BASE_URL}/semantic_visualization", params=params)
                response.raise_for_status()
                result = response.json()
                st.success("Semantic visualization data generated!")
                st.markdown(f"**Keyword:** {result.get('keyword')}")
                st.markdown(f"**Number of Tweets Analyzed:** {result.get('num_tweets_analyzed')}")
                st.markdown("### Topics Extracted:")
                topics = result.get("topics", {})
                for topic, words in topics.items():
                    st.markdown(f"**{topic}:** {', '.join(words)}")
                st.info(result.get("message"))
                with st.expander("View Raw JSON"):
                    st.json(result)
            except Exception as e:
                st.error(f"Error during semantic visualization: {e}")

elif page == "Term Co-occurrence Analysis":
    st.header("Term Co-occurrence Analysis")
    st.markdown("""
    This section performs term co-occurrence analysis on tweets.  
    Adjust the parameters below and run the analysis.  
    The AI analysis and interactive network visualization will be returned.
    """)
    tweets_file = st.text_input("Tweets File", value="tweets.csv")
    min_term_count = st.number_input("Minimum Term Count", min_value=1, value=2, step=1)
    max_terms = st.number_input("Maximum Terms", min_value=1, value=200, step=1)
    min_edge_weight = st.number_input("Minimum Edge Weight", min_value=1, value=2, step=1)
    if st.button("Run Term Co-occurrence Analysis"):
        with st.spinner("Analyzing term co-occurrence..."):
            try:
                params = {
                    "tweets_file": tweets_file,
                    "min_term_count": min_term_count,
                    "max_terms": max_terms,
                    "min_edge_weight": min_edge_weight
                }
                response = requests.get(f"{BASE_URL}/cooccurrence", params=params)
                response.raise_for_status()
                result = response.json()
                st.success("Term co-occurrence analysis complete!")
                st.subheader("AI-Generated Analysis")
                st.json(result.get("analysis", {}))
                visualization_file = result.get("visualization_file", "term_cooccurrence_graph.html")
                st.subheader("Interactive Network Visualization")
                vis_url = f"{BASE_URL}/visualization?file={visualization_file}"
                st.components.v1.iframe(vis_url, height=800, scrolling=True)
            except Exception as e:
                st.error(f"Error during term co-occurrence analysis: {e}")

st.markdown("""
---
**Instructions:**

1. Use the sidebar to navigate between different functionalities.
2. For Query Scrape and Semantic Visualization, provide a keyword and adjust parameters as needed.
3. For Term Co-occurrence Analysis, adjust the parameters and run the analysis to view the AI summary and interactive network.
""")

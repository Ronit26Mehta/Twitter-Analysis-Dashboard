import streamlit as st
import requests
import json

# Base URL of your FastAPI backend
BASE_URL = "http://localhost:8000"

st.title("Tweet Term Co-occurrence Analysis Dashboard")

# Sidebar for parameter settings
st.sidebar.header("Analysis Parameters")
tweets_file = st.sidebar.text_input("Tweets File", value="tweets.csv")
min_term_count = st.sidebar.number_input("Minimum Term Count", min_value=1, value=2, step=1)
max_terms = st.sidebar.number_input("Maximum Terms", min_value=1, value=200, step=1)
min_edge_weight = st.sidebar.number_input("Minimum Edge Weight", min_value=1, value=2, step=1)

if st.sidebar.button("Run Co-occurrence Analysis"):
    with st.spinner("Running analysis..."):
        params = {
            "tweets_file": tweets_file,
            "min_term_count": min_term_count,
            "max_terms": max_terms,
            "min_edge_weight": min_edge_weight
        }
        try:
            response = requests.get(f"{BASE_URL}/cooccurrence", params=params)
            response.raise_for_status()
            result = response.json()
            
            # Display the analysis JSON summary in a beautified way
            st.success("Analysis complete!")
            analysis = result.get("analysis", {})
            
            st.subheader("AI-Generated Analysis Summary")
            
            # Display key themes if available
            if "key_themes" in analysis:
                st.markdown("### Key Themes")
                for theme in analysis["key_themes"]:
                    st.markdown(f"- **{theme}**")
            
            # Display topic clusters if available
            if "topic_clusters" in analysis:
                st.markdown("### Topic Clusters")
                for cluster, terms in analysis["topic_clusters"].items():
                    terms_str = ", ".join(terms)
                    st.markdown(f"- **{cluster}**: {terms_str}")
            
            # Display interesting insights if available
            if "interesting_insights" in analysis:
                st.markdown("### Interesting Insights")
                for insight in analysis["interesting_insights"]:
                    st.markdown(f"- {insight}")
            
            # Display summary report if available
            if "summary_report" in analysis:
                st.markdown("### Summary Report")
                st.info(analysis["summary_report"])
            
            # Display the raw JSON as an expandable section
            with st.expander("View Full JSON Response"):
                st.json(analysis)
            
            # Display the visualization using an iframe
            visualization_file = result.get("visualization_file", "term_cooccurrence_graph.html")
            st.subheader("Interactive Term Co-occurrence Visualization")
            vis_url = f"{BASE_URL}/visualization?file={visualization_file}"
            st.components.v1.iframe(vis_url, height=800, scrolling=True)
            
        except Exception as e:
            st.error(f"Error during analysis: {e}")

st.markdown("""
---
**Instructions:**

1. Adjust the analysis parameters in the sidebar.
2. Click **Run Co-occurrence Analysis** to trigger the backend analysis.
3. View the beautified AI-generated summary and interact with the visualization embedded below.
""")

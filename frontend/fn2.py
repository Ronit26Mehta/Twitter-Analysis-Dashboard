import streamlit as st
import requests

st.title("Twitter Scraper Frontend")
st.write("Enter your search query and select a mode to test the FastAPI endpoint.")

# User input for query and mode selection
user_query = st.text_input("User Query", "Enter your query here")
mode = st.radio("Select Scraping Mode", options=["hard", "soft"])

if st.button("Submit"):
    # Prepare payload with query and mode
    payload = {"userquery": user_query, "mode": mode}
    
    # Replace URL with your FastAPI endpoint URL if different
    url = "http://localhost:8000/query"
    
    st.write("Sending request...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Display the response as formatted JSON
        data = response.json()
        st.success("Scraping completed!")
        st.json(data)
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
    except Exception as e:
        st.error(f"An error occurred: {e}")

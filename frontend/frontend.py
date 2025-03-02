import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Title and description
st.title("News Reliability Dashboard")
st.write("Enter a news article URL to check if it is from a known unreliable source.")

# Input field for the news URL
news_url = st.text_input("News Article URL", "")

if st.button("Check News"):
    if news_url:
        try:
            # Call the FastAPI endpoint (adjust the URL if necessary)
            response = requests.get("http://localhost:8000/check_news", params={"url": news_url})
            if response.status_code == 200:
                data = response.json()

                # Display the reliability message
                st.markdown("### Result")
                st.info(data["message"])
                st.write(f"**Domain:** {data['domain']}")

                # Display media details if available
                if data.get("media_details"):
                    st.markdown("### Media Details")
                    media_details = data["media_details"]
                    for key, value in media_details.items():
                        st.write(f"**{key}:** {value}")

                # Display WHOIS information if available
                if data.get("whois_info"):
                    st.markdown("### WHOIS Information")
                    st.json(data["whois_info"])

                # Display social media statistics
                if data.get("social_media_stats"):
                    st.markdown("### Social Media Sharing Stats")
                    stats = data["social_media_stats"]
                    # Convert stats to a DataFrame for display and plotting
                    df_stats = pd.DataFrame(list(stats.items()), columns=["Platform", "Shares"])
                    st.table(df_stats)

                    # Create an interactive bar plot using matplotlib
                    fig, ax = plt.subplots()
                    ax.bar(df_stats["Platform"], df_stats["Shares"])
                    ax.set_xlabel("Social Media Platform")
                    ax.set_ylabel("Number of Shares")
                    ax.set_title("Social Media Shares")
                    st.pyplot(fig)
            else:
                st.error("Error: " + response.json().get("detail", "Unknown error"))
        except Exception as e:
            st.error("Failed to connect to the API. " + str(e))
    else:
        st.warning("Please enter a valid URL.")

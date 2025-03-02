import streamlit as st
import requests
import matplotlib.pyplot as plt
import seaborn as sns

# Set page config
st.set_page_config(page_title="WHOIS Lookup Tool", layout="wide")

# Title
st.title("🔍 WHOIS Lookup Tool")
st.markdown("Enter a URL to fetch WHOIS data and visualize domain age.")

# URL input
url = st.text_input("Enter a URL:", placeholder="https://example.com")
check_button = st.button("Fetch WHOIS Data")

if check_button and url:
    with st.spinner("Fetching WHOIS data..."):
        try:
            # Fetch WHOIS data from backend
            response = requests.get("http://localhost:8000/whois", params={"url": url}, timeout=5)
            whois_data = response.json()
            
            if "error" in whois_data:
                st.error(whois_data["error"])
            else:
                # Display WHOIS data
                st.subheader("WHOIS Information")
                # st.write(f"**Domain**: {whois_data['domain']}")
                # st.write(f"**Creation Date**: {whois_data['creation_date']}")
                # st.write(f"**Expiration Date**: {whois_data['expiration_date']}")
                # st.write(f"**Registrar**: {whois_data['registrar']}")
                # st.write(f"**Domain Age**: {whois_data['domain_age_years']} years")
                st.write(whois_data)
                
                # Plot domain age
                if isinstance(whois_data['domain_age_years'], float):
                    fig, ax = plt.subplots(figsize=(6, 3))
                    sns.barplot(x=["Domain Age"], y=[whois_data['domain_age_years']], ax=ax, color='skyblue')
                    ax.set_title("Domain Age in Years")
                    ax.set_ylabel("Years")
                    st.pyplot(fig)
                else:
                    st.warning("Domain age information not available for plotting.")
        except requests.RequestException:
            st.error("Unable to connect to the backend. Ensure the API is running.")
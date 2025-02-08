import requests
import streamlit as st
from requests.structures import CaseInsensitiveDict

# Define API key
API_KEY = "#####"  # Replace with your actual API key

# Define category options
CATEGORIES = {
    "Restaurant": ["catering.restaurant", ["Indian", "Moroccan", "Italian", "Chinese"]],
    "Entertainment": ["entertainment", ["Shopping", "Movies", "Theatre", "Concerts"]]
}

# Streamlit UI
st.title("Find Places in Soho, London")
category = st.selectbox("Select a category", list(CATEGORIES.keys()))
subcategory = st.selectbox("Select a subcategory", CATEGORIES[category][1])

# Construct the API URL
FILTER = "circle:-0.1337,51.5136,1000"  # Soho, London with 1km radius
LIMIT = 20
url = f"https://api.geoapify.com/v2/places?categories={CATEGORIES[category][0]}&filter={FILTER}&limit={LIMIT}&name={subcategory}&apiKey={API_KEY}"

# Set headers
headers = CaseInsensitiveDict()
headers["Accept"] = "application/json"

# Make the request
response = requests.get(url, headers=headers)

# Display results
if response.status_code == 200:
    data = response.json()
    for place in data.get("features", []):
        properties = place.get("properties", {})
        st.write(f"**Name:** {properties.get('name', 'Unknown')}")
        st.write(f"**Address:** {properties.get('formatted', 'No address')}")
        st.write("-" * 40)
else:
    st.error(f"Error: {response.status_code}, {response.text}")

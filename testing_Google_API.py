import streamlit as st
import requests
from collections import defaultdict

# Define API key
GOOGLE_API_KEY = "####"

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'preferences'
if 'location' not in st.session_state:
    st.session_state.location = None
if 'selected_categories' not in st.session_state:
    st.session_state.selected_categories = {}
if 'current_category_index' not in st.session_state:
    st.session_state.current_category_index = 0
if 'liked_places' not in st.session_state:
    st.session_state.liked_places = []
if 'current_places' not in st.session_state:
    st.session_state.current_places = []
if 'current_place_index' not in st.session_state:
    st.session_state.current_place_index = 0

def get_coordinates(location):
    """Get coordinates for a location using Google Geocoding API"""
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={GOOGLE_API_KEY}"
    response = requests.get(geocode_url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    return None

def get_place_photo(photo_reference, max_width=800):
    """Get place photo using Google Places Photo API"""
    if not photo_reference:
        return None
    url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&photo_reference={photo_reference}&key={GOOGLE_API_KEY}"
    return url

def nearby_search(lat, lng, place_type, keyword=None, radius=1500):
    """Perform a nearby search using Google Places API with improved filtering"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{lat},{lng}",
        'radius': radius,
        'type': place_type,
        'key': GOOGLE_API_KEY
    }
    
    # Add keyword for more specific results
    if keyword:
        params['keyword'] = keyword
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        
        # Filter out results that don't match our criteria
        filtered_results = []
        for result in results:
            # Skip hotels and lodging unless specifically requested
            if 'lodging' in result.get('types', []) and place_type != 'lodging':
                continue
            # Ensure the place matches our type requirement
            if place_type in result.get('types', []) or any(t.startswith(place_type.split('_')[0]) for t in result.get('types', [])):
                filtered_results.append(result)
                
        return filtered_results
    return []

def get_place_details(place_id):
    """Get detailed information about a place using Google Places Details API"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,rating,user_ratings_total,opening_hours,formatted_phone_number,price_level,website,photos,types',
        'key': GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('result', {})
    return {}

def show_preferences_page():
    st.title("Where do you want to go?")
    
    # Location input
    location = st.text_input("Enter location", "")
    if location:
        st.session_state.location = location
    
    # Updated categories with more specific types and keywords
    categories = {
        "Food & Dining": {
            "restaurant": {
                "Indian": {"type": "restaurant", "keyword": "indian restaurant"},
                "Moroccan": {"type": "restaurant", "keyword": "moroccan restaurant"},
                "Italian": {"type": "restaurant", "keyword": "italian restaurant"},
                "Chinese": {"type": "restaurant", "keyword": "chinese restaurant"},
                "Japanese": {"type": "restaurant", "keyword": "japanese restaurant"},
                "Thai": {"type": "restaurant", "keyword": "thai restaurant"}
            }
        },
        "Entertainment": {
            "entertainment": {
                "Movies": {"type": "movie_theater", "keyword": "cinema"},
                "Museums": {"type": "museum", "keyword": "museum"},
                "Shopping": {"type": "shopping_mall", "keyword": "shopping center"},
                "Bowling": {"type": "bowling_alley", "keyword": "bowling"},
                "Parks": {"type": "park", "keyword": "park"}
            }
        },
        "Nightlife": {
            "nightlife": {
                "Bars": {"type": "bar", "keyword": "bar pub"},
                "Night Clubs": {"type": "night_club", "keyword": "nightclub"},
                "Live Music": {"type": "bar", "keyword": "live music venue"},
                "Comedy Clubs": {"type": "night_club", "keyword": "comedy club"}
            }
        }
    }
    
    selected_categories = {}
    
    for category, subcategories in categories.items():
        st.subheader(category)
        for main_type, options in subcategories.items():
            cols = st.columns(3)
            for i, (option_name, option_data) in enumerate(options.items()):
                if cols[i % 3].checkbox(option_name, key=f"{category}_{option_name}"):
                    if category not in selected_categories:
                        selected_categories[category] = []
                    selected_categories[category].append({
                        'name': option_name,
                        'type': option_data['type'],
                        'keyword': option_data['keyword']
                    })
    
    if st.button("Let's Go!") and location and any(selected_categories.values()):
        st.session_state.selected_categories = selected_categories
        st.session_state.page = 'swipe'
        st.rerun()

def show_swipe_page():
    # Get places if needed
    if not st.session_state.current_places:
        coords = get_coordinates(st.session_state.location)
        if coords:
            current_category = list(st.session_state.selected_categories.keys())[st.session_state.current_category_index]
            for place_data in st.session_state.selected_categories[current_category]:
                results = nearby_search(
                    coords[0], 
                    coords[1], 
                    place_data['type'],
                    keyword=place_data['keyword']
                )
                for result in results:
                    details = get_place_details(result['place_id'])
                    if details:
                        # Additional filtering to ensure relevance
                        if not any(t in details.get('types', []) for t in ['lodging', 'hotel']):
                            st.session_state.current_places.append(details)
    
    # Show current place
    if st.session_state.current_places and st.session_state.current_place_index < len(st.session_state.current_places):
        place = st.session_state.current_places[st.session_state.current_place_index]
        
        # Create a card-like container
        with st.container():
            # Display photo if available
            if place.get('photos'):
                photo_url = get_place_photo(place['photos'][0]['photo_reference'])
                if photo_url:
                    st.image(photo_url, use_column_width=True)
            
            # Place details
            st.title(place['name'])
            if place.get('rating'):
                st.write(f"⭐ {place['rating']} ({place.get('user_ratings_total', 0)} reviews)")
            if place.get('formatted_address'):
                st.write(f"📍 {place['formatted_address']}")
            if place.get('price_level'):
                st.write(f"💰 {'$' * place['price_level']}")
            
            # Swipe buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👎 Nope", use_container_width=True):
                    st.session_state.current_place_index += 1
                    st.rerun()
            with col2:
                if st.button("❤️ Like", use_container_width=True):
                    st.session_state.liked_places.append(place)
                    st.session_state.current_place_index += 1
                    st.rerun()
            
            # Show progress
            st.progress(len(st.session_state.liked_places) / 10)
            
            # Next category button
            if len(st.session_state.liked_places) >= 10:
                if st.button("Next Category"):
                    st.session_state.current_category_index += 1
                    st.session_state.current_places = []
                    st.session_state.current_place_index = 0
                    st.session_state.liked_places = []
                    if st.session_state.current_category_index >= len(st.session_state.selected_categories):
                        st.session_state.page = 'results'
                    st.rerun()
    else:
        st.write("No more places to show in this category!")
        if st.button("Next Category"):
            st.session_state.current_category_index += 1
            st.session_state.current_places = []
            st.session_state.current_place_index = 0
            st.session_state.liked_places = []
            if st.session_state.current_category_index >= len(st.session_state.selected_categories):
                st.session_state.page = 'results'
            st.rerun()

def show_results_page():
    st.title("Your Matched Places!")
    
    for place in st.session_state.liked_places:
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if place.get('photos'):
                    photo_url = get_place_photo(place['photos'][0]['photo_reference'])
                    if photo_url:
                        st.image(photo_url)
            
            with col2:
                st.subheader(place['name'])
                if place.get('rating'):
                    st.write(f"⭐ {place['rating']} ({place.get('user_ratings_total', 0)} reviews)")
                if place.get('formatted_address'):
                    st.write(f"📍 {place['formatted_address']}")
                if place.get('formatted_phone_number'):
                    st.write(f"📞 {place['formatted_phone_number']}")
                if place.get('website'):
                    st.write(f"🌐 [Website]({place['website']})")
            
            st.write("---")

    if st.button("Start Over"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# Main app logic
if st.session_state.page == 'preferences':
    show_preferences_page()
elif st.session_state.page == 'swipe':
    show_swipe_page()
elif st.session_state.page == 'results':
    show_results_page()

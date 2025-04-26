import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import bcrypt
from datetime import datetime
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# Initialize SQLite database
conn = sqlite3.connect('health_tracker.db', check_same_thread=False)
c = conn.cursor()

# Create necessary tables
c.execute('''CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE NOT NULL,
             password TEXT NOT NULL,
             email TEXT UNIQUE NOT NULL)''')

c.execute('''CREATE TABLE IF NOT EXISTS health_data
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER,
             date DATE,
             weight FLOAT,
             steps INTEGER,
             heart_rate INTEGER,
             sleep_hours FLOAT,
             FOREIGN KEY (user_id) REFERENCES users (id))''')

conn.commit()

# Set page configuration
st.set_page_config(page_title="HealthTracker Pro", layout="wide")

# Custom CSS for dual-tone calming colors
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
    }
    .stButton>button {
        background-color: #64B5F6;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 24px;
    }
    .stTextInput>div>div>input {
        background-color: #FFFFFF;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def register_user(username, password, email):
    try:
        hashed_pw = hash_password(password)
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                 (username, hashed_pw, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    result = c.fetch_one()
    if result and check_password(password, result[1]):
        return result[0]
    return None

def main():
    st.title("🏥 HealthTracker Pro")
    
    if not st.session_state.logged_in:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                user_id = login_user(login_username, login_password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")

        with tab2:
            st.subheader("Register")
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_email = st.text_input("Email", key="reg_email")
            if st.button("Register"):
                if register_user(reg_username, reg_password, reg_email):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Username or email already exists")

    else:
        # Main app interface after login
        menu = st.sidebar.selectbox(
            "Navigation",
            ["Dashboard", "Health Tracking", "Find Hospitals", "Settings"]
        )

        if menu == "Dashboard":
            st.header("Your Health Dashboard")
            col1, col2 = st.columns(2)
            
            with col1:
                # Health metrics visualization
                health_data = pd.DataFrame({
                    'Date': pd.date_range(start='2024-01-01', periods=7),
                    'Steps': np.random.randint(5000, 15000, 7),
                    'Heart Rate': np.random.randint(60, 100, 7)
                })
                
                fig = px.line(health_data, x='Date', y=['Steps', 'Heart Rate'],
                            title='Weekly Health Metrics')
                st.plotly_chart(fig)

            with col2:
                # Sleep tracking
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = 7.5,
                    title = {'text': "Sleep Hours"},
                    gauge = {'axis': {'range': [0, 12]},
                            'bar': {'color': "#64B5F6"}}
                ))
                st.plotly_chart(fig)

        elif menu == "Health Tracking":
            st.header("Track Your Health")
            col1, col2 = st.columns(2)
            
            with col1:
                weight = st.number_input("Weight (kg)", min_value=0.0)
                steps = st.number_input("Steps Today", min_value=0)
                
            with col2:
                heart_rate = st.number_input("Heart Rate (bpm)", min_value=0)
                sleep = st.number_input("Sleep Hours", min_value=0.0, max_value=24.0)
                
            if st.button("Save Data"):
                c.execute("""
                    INSERT INTO health_data (user_id, date, weight, steps, heart_rate, sleep_hours)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (st.session_state.user_id, datetime.now().date(), weight, steps, heart_rate, sleep))
                conn.commit()
                st.success("Health data saved successfully!")

        elif menu == "Find Hospitals":
            st.header("Nearby Hospitals")
            
            # Get user's location
            geolocator = Nominatim(user_agent="health_tracker")
            location = st.text_input("Enter your location")
            
            if location:
                try:
                    loc = geolocator.geocode(location)
                    if loc:
                        # Create map centered on user's location
                        m = folium.Map(location=[loc.latitude, loc.longitude], zoom_start=13)
                        
                        # Add marker for user's location
                        folium.Marker(
                            [loc.latitude, loc.longitude],
                            popup="Your Location",
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(m)
                        
                        # Search for nearby hospitals using OpenStreetMap
                        overpass_url = "http://overpass-api.de/api/interpreter"
                        overpass_query = f"""
                        [out:json];
                        (
                          node["amenity"="hospital"](around:5000,{loc.latitude},{loc.longitude});
                          way["amenity"="hospital"](around:5000,{loc.latitude},{loc.longitude});
                          relation["amenity"="hospital"](around:5000,{loc.latitude},{loc.longitude});
                        );
                        out center;
                        """
                        
                        response = requests.get(overpass_url, params={'data': overpass_query})
                        data = response.json()
                        
                        # Add hospital markers to map
                        for element in data['elements']:
                            if 'lat' in element and 'lon' in element:
                                folium.Marker(
                                    [element['lat'], element['lon']],
                                    popup=element.get('tags', {}).get('name', 'Hospital'),
                                    icon=folium.Icon(color='blue', icon='plus')
                                ).add_to(m)
                        
                        # Display map
                        folium_static(m)
                    else:
                        st.error("Location not found")
                except Exception as e:
                    st.error(f"Error finding hospitals: {str(e)}")

        elif menu == "Settings":
            st.header("Account Settings")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.experimental_rerun()

if __name__ == "__main__":
    main()

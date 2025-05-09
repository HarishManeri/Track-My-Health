import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import requests
import base64

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

def simple_encrypt(password):
    # Very simple encoding - NOT secure for production!
    # Only for demonstration without external libraries
    return base64.b64encode(password.encode()).decode()

def register_user(username, password, email):
    try:
        # Simple password encoding
        encoded_pw = simple_encrypt(password)
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                 (username, encoded_pw, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if result and simple_encrypt(password) == result[1]:
        return result[0]
    return None

def get_hospitals_near_location(lat, lon, radius=5000):
    # Use a simple API call to OpenStreetMap's Nominatim service
    url = f"https://nominatim.openstreetmap.org/search?q=hospital&format=json&lat={lat}&lon={lon}&radius={radius}"
    headers = {'User-Agent': 'HealthTrackerPro/1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        st.error(f"Error fetching hospitals: {str(e)}")
        return []

def geocode_location(location_string):
    # Use Nominatim to geocode a location string
    url = f"https://nominatim.openstreetmap.org/search?q={location_string}&format=json&limit=1"
    headers = {'User-Agent': 'HealthTrackerPro/1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data and len(data) > 0:
            return {
                'lat': float(data[0]['lat']),
                'lon': float(data[0]['lon']),
                'display_name': data[0]['display_name']
            }
        return None
    except Exception as e:
        st.error(f"Error geocoding location: {str(e)}")
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
                # Health metrics visualization using Streamlit's native chart
                health_data = pd.DataFrame({
                    'Date': pd.date_range(start='2024-01-01', periods=7),
                    'Steps': np.random.randint(5000, 15000, 7),
                    'Heart Rate': np.random.randint(60, 100, 7)
                })
                
                # Use Streamlit's native line chart instead of plotly
                st.subheader("Weekly Health Metrics")
                st.line_chart(health_data.set_index('Date'))

            with col2:
                # Sleep tracking using a simple metric display
                st.subheader("Sleep Hours")
                sleep_hours = 7.5  # Example value
                st.metric("Average Sleep", f"{sleep_hours} hours")
                
                # Create a simple progress bar to visualize sleep quality
                st.progress(sleep_hours/12)
                
                if sleep_hours < 6:
                    st.warning("You're not getting enough sleep!")
                elif sleep_hours > 9:
                    st.info("You're getting plenty of rest.")
                else:
                    st.success("Your sleep is in the healthy range.")

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
            location = st.text_input("Enter your location (city, address, etc.)")
            
            if location:
                loc = geocode_location(location)
                if loc:
                    st.write(f"Found location: {loc['display_name']}")
                    
                    # Create a simple map display using st.map
                    map_df = pd.DataFrame({
                        'lat': [loc['lat']],
                        'lon': [loc['lon']]
                    })
                    
                    st.write("Your location:")
                    st.map(map_df)
                    
                    # Find hospitals
                    hospitals = get_hospitals_near_location(loc['lat'], loc['lon'])
                    
                    if hospitals:
                        st.subheader(f"Found {len(hospitals)} hospitals nearby")
                        
                        # Create dataframe for hospital markers
                        hospital_df = pd.DataFrame([{
                            'lat': float(h['lat']),
                            'lon': float(h['lon']),
                            'name': h.get('display_name', 'Hospital')
                        } for h in hospitals])
                        
                        st.write("Nearby hospitals:")
                        st.map(hospital_df)
                        
                        # List hospitals
                        for i, hospital in enumerate(hospitals, 1):
                            st.write(f"{i}. {hospital.get('display_name', 'Hospital')}")
                    else:
                        st.info("No hospitals found in the area")
                else:
                    st.error("Location not found")

        elif menu == "Settings":
            st.header("Account Settings")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.experimental_rerun()

if __name__ == "__main__":
    main()

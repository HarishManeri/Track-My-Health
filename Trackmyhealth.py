# This version now includes pandas and PIL (Pillow) for image and data handling.

import streamlit as st
import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
import uuid
import base64
import pandas as pd
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="Track My Health",
    page_icon="❤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create database directory
os.makedirs("data", exist_ok=True)
DB_FILE = "data/trackmyhealth.db"

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_trackmyhealth_logo():
    logo_svg = '''
    <svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
        <circle cx="30" cy="30" r="30" fill="#28A745"/>
        <path d="M15 30 Q30 10 45 30 Q30 50 15 30 Z" fill="#FF69B4" stroke="#FFFFFF" stroke-width="2"/>
        <path d="M25 20 V40 M35 20 V40" stroke="#FFFFFF" stroke-width="2"/>
        <path d="M20 30 H40" stroke="#FFFFFF" stroke-width="2" stroke-dasharray="5"/>
    </svg>
    '''
    return "data:image/svg+xml;base64," + base64.b64encode(logo_svg.encode()).decode()

# Database setup
def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        name TEXT,
        email TEXT
    )''')
    conn.commit()
    conn.close()

# Authentication
def authenticate(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, role, name FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and user[1] == hash_password(password):
            return {'user_id': user[0], 'role': user[2], 'name': user[3]}
    except:
        return None
    finally:
        conn.close()

# UI Pages
def login_page():
    st.markdown(f'<h1 style="color:#28A745">Track My Health</h1><p>Your health companion.</p>', unsafe_allow_html=True)
    role = st.selectbox("Login as", ["Patient", "Hospital", "Admin"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate(username, password)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid credentials")

def dashboard():
    st.markdown(f"<h2 style='color:#28A745'>Welcome {st.session_state.user['name']}</h2>", unsafe_allow_html=True)
    st.info("This version supports pandas for data handling and Pillow for image support.")
    # Example pandas DataFrame
    df = pd.DataFrame({
        'Vital': ['Heart Rate', 'Blood Pressure'],
        'Value': ['72 bpm', '120/80 mmHg']
    })
    st.dataframe(df)

    # Example image with PIL
    img = Image.new('RGB', (100, 50), color = 'green')
    st.image(img, caption='Sample PIL Image')

def main():
    initialize_database()
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()

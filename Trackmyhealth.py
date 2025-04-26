# Full-featured Track My Health app with login, registration, and role-based dashboards.

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
    cursor.execute('''CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        first_name TEXT,
        last_name TEXT,
        date_of_birth TEXT,
        gender TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS hospitals (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        name TEXT,
        address TEXT,
        phone TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        hospital_id TEXT,
        appointment_date TEXT,
        reason TEXT,
        status TEXT
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

# Registration logic
def register_user():
    role = st.selectbox("Register as", ["Patient", "Hospital"])
    if role == "Patient":
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        dob = st.date_input("Date of Birth")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        email = st.text_input("Email")
        if st.button("Register Patient"):
            if first_name and last_name and email:
                username = f"{first_name.lower()}.{last_name.lower()}"
                password = "patient123"
                user_id = f"USR_PAT_{uuid.uuid4().hex[:6]}"
                patient_id = f"PAT_{uuid.uuid4().hex[:6]}"
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                               (user_id, username, hash_password(password), "patient", f"{first_name} {last_name}", email))
                cursor.execute("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?)",
                               (patient_id, user_id, first_name, last_name, dob.isoformat(), gender))
                conn.commit()
                conn.close()
                st.success(f"Registered! Username: {username}, Password: {password}")
            else:
                st.warning("Please fill all required fields.")
    elif role == "Hospital":
        name = st.text_input("Hospital Name")
        address = st.text_area("Address")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email")
        if st.button("Register Hospital"):
            if name and address and phone and email:
                username = name.lower().replace(" ", "")
                password = "hospital123"
                user_id = f"USR_HOS_{uuid.uuid4().hex[:6]}"
                hospital_id = f"HOS_{uuid.uuid4().hex[:6]}"
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                               (user_id, username, hash_password(password), "hospital", name, email))
                cursor.execute("INSERT INTO hospitals VALUES (?, ?, ?, ?, ?)",
                               (hospital_id, user_id, name, address, phone))
                conn.commit()
                conn.close()
                st.success(f"Registered! Username: {username}, Password: {password}")
            else:
                st.warning("Please fill all required fields.")

# UI Pages
def login_page():
    st.markdown(f'<h1 style="color:#28A745">Track My Health</h1><p>Your health companion.</p>', unsafe_allow_html=True)
    choice = st.radio("Select Option", ["Login", "Register"])
    if choice == "Login":
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
    else:
        register_user()

def patient_dashboard():
    st.subheader("Patient Dashboard")
    st.write("Book appointments, view history, and monitor health trends.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM patients WHERE user_id = ?", (st.session_state.user['user_id'],))
    patient_id = cursor.fetchone()[0]
    cursor.execute("SELECT id, name FROM hospitals")
    hospitals = cursor.fetchall()
    hospital_dict = {name: id_ for id_, name in hospitals}

    hospital_choice = st.selectbox("Choose Hospital", list(hospital_dict.keys()))
    appointment_date = st.date_input("Appointment Date")
    appointment_time = st.time_input("Appointment Time")
    reason = st.text_input("Reason for Visit")
    if st.button("Book Appointment"):
        appt_datetime = datetime.combine(appointment_date, appointment_time).isoformat()
        appt_id = f"APT_{uuid.uuid4().hex[:6]}"
        cursor.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)",
                       (appt_id, patient_id, hospital_dict[hospital_choice], appt_datetime, reason, "Scheduled"))
        conn.commit()
        st.success("Appointment booked successfully.")

    cursor.execute("SELECT a.id, h.name, a.appointment_date, a.reason, a.status FROM appointments a JOIN hospitals h ON a.hospital_id = h.id WHERE a.patient_id = ?", (patient_id,))
    appointments = cursor.fetchall()
    if appointments:
        df = pd.DataFrame(appointments, columns=["Appointment ID", "Hospital", "Date & Time", "Reason", "Status"])
        st.dataframe(df)

        if st.button("Export My Appointments to CSV"):
            df.to_csv("my_appointments.csv", index=False)
            st.download_button("Download My Appointments", data=open("my_appointments.csv", "rb"), file_name="my_appointments.csv")

    conn.close()

def hospital_dashboard():
    st.subheader("Hospital Dashboard")
    st.write("Manage appointments and view patient records.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM hospitals WHERE user_id = ?", (st.session_state.user['user_id'],))
    hospital_id = cursor.fetchone()[0]

    cursor.execute("SELECT a.id, u.name, a.appointment_date, a.reason, a.status FROM appointments a JOIN patients p ON a.patient_id = p.id JOIN users u ON p.user_id = u.id WHERE a.hospital_id = ?", (hospital_id,))
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["Appointment ID", "Patient Name", "Date & Time", "Reason", "Status"])
        st.dataframe(df)

        selected = st.selectbox("Select Appointment to Update Status", df["Appointment ID"])
        new_status = st.selectbox("New Status", ["Scheduled", "Completed", "Cancelled"])
        if st.button("Update Status"):
            cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, selected))
            conn.commit()
            st.success("Appointment status updated.")
    else:
        st.info("No appointments found.")

    if st.button("Export Appointments to CSV"):
        df.to_csv("appointments.csv", index=False)
        st.download_button("Download CSV", data=open("appointments.csv", "rb"), file_name="appointments.csv")

    conn.close()

def admin_dashboard():
    st.subheader("Admin Dashboard")
    st.write("Review hospital registrations and system stats.")

def dashboard():
    role = st.session_state.user['role']
    st.markdown(f"<h2 style='color:#28A745'>Welcome {st.session_state.user['name']}</h2>", unsafe_allow_html=True)
    if role == "patient":
        patient_dashboard()
    elif role == "hospital":
        hospital_dashboard()
    elif role == "admin":
        admin_dashboard()

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

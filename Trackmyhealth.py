import streamlit as st
import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
import uuid
import base64
import pandas as pd
import webbrowser
import json
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS health_records (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        record_date TEXT,
        record_type TEXT,
        value TEXT,
        notes TEXT
    )''')
    
    # Add admin user if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE role = 'admin'")
    if not cursor.fetchone():
        admin_id = f"USR_ADM_{uuid.uuid4().hex[:6]}"
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                      (admin_id, "admin", hash_password("admin123"), "admin", "System Admin", "admin@trackmyhealth.com"))
    
    # Add some sample hospitals if none exist
    cursor.execute("SELECT * FROM hospitals LIMIT 1")
    if not cursor.fetchone():
        sample_hospitals = [
            ("City General Hospital", "123 Main St, City Center", "555-123-4567"),
            ("Memorial Medical Center", "456 Oak Ave, Westside", "555-234-5678"),
            ("Community Health Network", "789 Pine Rd, Eastville", "555-345-6789")
        ]
        
        for hospital in sample_hospitals:
            user_id = f"USR_HOS_{uuid.uuid4().hex[:6]}"
            hospital_id = f"HOS_{uuid.uuid4().hex[:6]}"
            hospital_name = hospital[0]
            username = hospital_name.lower().replace(" ", "")
            
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, username, hash_password("hospital123"), "hospital", hospital_name, f"info@{username}.com"))
            cursor.execute("INSERT INTO hospitals VALUES (?, ?, ?, ?, ?)",
                         (hospital_id, user_id, hospital_name, hospital[1], hospital[2]))
    
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
        return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None
    finally:
        conn.close()

# Registration logic
def register_user():
    role = st.selectbox("Register as", ["Patient", "Hospital"])
    if role == "Patient":
        with st.form("patient_registration"):
            st.subheader("Patient Registration")
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            dob = st.date_input("Date of Birth")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            email = st.text_input("Email")
            custom_username = st.text_input("Username (optional)")
            custom_password = st.text_input("Password (optional)", type="password")
            
            submit_button = st.form_submit_button("Register Patient")
            if submit_button:
                if first_name and last_name and email:
                    username = custom_username if custom_username else f"{first_name.lower()}.{last_name.lower()}"
                    password = custom_password if custom_password else "patient123"
                    
                    # Check if username already exists
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                    if cursor.fetchone():
                        st.error(f"Username '{username}' already exists. Please choose another username.")
                        conn.close()
                        return
                    
                    user_id = f"USR_PAT_{uuid.uuid4().hex[:6]}"
                    patient_id = f"PAT_{uuid.uuid4().hex[:6]}"
                    
                    try:
                        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                                    (user_id, username, hash_password(password), "patient", f"{first_name} {last_name}", email))
                        cursor.execute("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?)",
                                    (patient_id, user_id, first_name, last_name, dob.isoformat(), gender))
                        conn.commit()
                        st.success(f"Registered successfully! Username: {username}, Password: {password}")
                    except Exception as e:
                        st.error(f"Registration error: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("Please fill all required fields.")
    
    elif role == "Hospital":
        with st.form("hospital_registration"):
            st.subheader("Hospital Registration")
            name = st.text_input("Hospital Name")
            address = st.text_area("Address")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email")
            custom_username = st.text_input("Username (optional)")
            custom_password = st.text_input("Password (optional)", type="password")
            
            submit_button = st.form_submit_button("Register Hospital")
            if submit_button:
                if name and address and phone and email:
                    username = custom_username if custom_username else name.lower().replace(" ", "")
                    password = custom_password if custom_password else "hospital123"
                    
                    # Check if username already exists
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                    if cursor.fetchone():
                        st.error(f"Username '{username}' already exists. Please choose another username.")
                        conn.close()
                        return
                    
                    user_id = f"USR_HOS_{uuid.uuid4().hex[:6]}"
                    hospital_id = f"HOS_{uuid.uuid4().hex[:6]}"
                    
                    try:
                        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                                    (user_id, username, hash_password(password), "hospital", name, email))
                        cursor.execute("INSERT INTO hospitals VALUES (?, ?, ?, ?, ?)",
                                    (hospital_id, user_id, name, address, phone))
                        conn.commit()
                        st.success(f"Registered successfully! Username: {username}, Password: {password}")
                    except Exception as e:
                        st.error(f"Registration error: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("Please fill all required fields.")

# UI Pages
def login_page():
    col1, col2 = st.columns([1, 3])
    
    with col1:
        logo_url = get_trackmyhealth_logo()
        st.markdown(f'<img src="{logo_url}" style="width:150px;">', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<h1 style="color:#28A745">Track My Health</h1><p>Your comprehensive health companion.</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("Login")
            role = st.selectbox("Login as", ["Patient", "Hospital", "Admin"])
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if username and password:
                    user = authenticate(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please enter both username and password")
    
    with tab2:
        register_user()

def search_hospital():
    st.subheader("Find Hospitals")
    search_term = st.text_input("Search for hospitals by name or location", "hospitals near me")
    
    if st.button("Search on Google"):
        google_search_url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
        st.markdown(f"<a href='{google_search_url}' target='_blank'>Click here to search for hospitals on Google</a>", unsafe_allow_html=True)
        
        # This will open in the current tab which is not ideal for Streamlit
        # webbrowser.open_new_tab(google_search_url)
        
        st.info("A link to search for hospitals has been provided above. Click it to open Google search in a new tab.")
        
    # Display local hospitals from the database
    st.subheader("Hospitals in our system")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT h.id, h.name, h.address, h.phone FROM hospitals h JOIN users u ON h.user_id = u.id")
    hospitals = cursor.fetchall()
    
    if hospitals:
        df = pd.DataFrame(hospitals, columns=["Hospital ID", "Name", "Address", "Phone"])
        st.dataframe(df)
        
        # Store hospitals in session state for selection
        hospital_dict = {row[1]: row[0] for row in hospitals}
        st.session_state.hospital_dict = hospital_dict
        st.session_state.hospital_selected = True
    else:
        st.info("No hospitals found in our system. Please use the search function to find hospitals.")
    
    conn.close()

def record_health_data():
    st.subheader("Record Health Data")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM patients WHERE user_id = ?", (st.session_state.user['user_id'],))
    patient_data = cursor.fetchone()
    
    if patient_data:
        patient_id = patient_data[0]
        
        with st.form("health_record_form"):
            record_type = st.selectbox("Record Type", [
                "Blood Pressure", "Heart Rate", "Blood Sugar", 
                "Weight", "Temperature", "Exercise", "Medication"
            ])
            
            if record_type == "Blood Pressure":
                systolic = st.number_input("Systolic (mm Hg)", min_value=70, max_value=220)
                diastolic = st.number_input("Diastolic (mm Hg)", min_value=40, max_value=180)
                value = f"{systolic}/{diastolic}"
            elif record_type == "Heart Rate":
                value = st.number_input("Beats Per Minute", min_value=30, max_value=220)
            elif record_type == "Blood Sugar":
                value = st.number_input("Blood Sugar (mg/dL)", min_value=20, max_value=600)
            elif record_type == "Weight":
                value = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, step=0.1)
            elif record_type == "Temperature":
                value = st.number_input("Temperature (°C)", min_value=35.0, max_value=42.0, step=0.1)
            elif record_type == "Exercise":
                activity = st.text_input("Activity Type")
                duration = st.number_input("Duration (minutes)", min_value=1, max_value=600)
                value = f"{activity}: {duration} minutes"
            elif record_type == "Medication":
                med_name = st.text_input("Medication Name")
                med_dose = st.text_input("Dosage")
                value = f"{med_name}: {med_dose}"
            
            notes = st.text_area("Notes", height=100)
            record_date = st.date_input("Date")
            record_time = st.time_input("Time")
            
            submit_button = st.form_submit_button("Save Record")
            
            if submit_button:
                record_id = f"REC_{uuid.uuid4().hex[:6]}"
                record_datetime = datetime.combine(record_date, record_time).isoformat()
                
                try:
                    cursor.execute("INSERT INTO health_records VALUES (?, ?, ?, ?, ?, ?)",
                                  (record_id, patient_id, record_datetime, record_type, str(value), notes))
                    conn.commit()
                    st.success("Health record saved successfully!")
                except Exception as e:
                    st.error(f"Error saving record: {e}")
    else:
        st.warning("Patient profile not found. Please contact support.")
    
    conn.close()

def view_health_history():
    st.subheader("Health History")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM patients WHERE user_id = ?", (st.session_state.user['user_id'],))
    patient_data = cursor.fetchone()
    
    if patient_data:
        patient_id = patient_data[0]
        
        # Get all record types for filtering
        cursor.execute("SELECT DISTINCT record_type FROM health_records WHERE patient_id = ?", (patient_id,))
        record_types = [r[0] for r in cursor.fetchall()]
        
        if record_types:
            selected_type = st.selectbox("Filter by Type", ["All Types"] + record_types)
            
            if selected_type == "All Types":
                cursor.execute("""
                    SELECT record_date, record_type, value, notes 
                    FROM health_records 
                    WHERE patient_id = ? 
                    ORDER BY record_date DESC
                """, (patient_id,))
            else:
                cursor.execute("""
                    SELECT record_date, record_type, value, notes 
                    FROM health_records 
                    WHERE patient_id = ? AND record_type = ? 
                    ORDER BY record_date DESC
                """, (patient_id, selected_type))
            
            records = cursor.fetchall()
            
            if records:
                df = pd.DataFrame(records, columns=["Date & Time", "Type", "Value", "Notes"])
                st.dataframe(df)
                
                if st.button("Export Health Records to CSV"):
                    df.to_csv("my_health_records.csv", index=False)
                    st.download_button(
                        "Download Health Records", 
                        data=open("my_health_records.csv", "rb"), 
                        file_name="my_health_records.csv"
                    )
                
                # Display chart for numeric data
                if selected_type in ["Heart Rate", "Blood Sugar", "Weight", "Temperature"]:
                    # Convert to numeric values
                    numeric_values = []
                    dates = []
                    
                    for record in records:
                        try:
                            date = datetime.fromisoformat(record[0]).strftime('%Y-%m-%d %H:%M')
                            value = float(record[2])
                            numeric_values.append(value)
                            dates.append(date)
                        except (ValueError, TypeError):
                            pass
                    
                    if numeric_values:
                        chart_data = pd.DataFrame({
                            'Date': dates,
                            'Value': numeric_values
                        })
                        
                        st.line_chart(chart_data.set_index('Date'))
            else:
                st.info(f"No records found for {selected_type}")
        else:
            st.info("No health records found. Start tracking your health data now!")
    else:
        st.warning("Patient profile not found. Please contact support.")
    
    conn.close()

def patient_dashboard():
    st.markdown(f'<h2 style="color:#28A745">Patient Dashboard</h2>', unsafe_allow_html=True)
    
    # Create tabs for different patient functions
    tabs = st.tabs(["Book Appointments", "My Appointments", "Health Records", "Track Health", "Find Hospitals"])
    
    with tabs[0]:  # Book Appointments
        st.subheader("Book New Appointment")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patients WHERE user_id = ?", (st.session_state.user['user_id'],))
        patient_data = cursor.fetchone()
        
        if patient_data:
            patient_id = patient_data[0]
            
            if "hospital_selected" not in st.session_state:
                st.session_state.hospital_selected = False
            
            if not st.session_state.hospital_selected:
                if st.button("Find Hospitals"):
                    st.session_state.hospital_selected = True
                    st.rerun()
            else:
                cursor.execute("SELECT id, name FROM hospitals")
                hospitals = cursor.fetchall()
                hospital_dict = {name: id_ for id_, name in hospitals}
                
                with st.form("book_appointment"):
                    hospital_choice = st.selectbox("Choose Hospital", list(hospital_dict.keys()))
                    appointment_date = st.date_input("Appointment Date", min_value=datetime.now().date())
                    appointment_time = st.time_input("Appointment Time")
                    reason = st.text_area("Reason for Visit")
                    doctor_preference = st.text_input("Preferred Doctor (optional)")
                    
                    submit_button = st.form_submit_button("Book Appointment")
                    
                    if submit_button:
                        if reason:
                            appt_datetime = datetime.combine(appointment_date, appointment_time).isoformat()
                            appt_id = f"APT_{uuid.uuid4().hex[:6]}"
                            
                            try:
                                cursor.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)",
                                              (appt_id, patient_id, hospital_dict[hospital_choice], 
                                               appt_datetime, f"{reason} (Doctor: {doctor_preference})", "Scheduled"))
                                conn.commit()
                                st.success("Appointment booked successfully!")
                            except Exception as e:
                                st.error(f"Error booking appointment: {e}")
                        else:
                            st.warning("Please provide a reason for your visit.")
        else:
            st.warning("Patient profile not found. Please contact support.")
        
        conn.close()
    
    with tabs[1]:  # My Appointments
        st.subheader("My Appointments")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patients WHERE user_id = ?", (st.session_state.user['user_id'],))
        patient_data = cursor.fetchone()
        
        if patient_data:
            patient_id = patient_data[0]
            
            cursor.execute("""
                SELECT a.id, h.name, a.appointment_date, a.reason, a.status 
                FROM appointments a 
                JOIN hospitals h ON a.hospital_id = h.id 
                WHERE a.patient_id = ? 
                ORDER BY a.appointment_date DESC
            """, (patient_id,))
            
            appointments = cursor.fetchall()
            
            if appointments:
                df = pd.DataFrame(appointments, columns=["Appointment ID", "Hospital", "Date & Time", "Reason", "Status"])
                st.dataframe(df)
                
                if st.button("Export My Appointments to CSV"):
                    df.to_csv("my_appointments.csv", index=False)
                    st.download_button(
                        "Download My Appointments", 
                        data=open("my_appointments.csv", "rb"), 
                        file_name="my_appointments.csv"
                    )
                
                selected_apt = st.selectbox("Select Appointment", df["Appointment ID"], key="cancel_apt")
                if st.button("Cancel Appointment"):
                    try:
                        cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (selected_apt,))
                        conn.commit()
                        st.success("Appointment cancelled successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error cancelling appointment: {e}")
            else:
                st.info("No appointments found. Book your first appointment now!")
        else:
            st.warning("Patient profile not found. Please contact support.")
        
        conn.close()
    
    with tabs[2]:  # Health Records
        view_health_history()
    
    with tabs[3]:  # Track Health
        record_health_data()
    
    with tabs[4]:  # Find Hospitals
        search_hospital()

def hospital_dashboard():
    st.markdown(f'<h2 style="color:#28A745">Hospital Dashboard</h2>', unsafe_allow_html=True)
    
    # Create tabs for different hospital functions
    tabs = st.tabs(["Upcoming Appointments", "Appointment History", "Patient Records", "Hospital Profile"])
    
    with tabs[0]:  # Upcoming Appointments
        st.subheader("Upcoming Appointments")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM hospitals WHERE user_id = ?", (st.session_state.user['user_id'],))
        hospital_data = cursor.fetchone()
        
        if hospital_data:
            hospital_id = hospital_data[0]
            
            cursor.execute("""
                SELECT a.id, u.name, a.appointment_date, a.reason, a.status 
                FROM appointments a 
                JOIN patients p ON a.patient_id = p.id 
                JOIN users u ON p.user_id = u.id 
                WHERE a.hospital_id = ? AND a.status = 'Scheduled' AND a.appointment_date >= ? 
                ORDER BY a.appointment_date ASC
            """, (hospital_id, datetime.now().isoformat()))
            
            upcoming = cursor.fetchall()
            
            if upcoming:
                df = pd.DataFrame(upcoming, columns=["Appointment ID", "Patient Name", "Date & Time", "Reason", "Status"])
                st.dataframe(df)
                
                selected_apt = st.selectbox("Select Appointment to Update", df["Appointment ID"])
                new_status = st.selectbox("Update Status", ["Scheduled", "Completed", "Cancelled", "No Show"])
                
                if st.button("Update Status"):
                    try:
                        cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, selected_apt))
                        conn.commit()
                        st.success("Appointment status updated successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating appointment: {e}")
            else:
                st.info("No upcoming appointments found.")
        else:
            st.warning("Hospital profile not found. Please contact support.")
        
        conn.close()
    
    with tabs[1]:  # Appointment History
        st.subheader("Appointment History")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM hospitals WHERE user_id = ?", (st.session_state.user['user_id'],))
        hospital_data = cursor.fetchone()
        
        if hospital_data:
            hospital_id = hospital_data[0]
            
            # Get all appointment statuses for filtering
            cursor.execute("SELECT DISTINCT status FROM appointments WHERE hospital_id = ?", (hospital_id,))
            statuses = [s[0] for s in cursor.fetchall()]
            
            if statuses:
                selected_status = st.selectbox("Filter by Status", ["All"] + statuses)
                
                if selected_status == "All":
                    cursor.execute("""
                        SELECT a.id, u.name, a.appointment_date, a.reason, a.status 
                        FROM appointments a 
                        JOIN patients p ON a.patient_id = p.id 
                        JOIN users u ON p.user_id = u.id 
                        WHERE a.hospital_id = ? 
                        ORDER BY a.appointment_date DESC
                    """, (hospital_id,))
                else:
                    cursor.execute("""
                        SELECT a.id, u.name, a.appointment_date, a.reason, a.status 
                        FROM appointments a 
                        JOIN patients p ON a.patient_id = p.id 
                        JOIN users u ON p.user_id = u.id 
                        WHERE a.hospital_id = ? AND a.status = ? 
                        ORDER BY a.appointment_date DESC
                    """, (hospital_id, selected_status))
                
                appointments = cursor.fetchall()
                
                if appointments:
                    df = pd.DataFrame(appointments, columns=["Appointment ID", "Patient Name", "Date & Time", "Reason", "Status"])
                    st.dataframe(df)
                    
                    if st.button("Export Appointments to CSV"):
                        df.to_csv("hospital_appointments.csv", index=False)
                        st.download_button(
                            "Download CSV", 
                            data=open("hospital_appointments.csv", "rb"), 
                            file_name="hospital_appointments.csv"
                        )
                else:
                    st.info(f"No appointments with status '{selected_status}' found.")
            else:
                st.info("No appointment history found.")
        else:
            st.warning("Hospital profile not found. Please contact support.")
        
        conn.close()
    
    with tabs[2]:  # Patient Records
        st.subheader("Patient Records")
        st.info("This feature will allow you to view patient records for those who have appointments with your hospital.")
        
        # Demo functionality - in a real app, this would be connected to patient records
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM hospitals WHERE user_id = ?", (st.session_state.user['user_id'],))
        hospital_data = cursor.fetchone()
        
        if hospital_data:
            hospital_id = hospital_data[0]
            
            cursor.execute("""
                SELECT DISTINCT p.id, u.name 
                FROM appointments a 
                JOIN patients p ON a.patient_id = p.id 
                JOIN users u ON p.user_id = u.id 
                WHERE a.hospital_id = ?
            """, (hospital_id,))
            
            patients = cursor.fetchall()
            
            if patients:
                patient_dict = {name: id_ for id_, name in patients}
                selected_patient = st.selectbox("Select Patient", list(patient_dict.keys()))
                
                st.write("Patient records would be displayed here (demo functionality)")
            else:
                st.info("No patients have appointments with your hospital yet.")
        else:
            st.warning("Hospital profile not found. Please contact support.")
        
        conn.close()
    
    with tabs[3]:  # Hospital Profile
        st.subheader("Hospital Profile")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT h.name, h.address, h.phone, u.email 
            FROM hospitals h 
            JOIN users u ON h.user_id = u.id 
            WHERE h.user_id = ?
        """, (st.session_state.user['user_id'],))
        
        profile = cursor.fetchone()
        
        if profile:
            st.write(f"**Hospital Name:** {profile[0]}")
            st.write(f"**Address:** {profile[1]}")
            st.write(f"**Phone:** {profile[2]}")
            st.write(f"**Email:** {profile[3]}")
            
            st.subheader("Update Hospital Information")
            with st.form("update_hospital"):
                new_address = st.text_area("Address", value=profile[1])
                new_phone = st.text_input("Phone", value=profile[2])
                new_email = st.text_input("Email", value=profile[3])
                
                submit_button = st.form_submit_button("Update Profile")
                
                if submit_button:
                    try:
                        cursor.execute("UPDATE hospitals SET address = ?, phone = ? WHERE user_id = ?", 
                                      (new_address, new_phone, st.session_state.user['user_id']))
                        cursor.execute("UPDATE users SET email = ? WHERE id = ?", 
                                      (new_email, st.session_state.user['user_id']))
                        conn.commit()
                        st.success("Hospital profile updated successfully!")
                    except Exception as e:
                        st.error(f"Error updating profile: {e}")
        else:
            st.warning("Hospital profile not found. Please contact support.")
        
        conn.close()

def admin_dashboard():
    st.markdown(f'<h2 style="color:#28A745">Admin Dashboard</h2>', unsafe_allow_html=True)
    
    # Create tabs for different admin functions
    tabs = st.tabs(["System Statistics", "User Management", "Hospital Approvals", "System Logs"])
    
    with tabs[0]:  # System Statistics
        st.subheader("System Statistics")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get counts for dashboard
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='patient'")
        patient_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='hospital'")
        hospital_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appointment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status='Completed'")
        completed_count = cursor.fetchone()[0]
        
        # Display statistics in a nice format
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Registered Patients", patient_count)
        with col2:
            st.metric("Registered Hospitals", hospital_count)
        with col3:
            st.metric("Total Appointments", appointment_count)
        with col4:
            st.metric("Completed Appointments", completed_count)
        
        # Chart for appointments by status
        cursor.execute("SELECT status, COUNT(*) FROM appointments GROUP BY status")
        status_data = cursor.fetchall()
        if status_data:
            status_df = pd.DataFrame(status_data, columns=["Status", "Count"])
            st.subheader("Appointments by Status")
            st.bar_chart(status_df.set_index("Status"))
        
        # Recent activity
        st.subheader("Recent Activity")
        cursor.execute("""
            SELECT u.name, a.appointment_date, h.name, a.status 
            FROM appointments a 
            JOIN patients p ON a.patient_id = p.id 
            JOIN users u ON p.user_id = u.id 
            JOIN hospitals h ON a.hospital_id = h.id 
            ORDER BY a.appointment_date DESC 
            LIMIT 10
        """)
        recent_activity = cursor.fetchall()
        if recent_activity:
            activity_df = pd.DataFrame(recent_activity, columns=["Patient", "Date", "Hospital", "Status"])
            st.dataframe(activity_df)
        else:
            st.info("No recent activity found.")
        
        conn.close()
    
    with tabs[1]:  # User Management
        st.subheader("User Management")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # User role filter
        role_filter = st.selectbox("Filter by Role", ["All", "Patient", "Hospital", "Admin"])
        
        if role_filter == "All":
            cursor.execute("""
                SELECT id, username, role, name, email 
                FROM users 
                ORDER BY role, name
            """)
        else:
            cursor.execute("""
                SELECT id, username, role, name, email 
                FROM users 
                WHERE LOWER(role) = LOWER(?) 
                ORDER BY name
            """, (role_filter,))
        
        users = cursor.fetchall()
        
        if users:
            user_df = pd.DataFrame(users, columns=["User ID", "Username", "Role", "Name", "Email"])
            st.dataframe(user_df)
            
            # User actions
            selected_user = st.selectbox("Select User for Action", user_df["Username"])
            action = st.selectbox("Action", ["Reset Password", "Disable Account", "Delete Account"])
            
            if st.button("Execute Action"):
                if action == "Reset Password":
                    try:
                        new_password = "password123"
                        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
                                      (hash_password(new_password), selected_user))
                        conn.commit()
                        st.success(f"Password reset successfully for {selected_user}. New password: {new_password}")
                    except Exception as e:
                        st.error(f"Error resetting password: {e}")
                elif action == "Disable Account":
                    st.info("Account disable functionality would be implemented here.")
                elif action == "Delete Account":
                    try:
                        cursor.execute("DELETE FROM users WHERE username = ?", (selected_user,))
                        conn.commit()
                        st.success(f"Account {selected_user} deleted successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting account: {e}")
        else:
            st.info("No users found with the selected role.")
        
        conn.close()
    
    with tabs[2]:  # Hospital Approvals
        st.subheader("Hospital Registration Approvals")
        st.info("In a production system, hospital registrations would require admin approval before activation.")
        
        # Demo of approval workflow
        with st.form("hospital_approval_demo"):
            hospital_name = st.text_input("Hospital Name")
            hospital_address = st.text_input("Hospital Address")
            hospital_contact = st.text_input("Contact Person")
            hospital_status = st.selectbox("Status", ["Pending", "Approved", "Rejected"])
            
            submit_button = st.form_submit_button("Update Approval Status")
            
            if submit_button:
                st.success(f"Hospital {hospital_name} status updated to {hospital_status}")
    
    with tabs[3]:  # System Logs
        st.subheader("System Logs")
        
        # Demo of system logs
        log_entries = [
            {"timestamp": "2025-04-26 09:15:23", "level": "INFO", "message": "User login: admin"},
            {"timestamp": "2025-04-26 09:12:11", "level": "INFO", "message": "System backup completed"},
            {"timestamp": "2025-04-26 08:45:02", "level": "WARNING", "message": "Failed login attempt: unknown_user"},
            {"timestamp": "2025-04-26 08:30:15", "level": "INFO", "message": "New user registered: patient4321"},
            {"timestamp": "2025-04-26 08:25:33", "level": "ERROR", "message": "Database connection timeout"},
            {"timestamp": "2025-04-25 23:15:12", "level": "INFO", "message": "System maintenance started"},
            {"timestamp": "2025-04-25 22:30:45", "level": "INFO", "message": "Daily report generated"},
            {"timestamp": "2025-04-25 21:12:05", "level": "WARNING", "message": "Low disk space warning"},
        ]
        
        log_df = pd.DataFrame(log_entries)
        st.dataframe(log_df)
        
        if st.button("Export Logs"):
            log_df.to_csv("system_logs.csv", index=False)
            st.download_button(
                "Download System Logs", 
                data=open("system_logs.csv", "rb"), 
                file_name="system_logs.csv"
            )

# Main dashboard router
def dashboard():
    # Add sidebar with user info and logout
    with st.sidebar:
        logo_url = get_trackmyhealth_logo()
        st.markdown(f'<img src="{logo_url}" style="width:80px;">', unsafe_allow_html=True)
        st.markdown(f"### Welcome, {st.session_state.user['name']}")
        st.write(f"Role: {st.session_state.user['role'].capitalize()}")
        
        # Add navigation links based on role
        st.markdown("---")
        st.markdown("### Navigation")
        
        role = st.session_state.user['role']
        if role == "patient":
            st.markdown("- Book Appointments")
            st.markdown("- View Health Records")
            st.markdown("- Track Health Data")
            st.markdown("- Find Hospitals")
        elif role == "hospital":
            st.markdown("- Manage Appointments")
            st.markdown("- Update Hospital Profile")
            st.markdown("- Patient Records")
        elif role == "admin":
            st.markdown("- System Statistics")
            st.markdown("- User Management")
            st.markdown("- Hospital Approvals")
        
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # Main content area
    role = st.session_state.user['role']
    if role == "patient":
        patient_dashboard()
    elif role == "hospital":
        hospital_dashboard()
    elif role == "admin":
        admin_dashboard()

def main():
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #28A745;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f8f9fa;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 16px;
            font-size: 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #28A745 !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    initialize_database()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()

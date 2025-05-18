import streamlit as st
import subprocess
import time
import pandas as pd
import plotly.express as px
from database.db_connector import get_db_connection
from web.company_auth import get_company_by_name, create_company, get_company_by_id
from web.auth import verify_admin, create_admin, hash_password

# --- Initial Login Page ---
def initial_login_page():
    st.title("Company Login")
    company_name = st.text_input("Company Name")
    username = st.text_input("Username")
    if st.button("Login"):
        company = get_company_by_name(company_name)
        if not company:
            st.error("Company not found.")
            return
        company_id = company['company_id']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username=%s AND company_id=%s", (username, company_id))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        if admin:
            st.session_state['company_id'] = company_id
            st.session_state['company_name'] = company_name
            st.session_state['admin_username'] = username
            st.session_state['admin_id'] = admin['admin_id']
            st.session_state['is_admin'] = False  # Not admin dashboard yet
            st.success(f"Welcome, {company_name}!")
            st.rerun()
        else:
            st.error("Invalid company or username.")
    st.markdown("---")
    if st.button("Sign Up Company"):
        st.session_state['show_signup'] = True

# --- Signup Page ---
def signup_page():
    st.title("Company & Admin Signup")
    company_name = st.text_input("Company Name")
    admin_username = st.text_input("Admin Username")
    admin_name = st.text_input("Admin Full Name")
    admin_password = st.text_input("Admin Password", type="password")
    if st.button("Register Company and Admin"):
        if not (company_name and admin_username and admin_name and admin_password):
            st.error("Please fill in all fields.")
        else:
            company = get_company_by_name(company_name)
            if company:
                st.error("Company already exists. Please login.")
                return
            company_id = create_company(company_name)
            create_admin(admin_username, admin_name, admin_password, company_id)
            st.success(f"Company '{company_name}' and admin '{admin_username}' registered! Please login.")
            st.session_state['show_signup'] = False
    if st.button("Back to Login"):
        st.session_state['show_signup'] = False

# --- Mark Attendance Page ---
def mark_attendance_page():
    st.title("Mark Your Attendance")
    st.write("Face the camera and click the button below to mark your attendance.")
    if st.button("Mark Attendance"):
        with st.spinner("Checking face..."):
            result = subprocess.run(
                ["python", "src/3_face_recognition.py", str(st.session_state['company_id']), "--once"],
                capture_output=True, text=True
            )
            output = result.stdout.strip()
        if output.startswith("Attendance marked for:"):
            st.success(output)
            time.sleep(10)
        elif output.startswith("Attendance already marked for:"):
            st.info(output)
            time.sleep(10)
        elif output == "Face not recognized.":
            st.error("Face not recognized. Please try again.")
            time.sleep(10)
        else:
            st.error("An error occurred. Please try again.")
            time.sleep(10)
    st.sidebar.markdown("---")
    if st.sidebar.button("Login as Admin"):
        st.session_state['show_admin_login'] = True
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# --- Admin Login Modal ---
def admin_login_page():
    st.title("Admin Login")
    username = st.text_input("Admin Username")
    password = st.text_input("Admin Password", type="password")
    if st.button("Login as Admin"):
        company_id = st.session_state['company_id']
        admin = verify_admin(username, password, company_id)
        if admin:
            st.session_state['is_admin'] = True
            st.session_state['admin_id'] = admin['admin_id']
            st.session_state['admin_username'] = username
            st.success(f"Welcome, {admin['name']} (Admin)!")
            st.session_state['show_admin_login'] = False
            st.rerun()
        else:
            st.error("Invalid admin credentials.")
    if st.button("Back"):
        st.session_state['show_admin_login'] = False

# --- Register User Page ---
def register_user_page():
    st.header("Register New Employee")
    if 'data_collected' not in st.session_state:
        st.session_state['data_collected'] = False

    user_id = st.text_input("User ID")
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type='password', key="new_user_password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Collect Data", key="collect_data_btn"):
            if not user_id or not name:
                st.error("User ID and Name are required to collect data.")
            else:
                result = subprocess.run(
                    ["python", "src/1_data_collection.py", user_id, name],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.session_state['data_collected'] = True
                    st.success("Face data collected successfully! Now you can add the user.")
                else:
                    st.session_state['data_collected'] = False
                    st.error("Data collection failed. Please try again.")

    with col2:
        add_user_disabled = not st.session_state['data_collected']
        if st.button("Add User", key="add_user_btn", disabled=add_user_disabled):
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (user_id, name, email, password_hash, company_id) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, name, email, hash_password(password), st.session_state['company_id'])
                )
                conn.commit()
                st.success("User registered. Training model...")
                train_result = subprocess.run(
                    ["python", "src/2_train_model.py"],
                    capture_output=True, text=True
                )
                if train_result.returncode == 0:
                    st.success("Model trained and user added successfully!")
                    time.sleep(2)
                    st.session_state['data_collected'] = False
                    st.session_state['new_user_password'] = ""
                    st.rerun()
                else:
                    st.error("Model training failed.")
            except Exception as e:
                if "Duplicate entry" in str(e):
                    st.error("A user with this ID or email already exists.")
                else:
                    st.error(f"Error: {e}")
            finally:
                cursor.close()
                conn.close()

# --- Analytics Page ---
def analytics_page():
    st.header("📈 Employee Attendance Analytics")
    conn = get_db_connection()
    users_df = pd.read_sql(
        f"SELECT user_id, name FROM users WHERE company_id = {st.session_state['company_id']} ORDER BY name", conn)
    st.markdown("---")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("Select Employee")
        selected_user = st.selectbox(
            "Choose an employee:",
            options=users_df['name'],
            index=0,
            help="Select employee to view monthly attendance stats"
        )
        user_id = users_df[users_df['name'] == selected_user]['user_id'].values[0]
    with col2:
        if selected_user:
            query = f"""
                SELECT 
                    MONTH(timestamp) as month,
                    COUNT(DISTINCT DATE(timestamp)) as days_present
                FROM attendance
                WHERE user_id = {user_id}
                    AND YEAR(timestamp) = YEAR(CURDATE())
                GROUP BY MONTH(timestamp)
                ORDER BY MONTH(timestamp)
            """
            monthly_df = pd.read_sql(query, conn)
            full_months = pd.DataFrame({'month': range(1,13)})
            merged_df = full_months.merge(monthly_df, on='month', how='left').fillna(0)
            fig = px.bar(
                merged_df,
                x='month',
                y='days_present',
                labels={'month': 'Month', 'days_present': 'Days Present'},
                color='month',
                color_continuous_scale='rainbow',
                title=f"Monthly Attendance for {selected_user} ({pd.Timestamp.now().year})"
            )
            fig.update_layout(
                xaxis = dict(
                    tickmode = 'array',
                    tickvals = list(range(1,13)),
                    ticktext = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=500
            )
            fig.update_yaxes(range=[0, 31])
            st.plotly_chart(fig, use_container_width=True)

            # --- Month selection for detailed table ---
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            selected_month = st.selectbox(
                "Click a month to view daily attendance:",
                options=list(range(1, 13)),
                format_func=lambda x: month_names[x-1]
            )

            # Query for detailed attendance in the selected month
            detailed_query = f"""
                SELECT 
                    DATE(timestamp) as date, 
                    DATE_FORMAT(timestamp, '%h:%i %p') as time
                FROM attendance
                WHERE user_id = {user_id}
                  AND YEAR(timestamp) = YEAR(CURDATE())
                  AND MONTH(timestamp) = {selected_month}
                ORDER BY date
            """
            detailed_df = pd.read_sql(detailed_query, conn)
            if not detailed_df.empty:
                st.markdown(f"#### Attendance Details for {month_names[selected_month-1]}")
                st.dataframe(detailed_df)
            else:
                st.info("No attendance records for this month.")
        else:
            st.info("ℹ️ Select an employee from the dropdown to view their attendance patterns")
    conn.close()

# --- Admin Dashboard ---
def admin_dashboard():
    st.sidebar.title("Admin Dashboard")
    page = st.sidebar.radio("Go to", [
        "Register New User", "Analytics"
    ], index=1)
    if page == "Register New User":
        register_user_page()
    elif page == "Analytics":
        analytics_page()
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# --- Main Logic ---
def main():
    if st.session_state.get('show_signup'):
        signup_page()
        return
    if 'company_id' not in st.session_state:
        initial_login_page()
        return
    if st.session_state.get('show_admin_login'):
        admin_login_page()
        return
    if st.session_state.get('is_admin'):
        admin_dashboard()
    else:
        mark_attendance_page()

if __name__ == "__main__":
    main()

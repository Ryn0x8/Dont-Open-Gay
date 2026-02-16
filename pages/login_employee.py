import streamlit as st
from auth_utils import check_password, verify_face
from database import get_user
import base64
import time

# --- Page config ---
st.set_page_config(page_title="Employee Login - Anvaya", layout="wide", initial_sidebar_state="collapsed")

# --- Page-specific CSS overrides (your original design) ---
st.markdown("""
<style>
    /* Hide Streamlit default UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Main container styling */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        padding-left: 6rem;
        padding-right: 6rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Form container styling - override for this page only */
    div.stForm {
        background-color: #ffffff !important;
        padding: 30px 35px !important;
        border-radius: 16px !important;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.1) !important;
        max-width: 450px !important;
        margin: 0 auto !important;
        border: 1px solid #eaeef2 !important;
    }

    /* Input field styling - make them visible */
    div.stTextInput {
        margin-bottom: 20px !important;
    }

    div.stTextInput > label {
        color: #374151 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin-bottom: 6px !important;
        display: block !important;
    }

    div.stTextInput > div > input {
        background-color: #f8fafc !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        width: 100% !important;
        font-size: 15px !important;
        color: #1e293b !important;
        transition: all 0.2s ease !important;
    }

    div.stTextInput > div > input:focus {
        border-color: #2563EB !important;
        background-color: #ffffff !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
        outline: none !important;
    }

    div.stTextInput > div > input:hover {
        border-color: #94a3b8 !important;
        background-color: #ffffff !important;
    }

    div.stTextInput > div > input[type="password"] {
        background-color: #f8fafc !important;
        letter-spacing: 2px;
    }

    div.stForm button:first-child {
        background-color: #2563EB !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        border-radius: 10px !important;
        padding: 12px 20px !important;
        width: 100% !important;
        border: none !important;
        margin-top: 10px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 6px -1px rgba(37,99,235,0.2) !important;
    }

    div.stForm button:first-child:hover {
        background-color: #1E40AF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 8px -1px rgba(37,99,235,0.3) !important;
    }

    /* Navigation buttons styling */
    div.stButton > button {
        background-color: white !important;
        color: #2563EB !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        border: 1.5px solid #2563EB !important;
        transition: all 0.2s ease !important;
        width: auto !important;
        min-width: 160px !important;
    }

    div.stButton > button:hover {
        background-color: #2563EB !important;
        color: white !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px -1px rgba(37,99,235,0.2) !important;
    }

    /* Message styling */
    .stAlert {
        border-radius: 10px !important;
        margin-top: 20px !important;
        padding: 12px 16px !important;
    }

    .stAlert.success {
        background-color: #f0fdf4 !important;
        border-color: #86efac !important;
        color: #166534 !important;
    }

    .stAlert.error {
        background-color: #fef2f2 !important;
        border-color: #fecaca !important;
        color: #991b1b !important;
    }

    .stAlert.info {
        background-color: #eff6ff !important;
        border-color: #bfdbfe !important;
        color: #1e40af !important;
    }

    /* Spinner styling */
    .stSpinner > div {
        border-color: #2563EB !important;
    }

    /* Keep theme colors for other elements */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color) !important;
    }
    
    p {
        color: var(--text-color) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Function to get base64 image ---
def get_base64_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# --- Logo ---
logo_base64 = get_base64_image("logo.jpg")
if logo_base64:
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:25px;">
        <img src="data:image/png;base64,{logo_base64}" 
             style="width:100px; height:100px; border-radius:50%; object-fit:cover; box-shadow:0px 8px 20px rgba(0,0,0,0.1); border: 2px solid white;">
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; margin-bottom:25px;">
        <div style="width:100px; height:100px; border-radius:50%; background-color:#2563EB; margin:0 auto; display:flex; align-items:center; justify-content:center; box-shadow:0px 8px 20px rgba(0,0,0,0.1);">
            <span style="color:white; font-size:40px; font-weight:bold;">A</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<h3 style="text-align:center; margin-bottom:5px; font-weight:600;">Employee Login</h3>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; margin-top:0px; margin-bottom:25px; font-size:15px; opacity:0.8;">Welcome back! Enter your credentials to continue.</p>', unsafe_allow_html=True)

# --- Session state initialization for multi-step login ---
if "login_step" not in st.session_state:
    st.session_state.login_step = "credentials"
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "face_verified" not in st.session_state:
    st.session_state.face_verified = False

# --- Step 1: Credentials ---
if st.session_state.login_step == "credentials":
    with st.form("emp_login_form"):
        email = st.text_input("Email", placeholder="Enter your email address", key="login_email")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_clicked = st.form_submit_button("Login", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Navigation buttons
    col1, col2, col3, col4 = st.columns([1, 0.5, 0.6, 1])
    with col2:
        if st.button("← Back to Home", key="home_btn", use_container_width=True):
            st.switch_page("app.py")
    with col3:
        if st.button("Create an account →", key="signup_btn", use_container_width=True):
            st.switch_page("pages/signup_employee.py")

    if login_clicked:
        if not email or not password:
            st.error("⚠️ Please enter both email and password.")
        else:
            user = get_user(email)
            if user:
                stored_password = user[3]
                stored_role = user[4]

                if stored_role != "employee":
                    st.error("❌ This account is not registered as an employee.")
                elif check_password(password, stored_password):
                    # Move to face verification
                    st.session_state.user_data = user
                    st.session_state.login_step = "verifying"
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Please try again.")
            else:
                st.error("❌ No account found with this email.")
                st.info("Don't have an account? Click 'Create an account' below.")

# --- Step 2: Face Verification ---
if st.session_state.login_step == "verifying":
    user = st.session_state.user_data
    st.markdown("### 📸 Face Verification")
    st.write("Please look at the camera and take a photo for verification.")

    # Call verify_face – it now uses st.camera_input and returns True/False
    if verify_face(user[2]):  # user[2] is email
        # Success
        st.session_state.authenticated = True
        st.session_state.user_id = user[0]
        st.session_state.user_name = user[1]
        st.session_state.user_email = user[2]

        st.success("✅ Login successful! Welcome back.")
        st.balloons()
        st.markdown(f"""
        <div style="text-align:center; padding:20px; background-color:#f0fdf4; border-radius:10px; margin-top:20px;">
            <h4 style="color:#166534; margin-bottom:5px;">Welcome, {user[1]}!</h4>
            <p style="color:#166534;">You have successfully logged in as an employee.</p>
        </div>
        """, unsafe_allow_html=True)

        # Clean up session and redirect
        st.session_state.login_step = "credentials"
        st.session_state.user_data = None
        st.info("Redirecting to your dashboard...")
        time.sleep(2)
        st.switch_page("pages/employee_dashboard.py")
    else:
        # Verification failed – stay in this step (user can retry)
        if st.button("Try Again"):
            st.rerun()
        if st.button("Back to Login"):
            st.session_state.login_step = "credentials"
            st.session_state.user_data = None
            st.rerun()
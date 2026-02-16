import streamlit as st
from auth_utils import check_password, generate_otp, send_otp
import base64
import time
from database import get_user, get_company_by_email, create_company_for_employer, get_company_by_id

# --- Page config ---
st.set_page_config(page_title="Employer Login - Anvaya", layout="wide", initial_sidebar_state="collapsed")

# --- Page-specific CSS overrides ---
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

    /* Form container styling */
    div.stForm {
        background-color: #ffffff !important;
        padding: 30px 35px !important;
        border-radius: 16px !important;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.1) !important;
        max-width: 450px !important;
        margin: 0 auto !important;
        border: 1px solid #eaeef2 !important;
    }

    /* Input fields */
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

    /* Form submit button */
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

    /* Messages */
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
    
    /* OTP section styling */
    .otp-section {
        margin-top: 20px;
        padding: 20px;
        background-color: #f8fafc;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    
    .resend-link {
        color: #2563EB;
        cursor: pointer;
        text-decoration: underline;
        font-size: 14px;
    }
    .resend-link:hover {
        color: #1E40AF;
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

# --- Initialize session state for OTP ---
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "otp_verified" not in st.session_state:
    st.session_state.otp_verified = False
if "otp" not in st.session_state:
    st.session_state.otp = None
if "login_email" not in st.session_state:
    st.session_state.login_email = None
if "login_user_data" not in st.session_state:
    st.session_state.login_user_data = None

# --- Logo ---
logo_base64 = get_base64_image("logo.jpg")

# --- Header ---
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
            <span style="color:white; font-size:40px; font-weight:bold;">E</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<h3 style="text-align:center; margin-bottom:5px; font-weight:600;">Employer Login</h3>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; margin-top:0px; margin-bottom:25px; font-size:15px; opacity:0.8;">Welcome back! Enter your credentials to continue.</p>', unsafe_allow_html=True)

# --- Login Form (shown only if OTP not yet verified) ---
if not st.session_state.otp_verified:
    with st.form("employer_login_form"):
        email = st.text_input("Email", placeholder="Enter your email address", key="emp_login_email")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="emp_login_password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_clicked = st.form_submit_button("Login", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Navigation buttons ---
    col1, col2, col3, col4 = st.columns([1, 0.5, 0.6, 1])
    with col2:
        if st.button("← Back to Home", key="emp_home_btn", use_container_width=True):
            st.switch_page("app.py")
    with col3:
        if st.button("Create an account →", key="emp_signup_btn", use_container_width=True):
            st.switch_page("pages/signup_employer.py")

    # --- Handle initial login logic ---
    if login_clicked:
        if not email or not password:
            st.error("⚠️ Please enter both email and password.")
        else:
            user = get_user(email)
            if user:
                stored_password = user[3]  
                stored_role = user[4]     

                if stored_role != "employer":
                    st.error("❌ This account is not registered as an employer.")
                elif check_password(password, stored_password):
                    otp = generate_otp()
                    st.session_state.otp = otp
                    st.session_state.login_email = email
                    st.session_state.login_user_data = user
                    st.session_state.otp_sent = True
                    
                    with st.spinner("📧 Sending verification code to your email..."):
                        if send_otp(email, otp):
                            st.success("✅ Verification code sent to your email!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to send verification code. Please try again.")
                            st.session_state.otp_sent = False
                else:
                    st.error("❌ Incorrect password. Please try again.")
            else:
                st.error("❌ No account found with this email.")
                st.info("Don't have an account? Click 'Create an account' below.")

# --- OTP Verification Section ---
if st.session_state.otp_sent and not st.session_state.otp_verified:
    st.markdown('<div class="otp-section">', unsafe_allow_html=True)
    st.markdown('<h4 style="margin-bottom:15px;">📧 Email Verification</h4>', unsafe_allow_html=True)
    st.markdown('<p style="margin-bottom:20px;">Enter the 6-digit code sent to your email address.</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        otp_input = st.text_input("Verification Code", placeholder="Enter 6-digit code", max_chars=6, key="otp_input")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Verify", type="primary", use_container_width=True):
            if otp_input and otp_input == str(st.session_state.otp):
                with st.spinner("Verifying..."):
                    time.sleep(1) 
                    st.session_state.otp_verified = True
                    
                    user = st.session_state.login_user_data
                    # Try to get the company by email
                    company = get_company_by_email(user[2])  # user[2] is email
                    
                    # If no company exists, create one using the user's name as company name
                    if not company:
                        company_id = create_company_for_employer(user[0], user[1], user[2])
                        company = get_company_by_id(company_id)
                    
                    if company:
                        st.session_state.employer_authenticated = True
                        st.session_state.company_id = company[0]
                        st.session_state.employer_name = company[1]  # company name
                        st.session_state.employer_email = user[2]
                        
                        st.success("✅ Login successful! Welcome back.")
                        st.balloons()
                        st.markdown(f"""
                        <div style="text-align:center; padding:20px; background-color:#f0fdf4; border-radius:10px; margin-top:20px;">
                            <h4 style="color:#166534; margin-bottom:5px;">Welcome, {company[1]}!</h4>
                            <p style="color:#166534;">You have successfully logged in as an employer.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(2)
                        st.switch_page("pages/employer_dashboard.py")
                    else:
                        st.error("❌ Could not create company profile. Please contact support.")
            else:
                st.error("❌ Invalid verification code. Please try again.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Resend Code", use_container_width=True):
            otp = generate_otp()
            st.session_state.otp = otp
            with st.spinner("Resending code..."):
                if send_otp(st.session_state.login_email, otp):
                    st.success("✅ New verification code sent to your email!")
                else:
                    st.error("❌ Failed to send code. Please try again.")
    
    if st.button("← Back to Login", use_container_width=True):
        st.session_state.otp_sent = False
        st.session_state.otp = None
        st.session_state.login_email = None
        st.session_state.login_user_data = None
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.otp_verified and "company_id" in st.session_state:
    st.markdown("""
    <div style="text-align:center; padding:15px; background-color:#f0fdf4; border-radius:10px; margin:20px 0;">
        <p style="color:#166534; margin:0;">✓ Verification complete! Redirecting to dashboard...</p>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.switch_page("pages/employer_dashboard.py")
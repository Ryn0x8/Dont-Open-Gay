import streamlit as st
from auth_utils import generate_otp, send_otp, hash_password, capture_face
from database import add_user, get_user
import base64
import time

st.set_page_config(page_title="Employee Sign Up - Anvaya", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Hide Streamlit default UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}

    /* Main container styling */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        padding-left: 6rem;
        padding-right: 6rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    div.stTextInput div[role="progressbar"] {
        display: none !important;
    }

    /* Form container styling - matching login page */
    div.stForm {
        background-color: #ffffff !important;
        padding: 30px 35px !important;
        border-radius: 16px !important;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.1) !important;
        max-width: 550px !important;
        margin: 0 auto !important;
        border: 1px solid #eaeef2 !important;
        transition: all 0.3s ease !important;
    }

    /* Input field styling */
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

    /* Password field */
    div.stTextInput > div > input[type="password"] {
        background-color: #f8fafc !important;
        letter-spacing: 2px;
    }

    /* Button styling inside form */
    div.stForm button {
        border-radius: 10px !important;
        padding: 12px 20px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.2s ease !important;
        border: none !important;
        margin-top: 5px !important;
        
    }

    /* Send OTP button */
    div.stForm button:first-child {
        background-color: #2563EB !important;
        color: white !important;
        box-shadow: 0 4px 6px -1px rgba(37,99,235,0.2) !important;
    }

    div.stForm button:first-child:hover {
        background-color: #1E40AF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 8px -1px rgba(37,99,235,0.3) !important;
    }

    /* Verify button */
    div.stForm button:last-child {
        background-color: #10B981 !important;
        color: white !important;
        box-shadow: 0 4px 6px -1px rgba(16,185,129,0.2) !important;
    }

    div.stForm button:last-child:hover {
        background-color: #059669 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 8px -1px rgba(16,185,129,0.3) !important;
    }


    /* Message styling */
    .stAlert {
        border-radius: 10px !important;
        margin-top: 20px !important;
        margin-bottom: 20px !important;
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

    .otp-section {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 2px dashed #e2e8f0;
    }

    div.stButton > button {
        background-color: white !important;
        color: #2563EB !important;
        border: 1.5px solid #2563EB !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
        width: auto !important;
        min-width: 160px !important;
    }

    div.stButton > button:hover {
        background-color: #2563EB !important;
        color: white !important;
        transform: translateY(-1px) !important;
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

def get_base64_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

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

st.markdown('<h3 style="text-align:center; margin-bottom:5px; font-weight:600;">Employee Sign Up</h3>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; margin-top:0px; margin-bottom:25px; font-size:15px; opacity:0.8;">Create your employee account to get started.</p>', unsafe_allow_html=True)

if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "otp_verified" not in st.session_state:
    st.session_state.otp_verified = False
if "email_for_verification" not in st.session_state:
    st.session_state.email_for_verification = None

with st.form("employee_signup_form"):
    st.markdown('<p style="font-size:18px; font-weight:600; margin-bottom:20px;">Account Details</p>', unsafe_allow_html=True)
    
    name = st.text_input("Full Name", placeholder="Enter your full name", key="form_name")
    email = st.text_input("Email Address", placeholder="Enter your email address", key="form_email")
    password = st.text_input("Password", type="password", placeholder="Create a strong password", key="form_password")
    
    send_otp_clicked = st.form_submit_button("📧 Send OTP")
    
    if st.session_state.otp_sent and not st.session_state.otp_verified:
        st.markdown('<div class="otp-section">', unsafe_allow_html=True)
        st.markdown('<p style="font-size:16px; font-weight:600; margin-bottom:15px;">OTP Verification</p>', unsafe_allow_html=True)
        
        user_otp = st.text_input("Enter OTP", placeholder="Enter the 6-digit OTP sent to your email", key="form_otp")
        
        verify_clicked = st.form_submit_button("✅ Verify & Capture Face")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        verify_clicked = False
        user_otp = None

if send_otp_clicked:
    if not name or not email or not password:
        st.error("⚠️ Please fill in all fields before sending OTP.")
    else:
        existing_user = get_user(email)
        if existing_user:
            st.error("❌ Email already registered! Please use a different email or login.")
        else:
            otp = generate_otp()
            st.session_state.otp = otp
            st.session_state.email_for_verification = email
            st.session_state.otp_sent = True
            st.session_state.otp_verified = False
            
            with st.spinner("Sending OTP to your email..."):
                send_otp(email, otp)
            
            st.success("✅ OTP Sent! Please check your email.")
            st.rerun()  

if verify_clicked and user_otp:
    if not user_otp:
        st.error("⚠️ Please enter the OTP.")
    elif user_otp == str(st.session_state.otp):
        with st.spinner("📸 Verifying OTP and capturing face..."):
            st.info("📷 Please look at the camera for face capture...")
            
            success = capture_face(email)
            
            if success:
                hashed = hash_password(password)
                add_user(name, email, hashed, "employee")
                
                st.session_state.otp_verified = True
                st.success("✅ Employee Account Created Successfully!")
                st.balloons()
                
                st.markdown(f"""
                <div style="text-align:center; padding:20px; background-color:#f0fdf4; border-radius:10px; margin:20px 0;">
                    <h4 style="color:#166534; margin-bottom:5px;">Welcome, {name}!</h4>
                    <p style="color:#166534;">Your employee account has been created successfully.</p>
                    <p style="color:#166534; font-size:14px;">You can now login with your credentials.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("❌ Face/Logo not detected. Please try again.")
                st.info("Make sure you're in a well-lit area and looking directly at the camera.")
    else:
        st.error("❌ Invalid OTP. Please try again.")

if st.session_state.get('otp_verified', False):
    st.markdown("""
    <div style="text-align:center; padding:15px; background-color:#f0fdf4; border-radius:10px; margin:20px 0;">
        <p style="color:#166534; margin:0;">✓ Account created successfully! You can now login.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1, 0.5, 0.6, 1])

with col2:
    if st.button("← Back to Home", key="home_btn", use_container_width=True):
        st.switch_page("app.py")

with col3:
    if st.button("Login instead →", key="login_btn", use_container_width=True):
        st.switch_page("pages/login_employee.py")

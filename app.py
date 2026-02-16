import streamlit as st
from PIL import Image
import base64
from database import connect, add_user, get_user, create_tables

st.set_page_config(
    page_title="Anvaya",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

create_tables()

# -------- FORCE LIGHT BACKGROUND --------
st.markdown("""
<style>

/* Force white background everywhere */
html, body, [data-testid="stApp"] {
    background-color: #F4F6F8 !important;
}

/* Remove header/footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main container spacing */
.block-container {
    padding-top: 0.9rem;
    padding-bottom: 4rem;
    padding-left: 6rem;
    padding-right: 6rem;
}

/* Title */
.main-title {
    font-size: 52px;
    font-weight: 700;
    color: #1F2937;
    line-height: 1.2;
}

/* Sub line */
.sub-line {
    font-size: 22px;
    color: #4B5563;
    margin-top: 10px;
}

/* Tagline */
.tagline {
    font-size: 28px;
    font-weight: 600;
    color: #111827;
    margin-top: 30px;
}

/* Description */
.description {
    font-size: 18px;
    color: #374151;
    margin-top: 15px;
    max-width: 550px;
    line-height: 1.6;
}

/* Accent text */
.accent {
    color: #2563EB;
    font-weight: 600;
}

/* Buttons */
.stButton > button {
    background-color: #2563EB;
    color: white;
    font-size: 17px;
    padding: 12px 30px;
    border-radius: 8px;
    border: none;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background-color: #1D4ED8;
    transform: translateY(-2px);
}

/* Logo styling */
.logo-img {
    border-radius: 50%;
    width: 200px;
    height: 200px;
    object-fit: cover;
    box-shadow: 0px 10px 25px rgba(0,0,0,0.08);
    margin-top: 60px;
}

</style>
""", unsafe_allow_html=True)

# -------- LAYOUT --------
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="main-title">Still Unemployed or Looking for Employees?</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-line">We got you covered.</div>', unsafe_allow_html=True)

    st.markdown('<div class="tagline">The Future of Hiring</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="description">
    <span class="accent">Anvaya</span> is a smart bridge between talent and hiring. 
    We simplify recruitment by connecting skilled individuals with 
    companies that truly value their potential.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    btn1, btn2 = st.columns(2)

    with btn1:
        if st.button("Hire Talent"):
            st.switch_page("pages/login_employer.py")

    with btn2:
        if st.button("Find Job"):
            st.switch_page("pages/login_employee.py")

import base64

def get_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64("logo.jpg")

with col2:
    st.markdown(f"""
        <div style="display:flex; justify-content:center; align-items:center; margin-top:60px;">
            <img src="data:image/png;base64,{logo_base64}"
                 style="
                    width:220px;
                    height:220px;
                    object-fit:cover;
                    border-radius:50%;
                    box-shadow:0px 10px 30px rgba(0,0,0,0.08);
                    margin-top:60px;
                 ">
        </div>
    """, unsafe_allow_html=True)




st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<center style="color:#6B7280; font-size:16px;">Register in Anvaya Today</center>', unsafe_allow_html=True)

import streamlit as st
import base64
from PIL import Image

st.set_page_config(
    page_title="Anvaya – The Future of Hiring",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# import pkg_resources
# import streamlit as st

# packages = sorted([f"{d.project_name}=={d.version}" for d in pkg_resources.working_set])
# st.write(packages)

# --- Custom CSS (glass‑morphism, modern) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    :root {
        --primary: #4F46E5;
        --primary-light: #818CF8;
        --primary-dark: #3730A3;
        --secondary: #0EA5E9;
        --accent: #10B981;
        --bg: #F8FAFC;
        --card-bg: rgba(255,255,255,0.9);
        --text: #0F172A;
        --text-light: #475569;
        --border: #E2E8F0;
        --shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        --shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.02);
        --glass-bg: rgba(255,255,255,0.7);
        --glass-border: 1px solid rgba(255,255,255,0.5);
    }

    .stApp {
        background: radial-gradient(circle at 10% 30%, rgba(255,255,255,0.95) 0%, #f1f5f9 100%);
    }

    /* Remove default header/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        padding-left: 6rem;
        padding-right: 6rem;
        max-width: 1400px;
        margin: 0 auto;
    }

    /* Hero section */
    .hero-section {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        padding: 3rem 4rem;
        border-radius: 60px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-lg);
        backdrop-filter: blur(5px);
        text-align: center;
    }

    .hero-section h1 {
        font-size: 4rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 1rem;
        line-height: 1.2;
    }

    .hero-section p {
        font-size: 1.5rem;
        opacity: 0.9;
        max-width: 700px;
        margin: 0 auto;
    }

    /* Logo styling */
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 2rem 0;
    }

    .logo-img {
        width: 240px;
        height: 240px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: var(--shadow-lg);
        border: 4px solid white;
    }

    /* Tagline card */
    .tagline-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 40px;
        padding: 2.5rem 3rem;
        border: var(--glass-border);
        box-shadow: var(--shadow-lg);
        text-align: center;
        margin: 2rem 0 3rem;
    }

    .tagline-card h2 {
        font-size: 2.5rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 1rem;
    }

    .tagline-card p {
        font-size: 1.2rem;
        color: var(--text-light);
        max-width: 600px;
        margin: 0 auto 1.5rem;
        line-height: 1.6;
    }

    .accent {
        color: var(--primary);
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 60px;
        font-weight: 600;
        font-size: 1.2rem;
        padding: 1rem 2.5rem;
        transition: all 0.2s;
        border: none;
        background: var(--primary);
        color: white;
        box-shadow: var(--shadow-sm);
        width: 100%;
    }

    .stButton > button:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -8px rgba(79, 70, 229, 0.4);
        background: var(--primary-dark);
    }

    /* Footer */
    .footer {
        text-align: center;
        color: var(--text-light);
        font-size: 1rem;
        margin-top: 4rem;
        opacity: 0.8;
    }

    hr {
        border: 0;
        border-top: 1px solid var(--border);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper to load logo ---
def get_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# --- Layout ---
# Hero section
st.markdown("""
<div class="hero-section">
    <h1>Still Unemployed or Looking for Employees?</h1>
    <p>We got you covered.</p>
</div>
""", unsafe_allow_html=True)

# Two columns for logo and tagline
col1, col2 = st.columns([1, 1])

with col1:
    # Logo
    try:
        logo_base64 = get_base64("logo.jpg")  # make sure logo.jpg exists
        st.markdown(f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" class="logo-img">
        </div>
        """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Logo file not found. Please place logo.jpg in the root directory.")

with col2:
    # Tagline card
    st.markdown("""
    <div class="tagline-card">
        <h2>The Future of Hiring</h2>
        <p><span class="accent">Anvaya</span> is a smart bridge between talent and hiring. We simplify recruitment by connecting skilled individuals with companies that truly value their potential.</p>
    </div>
    """, unsafe_allow_html=True)

# Buttons row
btn1, btn2, btn3 = st.columns([1, 1, 1])
with btn1:
    if st.button("🌟 Hire Talent", use_container_width=True):
        st.switch_page("pages/login_employer.py")
with btn2:
    if st.button("🔍 Find Job", use_container_width=True):
        st.switch_page("pages/login_employee.py")
with btn3:
    # Empty column for balance
    pass

# Divider
st.markdown("<hr>", unsafe_allow_html=True)

# Footer
st.markdown('<div class="footer">✨ Register in Anvaya Today – Your Future Starts Here</div>', unsafe_allow_html=True)
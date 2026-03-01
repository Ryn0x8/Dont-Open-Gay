import streamlit as st
import pandas as pd
import numpy as np
import os
import base64
import time
import plotly.express as px
import random
import string
from datetime import datetime
from streamlit_option_menu import option_menu
from auth_utils import send_email, hash_password  
from database import (
    get_user_by_id, get_or_create_profile, update_profile,
    update_user_name, get_all_companies, get_company_jobs, search_jobs, get_job_by_id,
    add_application, get_user_applications, save_job, unsave_job, get_saved_jobs,
    add_notification, get_user_notifications, mark_notifications_read,
    add_job_request, get_user_requests,
    get_conversations, get_messages, send_message, mark_messages_read,
    get_application_stats, get_applications_over_time, get_interview_count,
    delete_job_request, update_job_request, update_user_password
)
from database import update_expired_jobs

update_expired_jobs()

# --- EMAIL FUNCTION (place in auth_utils.py, but included here for completeness) ---
from email.message import EmailMessage
import smtplib

def send_email(to_email, subject, body):
    sender_email = st.secrets["EMAIL_ADDRESS"]
    app_password = st.secrets["EMAIL_APP_PASSWORD"]
    if not sender_email or not app_password:
        print("Email credentials missing")
        return False
    try:
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# --- Helper to count unread messages for employee ---
def get_unread_messages_count_employee(employee_id):
    """Count unread messages from companies to this employee."""
    from database import db
    msgs_ref = db.collection('messages')\
                 .where('receiver_id', '==', employee_id)\
                 .where('receiver_type', '==', 'employee')\
                 .where('is_read', '==', False)
    return len(list(msgs_ref.stream()))

# --- Helper to count unread notifications ---
def get_unread_notifications_count(user_id):
    """Return the number of unread notifications for the employee."""
    from database import db
    notifications_ref = db.collection('notifications')\
                          .where('user_id', '==', user_id)\
                          .where('is_read', '==', False)
    return len(list(notifications_ref.stream()))

# --- Password change OTP handling ---
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, otp):
    subject = "Your Anvaya Password Change OTP"
    body = f"Your OTP for changing your password is: {otp}\n\nThis code will expire in 10 minutes."
    return send_email(to_email, subject, body)

# --- Page config ---
st.set_page_config(
    page_title="Employee Dashboard - Anvaya",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Authentication check ---
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.switch_page("pages/login_employee.py")
    st.stop()

from rapidfuzz import fuzz

def calculate_match_score(job_skills, employee_skills, threshold=70):
    if not job_skills or not employee_skills:
        return 0

    job_list = [s.strip().lower() for s in job_skills.split(',')]
    emp_list = [s.strip().lower() for s in employee_skills.split(',')]

    matched = 0

    for job_skill in job_list:
        for emp_skill in emp_list:
            similarity = fuzz.token_sort_ratio(job_skill, emp_skill)
            if similarity >= threshold:
                matched += 1
                break

    return int((matched / len(job_list)) * 100)

def get_resume_download_link(resume_path, text="Download Resume"):
    if resume_path and os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(resume_path)}" style="color: var(--primary); text-decoration: none;">{text}</a>'
        return href
    return None

# --- Custom CSS (softer, less blue, buttons auto width) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    :root {
        --primary: #2563EB;
        --primary-light: #60A5FA;
        --primary-dark: #1E40AF;
        --secondary: #0EA5E9;
        --accent: #10B981;
        --bg: #F8FAFC;
        --card-bg: #FFFFFF;
        --text: #1E293B;
        --text-light: #64748B;
        --border: #E2E8F0;
        --shadow-sm: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px 0 rgba(0,0,0,0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }

    .stApp {
        background: #F1F5F9;
    }

    .badge-count {
        background: #EF4444;
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.2rem 0.5rem;
        border-radius: 40px;
        line-height: 1;
        display: inline-block;
        margin-left: 0.3rem;
    }

    /* Hero header */
    .hero-header {
        background: linear-gradient(135deg, var(--primary), #3B82F6);
        padding: 1.5rem 2rem;
        border-radius: 30px;
        color: white;
        margin: 1rem 0 1.5rem 0;
        box-shadow: var(--shadow-lg);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .hero-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }

    .hero-header p {
        margin: 0.2rem 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }

    .date-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.4rem 1.2rem;
        border-radius: 40px;
        font-weight: 500;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* Notification card */
    .notification-card {
        background: white;
        border-radius: 20px;
        padding: 1rem;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    .notification-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }

    .notification-icon {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }

    .notification-title {
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.2rem;
        font-size: 0.9rem;
    }

    .notification-content {
        font-size: 0.85rem;
        color: var(--text-light);
        margin-bottom: 0.3rem;
    }

    .notification-time {
        font-size: 0.65rem;
        color: var(--text-light);
        margin-top: auto;
    }

    /* Stat cards */
    .stat-card {
        background: white;
        padding: 1.2rem;
        border-radius: 24px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s;
        text-align: center;
    }

    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }

    .stat-card h3 {
        color: var(--text-light);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }

    .stat-card p {
        font-size: 2rem;
        font-weight: 600;
        color: var(--primary);
        margin: 0;
    }

    .metric-card {
        background: white;
        padding: 0.8rem 1.2rem;
        border-radius: 24px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        text-align: center;
    }

    .metric-card .label {
        color: var(--text-light);
        font-size: 0.75rem;
        text-transform: uppercase;
    }

    .metric-card .value {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--primary);
        line-height: 1.2;
    }

    .metric-card .delta {
        font-size: 0.75rem;
        color: var(--accent);
    }

    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--text);
        margin: 1.5rem 0 1rem;
    }

    /* Job / company cards */
    .job-card, .company-card {
        background: white;
        padding: 1.2rem;
        border-radius: 20px;
        border: 1px solid var(--border);
        transition: all 0.2s;
        margin-bottom: 0.8rem;
    }
    .job-card:hover, .company-card:hover {
        box-shadow: var(--shadow-lg);
        border-color: var(--primary);
    }

    /* Buttons - auto width, outline for secondary */
    .stButton > button {
        border-radius: 40px;
        font-weight: 500;
        transition: all 0.2s;
        border: 1px solid transparent;
        padding: 0.4rem 1.2rem;
        background: var(--primary);
        color: white;
        box-shadow: var(--shadow-sm);
        width: auto !important;
    }

    .stButton > button[kind="secondary"] {
        background: white;
        color: var(--primary);
        border: 1px solid var(--primary);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px -2px rgba(37, 99, 235, 0.3);
    }

    /* Text links for navigation */
    .nav-link {
        color: var(--text-light);
        font-weight: 500;
        padding: 0.5rem 0;
        text-decoration: none;
        border-bottom: 2px solid transparent;
        transition: all 0.2s;
        cursor: pointer;
        display: inline-block;
        margin-right: 1.5rem;
    }
    .nav-link.active {
        color: var(--primary);
        border-bottom-color: var(--primary);
    }
    .nav-link:hover {
        color: var(--primary);
    }

    /* Form inputs */
    .stTextInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div > select {
        border-radius: 30px;
        border: 1px solid var(--border);
        padding: 0.6rem 1.2rem;
        background: white;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
    }

    /* Chat container */
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        border-radius: 24px;
        background: #F9FAFB;
        border: 1px solid var(--border);
        margin-bottom: 1rem;
    }

    .chat-bubble-employee {
        background: var(--primary);
        color: white;
        padding: 0.6rem 1rem;
        border-radius: 20px 20px 0 20px;
        max-width: 70%;
        display: inline-block;
        margin: 0.3rem 0;
        text-align: left;
    }

    .chat-bubble-company {
        background: white;
        color: var(--text);
        padding: 0.6rem 1rem;
        border-radius: 20px 20px 20px 0;
        max-width: 70%;
        display: inline-block;
        margin: 0.3rem 0;
        text-align: left;
        border: 1px solid var(--border);
    }

    .chat-timestamp {
        font-size: 0.65rem;
        opacity: 0.7;
        margin-top: 0.2rem;
    }

    hr {
        margin: 1.5rem 0;
        border: 0;
        border-top: 1px solid var(--border);
    }
""", unsafe_allow_html=True)

# --- Fetch counts for badges ---
user_id = st.session_state.user_id
applications = get_user_applications(user_id)
total_apps = len(applications)
pending_apps = sum(1 for a in applications if a[4] == 'pending')
interview_count = get_interview_count(user_id)
saved_count = len(get_saved_jobs(user_id))
unread_msgs = get_unread_messages_count_employee(user_id)
unread_notifications = get_unread_notifications_count(user_id)

# --- Hero Header ---
st.markdown(f"""
<div class="hero-header">
    <div>
        <h1>👋 Welcome back, {st.session_state.user_name}!</h1>
        <p>Your personalized employee dashboard</p>
    </div>
    <div class="date-badge">
        {datetime.now().strftime('%B %d, %Y')}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Styling for pills as underlined tabs ---
st.markdown("""
<style>
    /* ===== RESET ONLY FOR PILLS BUTTONS ===== */
    /* Main pills buttons */
    .st-key-main_pills button {
        all: unset; /* start fresh */
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.5rem 0.8rem !important;
        margin: 0 !important;
        font-family: inherit !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        border-radius: 0 !important;
        transition: color 0.2s, border-color 0.2s !important;
        outline: none !important;
        line-height: normal !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        display: inline-block !important;
        color: var(--text-light) !important;
        border-bottom: 2px solid transparent !important;
    }

    /* Sub pills buttons – any container with class containing "st-key-sub_pills" */
    div[class*="st-key-sub_pills"] button {
        all: unset;
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.5rem 0.8rem !important;
        margin: 0 !important;
        font-family: inherit !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        border-radius: 0 !important;
        transition: color 0.2s, border-color 0.2s !important;
        outline: none !important;
        line-height: normal !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        display: inline-block !important;
        color: var(--text-light) !important;
        border-bottom: 2px solid transparent !important;
    }

    /* ===== MAIN PILLS CONTAINER ===== */
    .st-key-main_pills {
        border-bottom: 1px solid var(--border) !important;
        margin-bottom: 1.5rem !important;
        padding-bottom: 0.5rem !important;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    /* Main pills hover */
    .st-key-main_pills button:hover {
        color: var(--primary) !important;
        border-bottom-color: var(--primary-light) !important;
    }

    /* Main pills active (opened) – using both aria and kind attributes */
    .st-key-main_pills button[aria-pressed="true"],
    .st-key-main_pills button[kind="pillsActive"] {
        color: var(--primary) !important;
        border-bottom-color: var(--primary) !important;
    }

    /* ===== SUB PILLS CONTAINER ===== */
    div[class*="st-key-sub_pills"] {
        margin-bottom: 1rem;
    }

    /* Sub pills hover */
    div[class*="st-key-sub_pills"] button:hover {
        color: #dc2626 !important;
        border-bottom-color: #f87171 !important;
    }

    /* Sub pills active (opened) – red theme */
    div[class*="st-key-sub_pills"] button[aria-pressed="true"],
    div[class*="st-key-sub_pills"] button[kind="pillsActive"] {
        color: #b91c1c !important;
        border-bottom: 2px solid #b91c1c !important;
        background: none !important;
    }

    /* Remove focus rings from all pills buttons */
    .st-key-main_pills button:focus,
    .st-key-main_pills button:active,
    div[class*="st-key-sub_pills"] button:focus,
    div[class*="st-key-sub_pills"] button:active {
        outline: none !important;
        box-shadow: none !important;
        background: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVIGATION using pills ---

if "main_tab" not in st.session_state:
    st.session_state.main_tab = "Dashboard"
if "sub_tab" not in st.session_state:
    st.session_state.sub_tab = None

main_tabs = ["Dashboard", "Jobs", "Applications", "Notifications", "Profile"]
main_icons = {
    "Dashboard": "📊",
    "Jobs": "🔍",
    "Applications": "📋",
    "Notifications": "🔔",
    "Profile": "👤"
}

# --- Main Navigation with pills ---
selected_main = st.pills(
    "",
    options=main_tabs,
    default=st.session_state.main_tab,
    selection_mode="single",
    format_func=lambda tab: f"{main_icons[tab]} {tab}" + 
        (f" ({unread_notifications})" if tab == "Notifications" and unread_notifications > 0 else ""),
    label_visibility="collapsed",
    key="main_pills"   # this creates class st-key-main_pills
)
st.session_state.main_tab = selected_main

# --- Sub Navigation with pills (only when needed) ---
if st.session_state.main_tab == "Jobs":
    sub_tabs = ["Find Jobs", "Companies", "Saved Jobs"]
    sub_icons = {"Find Jobs": "🔍", "Companies": "🏢", "Saved Jobs": "🔖"}
elif st.session_state.main_tab == "Applications":
    sub_tabs = ["My Applications", "Job Requests"]
    sub_icons = {"My Applications": "📋", "Job Requests": "📝"}
elif st.session_state.main_tab == "Profile":
    sub_tabs = ["Profile", "Messages", "Analytics"]
    sub_icons = {"Profile": "👤", "Messages": "💬", "Analytics": "📈"}
else:
    sub_tabs = []
    sub_icons = {}

if sub_tabs:
    # Prepare badges for sub tabs
    sub_badges = {
        "My Applications": pending_apps if pending_apps > 0 else None,
        "Saved Jobs": saved_count if saved_count > 0 else None,
        "Messages": unread_msgs if unread_msgs > 0 else None,
    }

    # Ensure the saved sub_tab is valid for the current main tab
    if st.session_state.sub_tab not in sub_tabs:
        st.session_state.sub_tab = sub_tabs[0]

    selected_sub = st.pills(
        "",
        options=sub_tabs,
        default=st.session_state.sub_tab,
        selection_mode="single",
        format_func=lambda tab: f"{sub_icons[tab]} {tab}" + 
            (f" ({sub_badges[tab]})" if sub_badges.get(tab) else ""),
        label_visibility="collapsed",
        key=f"sub_pills_{st.session_state.main_tab}"  # creates class like st-key-sub_pills_Jobs
    )
    st.session_state.sub_tab = selected_sub
else:
    st.session_state.sub_tab = None

current_page = st.session_state.sub_tab if st.session_state.sub_tab else st.session_state.main_tab
if current_page == "Dashboard":
    st.markdown("## 📊 Overview")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="stat-card"><h3>📋 Applications</h3><p>{total_apps}</p></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="stat-card"><h3>🗓️ Interviews</h3><p>{interview_count}</p></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="stat-card"><h3>💬 Unread</h3><p>{unread_msgs}</p></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="stat-card"><h3>🔖 Saved</h3><p>{saved_count}</p></div>', unsafe_allow_html=True)

    if total_apps > 0:
        interview_rate = (interview_count / total_apps) * 100
        pending_rate = (pending_apps / total_apps) * 100
    else:
        interview_rate = pending_rate = 0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Interview Conversion</div>
            <div class="value">{interview_rate:.1f}%</div>
            <div class="delta">of all applications</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Pending Applications</div>
            <div class="value">{pending_apps}</div>
            <div class="delta">{pending_rate:.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        if applications:
            dates = [a[7] for a in applications if a[7]]
            if dates:
                earliest = min(dates).date()
                latest = max(dates).date()
                days_span = (latest - earliest).days or 1
                apps_per_day = total_apps / days_span
            else:
                apps_per_day = 0
        else:
            apps_per_day = 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Applications / Day</div>
            <div class="value">{apps_per_day:.1f}</div>
            <div class="delta">over active period</div>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        timeline = get_applications_over_time(user_id)
        if timeline:
            df = pd.DataFrame(timeline, columns=['date', 'count'])
            fig = px.line(df, x='date', y='count', title='📈 Applications Over Time',
                          markers=True, line_shape='linear')
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='var(--text)',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No application data yet.")
    with col2:
        stats = get_application_stats(user_id)
        if stats:
            df = pd.DataFrame(stats, columns=['status', 'count'])
            fig = px.pie(df, values='count', names='status', title='🥧 Application Status',
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='var(--text)',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data.")

    if applications:
        company_counts = {}
        for app in applications:
            company_name = app[10]
            company_counts[company_name] = company_counts.get(company_name, 0) + 1
        df = pd.DataFrame(list(company_counts.items()), columns=['Company', 'Applications'])
        df = df.sort_values('Applications', ascending=True).tail(5)
        fig = px.bar(df, x='Applications', y='Company', orientation='h',
                     title='🏆 Top Companies by Applications',
                     color='Applications', color_continuous_scale='Blues')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='var(--text)',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)

elif current_page == "Find Jobs":
    if "apply_job_id" in st.session_state:
        # Apply for a specific job
        st.markdown("## 📝 Apply for Job")
        job_tuple = get_job_by_id(st.session_state.apply_job_id)
        if not job_tuple:
            st.error("Job not found")
            del st.session_state.apply_job_id
            del st.session_state.apply_job_title
            st.rerun()
        job = {
            'id': job_tuple[0],
            'company_id': job_tuple[1],
            'company_name': job_tuple[2],
            'title': job_tuple[3],
            'category': job_tuple[4],
            'description': job_tuple[5],
            'requirements': job_tuple[6],
            'location': job_tuple[7],
            'job_type': job_tuple[8],
            'salary_range': job_tuple[9],
            'experience_level': job_tuple[10],
            'skills_required': job_tuple[11],
            'status': job_tuple[12],
            'created_at': job_tuple[13],
            'deadline': job_tuple[14],
        }
        profile = get_or_create_profile(user_id)
        st.markdown(f"### {job['title']} at {job['company_name']}")
        with st.form("application_form"):
            match_score = calculate_match_score(job['skills_required'], profile[5])
            if match_score > 0:
                st.markdown(f"""
                <div style="margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>AI Match Score</span>
                        <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                    </div>
                    <div style="height:8px; background:#e2e8f0; border-radius:4px; width:100%;">
                        <div style="width:{match_score}%; height:8px; background:{'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'}; border-radius:4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            cover_letter = st.text_area("Cover Letter", height=200,
                                       placeholder="Write a brief cover letter...")
            if not profile[4]:
                st.warning("⚠️ Please upload your resume in Profile section before applying")
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button("✅ Submit Application")
            with col_b:
                if st.form_submit_button("❌ Cancel"):
                    del st.session_state.apply_job_id
                    del st.session_state.apply_job_title
                    st.rerun()
            if submitted:
                if not profile[4]:
                    st.error("Please upload your resume first")
                else:
                    add_application(job['id'], user_id, job['company_id'], match_score, cover_letter)
                    add_notification(user_id, "application", "Application Submitted",
                                   f"You applied for {job['title']} at {job['company_name']}")
                    send_email(
                        st.session_state.user_email,
                        "Application Submitted",
                        f"Hi {st.session_state.user_name},\n\nYour application for '{job['title']}' at {job['company_name']} has been received.\n\nWe'll notify you of any updates.\n\nThanks,\nAnvaya Team"
                    )
                    st.success("✅ Application submitted successfully!")
                    time.sleep(2)
                    del st.session_state.apply_job_id
                    del st.session_state.apply_job_title
                    st.rerun()
    else:
        st.markdown("## 🔍 Find Jobs")
        profile = get_or_create_profile(user_id)
        employee_skills = profile[5] if profile else ""
        jobs = search_jobs(user_id)
        def job_to_dict(job_tuple):
            return {
                'id': job_tuple[0],
                'company_id': job_tuple[1],
                'company_name': job_tuple[2],
                'company_name2': job_tuple[15],
                'logo': job_tuple[16],
                'title': job_tuple[3],
                'category': job_tuple[4],
                'description': job_tuple[5],
                'requirements': job_tuple[6],
                'location': job_tuple[7],
                'job_type': job_tuple[8],
                'salary_range': job_tuple[9],
                'experience_level': job_tuple[10],
                'skills_required': job_tuple[11],
                'status': job_tuple[12],
                'created_at': job_tuple[13],
                'deadline': job_tuple[14],
                'applied': job_tuple[17],
                'saved': job_tuple[18],
            }
        job_dicts = [job_to_dict(j) for j in jobs]
        with st.expander("🔎 Filters", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                search = st.text_input("Search jobs", placeholder="Title, skills...")
            with col2:
                job_types = st.multiselect("Job Type", ["Full-time", "Part-time", "Remote", "Hybrid", "Contract"])
            with col3:
                exp_levels = st.multiselect("Experience", ["Entry", "Junior", "Mid", "Senior", "Lead"])
            with col4:
                locations = list(set(j['location'] for j in job_dicts if j['location']))
                selected_locs = st.multiselect("Location", locations)
        filtered = job_dicts
        if search:
            filtered = [j for j in filtered if search.lower() in j['title'].lower() or search.lower() in j['description'].lower()]
        if job_types:
            filtered = [j for j in filtered if j['job_type'] in job_types]
        if exp_levels:
            filtered = [j for j in filtered if j['experience_level'] in exp_levels]
        if selected_locs:
            filtered = [j for j in filtered if j['location'] in selected_locs]
        for job in filtered:
            job['match_score'] = calculate_match_score(job['skills_required'], employee_skills)
        filtered.sort(key=lambda x: x['match_score'], reverse=True)
        st.markdown(f"### Found {len(filtered)} jobs")

        if "show_job_details" not in st.session_state:
            st.session_state.show_job_details = None

        for job in filtered:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    match_score = job['match_score']
                    st.markdown(f"""
                    <div class="job-card">
                        <h3>{job['title']}</h3>
                        <p style="color: var(--primary);">{job['company_name2']}</p>
                        <p>📍 {job['location']} | 💼 {job['job_type']} | 💰 {job['salary_range']}</p>
                        <p>{job['description'][:200]}...</p>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                            <span style="background:#DBEAFE; padding:0.2rem 0.8rem; border-radius:40px; font-size:0.8rem;">{job['category']}</span>
                            <span style="background:#FEF3C7; padding:0.2rem 0.8rem; border-radius:40px; font-size:0.8rem;">{job['experience_level']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if match_score > 0:
                        st.markdown(f"""
                        <div style="margin: 0.5rem 0;">
                            <div style="display: flex; justify-content: space-between;">
                                <span>AI Match Score</span>
                                <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                            </div>
                            <div style="height:8px; background:#e2e8f0; border-radius:4px; width:100%;">
                                <div style="width:{match_score}%; height:8px; background:{'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'}; border-radius:4px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                with col2:
                    if job['applied'] == 0:
                        if st.button("📝 Apply Now", key=f"apply_{job['id']}"):
                            st.session_state.apply_job_id = job['id']
                            st.session_state.apply_job_title = job['title']
                            st.rerun()
                    else:
                        st.success("✅ Applied")
                    if job['saved'] == 0:
                        if st.button("🔖 Save", key=f"save_{job['id']}"):
                            save_job(user_id, job['id'])
                            add_notification(user_id, "save", "Job Saved",
                                           f"You saved {job['title']}")
                            st.rerun()
                    else:
                        if st.button("📌 Saved", key=f"unsave_{job['id']}"):
                            unsave_job(user_id, job['id'])
                            st.rerun()
                    if st.button("📋 View Details", key=f"details_{job['id']}"):
                        if st.session_state.show_job_details == job['id']:
                            st.session_state.show_job_details = None
                        else:
                            st.session_state.show_job_details = job['id']
                        st.rerun()

                if st.session_state.show_job_details == job['id']:
                    with st.expander("Job Details", expanded=True):
                        st.markdown(f"**Description:**\n{job['description']}")
                        st.markdown(f"**Requirements:**\n{job['requirements']}")
                        st.markdown(f"**Skills Required:** {job['skills_required']}")
                        st.markdown(f"**Category:** {job['category']}")
                        st.markdown(f"**Experience Level:** {job['experience_level']}")
                        st.markdown(f"**Job Type:** {job['job_type']}")
                        st.markdown(f"**Location:** {job['location']}")
                        st.markdown(f"**Salary Range:** {job['salary_range']}")
                        deadline_str = job['deadline'].strftime('%Y-%m-%d') if job['deadline'] else 'Not specified'
                        st.markdown(f"**Application Deadline:** {deadline_str}")
                        posted_str = job['created_at'].strftime('%Y-%m-%d') if job['created_at'] else ''
                        st.markdown(f"**Posted on:** {posted_str}")
                        if st.button("Close", key=f"close_details_{job['id']}"):
                            st.session_state.show_job_details = None
                            st.rerun()
                st.markdown("---")

elif current_page == "Companies":
    st.markdown("## 🏢 Recruiting Companies")
    if "apply_job_id" in st.session_state:
        # Apply flow (same as above)
        st.markdown("## 📝 Apply for Job")
        job_tuple = get_job_by_id(st.session_state.apply_job_id)
        if not job_tuple:
            st.error("Job not found")
            del st.session_state.apply_job_id
            del st.session_state.apply_job_title
            st.rerun()
        job = {
            'id': job_tuple[0],
            'company_id': job_tuple[1],
            'company_name': job_tuple[2],
            'title': job_tuple[3],
            'category': job_tuple[4],
            'description': job_tuple[5],
            'requirements': job_tuple[6],
            'location': job_tuple[7],
            'job_type': job_tuple[8],
            'salary_range': job_tuple[9],
            'experience_level': job_tuple[10],
            'skills_required': job_tuple[11],
            'status': job_tuple[12],
            'created_at': job_tuple[13],
            'deadline': job_tuple[14],
        }
        profile = get_or_create_profile(user_id)
        st.markdown(f"### {job['title']} at {job['company_name']}")
        with st.form("application_form"):
            match_score = calculate_match_score(job['skills_required'], profile[5])
            if match_score > 0:
                st.markdown(f"""
                <div style="margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>AI Match Score</span>
                        <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                    </div>
                    <div style="height:8px; background:#e2e8f0; border-radius:4px; width:100%;">
                        <div style="width:{match_score}%; height:8px; background:{'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'}; border-radius:4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            cover_letter = st.text_area("Cover Letter", height=200,
                                       placeholder="Write a brief cover letter...")
            if not profile[4]:
                st.warning("⚠️ Please upload your resume in Profile section before applying")
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button("✅ Submit Application", use_container_width=True)
            with col_b:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    del st.session_state.apply_job_id
                    del st.session_state.apply_job_title
                    st.rerun()
            if submitted:
                if not profile[4]:
                    st.error("Please upload your resume first")
                else:
                    add_application(job['id'], user_id, job['company_id'], match_score, cover_letter)
                    add_notification(user_id, "application", "Application Submitted",
                                   f"You applied for {job['title']} at {job['company_name']}")
                    send_email(
                        st.session_state.user_email,
                        "Application Submitted",
                        f"Hi {st.session_state.user_name},\n\nYour application for '{job['title']}' at {job['company_name']} has been received.\n\nWe'll notify you of any updates.\n\nThanks,\nAnvaya Team"
                    )
                    st.success("✅ Application submitted successfully!")
                    time.sleep(2)
                    del st.session_state.apply_job_id
                    del st.session_state.apply_job_title
                    st.rerun()
    elif "selected_company" in st.session_state:
        # Show jobs for selected company
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📋 Jobs at {st.session_state.selected_company_name}")
        with col2:
            if st.button("← Back to Companies"):
                del st.session_state.selected_company
                del st.session_state.selected_company_name
                st.rerun()

        jobs = get_company_jobs(st.session_state.selected_company, user_id)
        if jobs:
            for job in jobs:
                # job tuple: ... + applied at index 15
                job_dict = {
                    'id': job[0],
                    'title': job[3],
                    'location': job[7],
                    'job_type': job[8],
                    'salary_range': job[9],
                    'description': job[5],
                    'requirements': job[6],
                    'category': job[4],
                    'experience_level': job[10],
                    'skills_required': job[11],
                    'deadline': job[14],
                    'created_at': job[13],
                    'applied': job[15],
                }
                st.markdown(f"""
                <div class="job-card">
                    <h3>{job_dict['title']}</h3>
                    <p>📍 {job_dict['location']} | 💼 {job_dict['job_type']} | 💰 {job_dict['salary_range']}</p>
                    <p>{job_dict['description'][:150]}...</p>
                </div>
                """, unsafe_allow_html=True)
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if job_dict['applied'] == 0:
                        if st.button(f"📝 Apply Now", key=f"apply_comp_{job[0]}"):
                            st.session_state.apply_job_id = job[0]
                            st.session_state.apply_job_title = job_dict['title']
                            st.rerun()
                    else:
                        st.info("✅ Already applied")
                with col_b:
                    # View Details button
                    if st.button("📋 View Details", key=f"details_comp_{job[0]}"):
                        if st.session_state.get("show_job_details_comp") == job[0]:
                            st.session_state.show_job_details_comp = None
                        else:
                            st.session_state.show_job_details_comp = job[0]
                        st.rerun()
                with col_c:
                    # Save button
                    if job_dict.get('saved', 0) == 0:
                        if st.button("🔖 Save", key=f"save_comp_{job[0]}"):
                            save_job(user_id, job[0])
                            add_notification(user_id, "save", "Job Saved",
                                           f"You saved {job_dict['title']}")
                            st.rerun()
                    else:
                        if st.button("📌 Saved", key=f"unsave_comp_{job[0]}"):
                            unsave_job(user_id, job[0])
                            st.rerun()

                # Expanded job details
                if st.session_state.get("show_job_details_comp") == job[0]:
                    with st.expander("Job Details", expanded=True):
                        st.markdown(f"**Description:**\n{job_dict['description']}")
                        st.markdown(f"**Requirements:**\n{job_dict['requirements']}")
                        st.markdown(f"**Skills Required:** {job_dict['skills_required']}")
                        st.markdown(f"**Category:** {job_dict['category']}")
                        st.markdown(f"**Experience Level:** {job_dict['experience_level']}")
                        st.markdown(f"**Job Type:** {job_dict['job_type']}")
                        st.markdown(f"**Location:** {job_dict['location']}")
                        st.markdown(f"**Salary Range:** {job_dict['salary_range']}")
                        deadline_str = job_dict['deadline'].strftime('%Y-%m-%d') if job_dict['deadline'] else 'Not specified'
                        st.markdown(f"**Application Deadline:** {deadline_str}")
                        posted_str = job_dict['created_at'].strftime('%Y-%m-%d') if job_dict['created_at'] else ''
                        st.markdown(f"**Posted on:** {posted_str}")
                        if st.button("Close", key=f"close_comp_details_{job[0]}"):
                            st.session_state.show_job_details_comp = None
                            st.rerun()
                st.markdown("---")
        else:
            st.info("No active jobs from this company.")
    else:
        # List all companies
        companies = get_all_companies()
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 Search companies", placeholder="Search by name or industry...")
        with col2:
            industries = list(set(c[5] for c in companies if c[5]))
            industry_filter = st.selectbox("Industry", ["All"] + industries)
        filtered = companies
        if search:
            filtered = [c for c in filtered if search.lower() in c[1].lower() or search.lower() in (c[5] or "").lower()]
        if industry_filter != "All":
            filtered = [c for c in filtered if c[5] == industry_filter]
        cols = st.columns(3)
        for idx, company in enumerate(filtered):
            with cols[idx % 3]:
                logo_text = company[1][0].upper() if company[1] else "C"
                st.markdown(f"""
                <div class="company-card" style="text-align:center;">
                    <div style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, var(--primary), var(--secondary)); color:white; font-size:2rem; font-weight:bold; display:flex; align-items:center; justify-content:center; margin:0 auto 1rem;">{logo_text}</div>
                    <h4>{company[1]}</h4>
                    <p style="color: var(--text-light);">{company[5] or 'Technology'}</p>
                    <p style="font-size: 0.9rem;">📍 {company[6] or 'Remote'}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"View Jobs", key=f"view_{company[0]}"):
                    st.session_state.selected_company = company[0]
                    st.session_state.selected_company_name = company[1]
                    st.rerun()

elif current_page == "Saved Jobs":
    st.markdown("## 🔖 Saved Jobs")
    saved = get_saved_jobs(user_id)
    if not saved:
        st.info("No saved jobs yet.")
    else:
        for job in saved:
            job_dict = {
                'id': job[0],
                'company_id': job[1],
                'company_name_jobs': job[2],
                'title': job[3],
                'category': job[4],
                'description': job[5],
                'requirements': job[6],
                'location': job[7],
                'job_type': job[8],
                'salary_range': job[9],
                'experience_level': job[10],
                'skills_required': job[11],
                'status': job[12],
                'created_at': job[13],
                'deadline': job[14],
                'company_name': job[15],
                'applied': job[16],
            }
            st.markdown(f"""
            <div class="job-card">
                <h3>{job_dict['title']}</h3>
                <p style="color: var(--primary);">{job_dict['company_name']}</p>
                <p>📍 {job_dict['location']} | 💼 {job_dict['job_type']} | 💰 {job_dict['salary_range']}</p>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if job_dict['applied'] == 0:
                    if st.button("📝 Apply", key=f"apply_saved_{job_dict['id']}"):
                        st.session_state.apply_job_id = job_dict['id']
                        st.session_state.apply_job_title = job_dict['title']
                        st.rerun()
                else:
                    st.info("✅ Applied")
            with col2:
                if st.button("❌ Remove", key=f"remove_saved_{job_dict['id']}"):
                    unsave_job(user_id, job_dict['id'])
                    st.rerun()
            st.markdown("---")

elif current_page == "My Applications":
    st.markdown("## 📋 My Applications")
    applications = get_user_applications(user_id)
    if not applications:
        st.info("You haven't applied to any jobs yet.")
    else:
        statuses = ["All", "Pending", "Reviewed", "Interview", "Accepted", "Rejected"]
        selected_status = st.selectbox("Filter by status", statuses)
        filtered = applications if selected_status == "All" else [a for a in applications if a[4].capitalize() == selected_status]
        for i, app in enumerate(filtered):
            status_color = {
                "pending": "warning",
                "reviewed": "info",
                "interview": "success",
                "accepted": "success",
                "rejected": "danger"
            }.get(app[4], "info")
            applied_at_str = app[7].strftime('%Y-%m-%d') if app[7] else ''
            st.markdown(f"""
            <div class="job-card">
                <h3>{app[9]}</h3>
                <p style="color: var(--primary);">{app[10]}</p>
                <p>📍 {app[11]} | 💰 {app[12]}</p>
                <p><strong>Applied:</strong> {applied_at_str}</p>
                <p><strong>Status:</strong> <span style="background:{ '#10B98120' if app[4]=='accepted' else '#F59E0B20' if app[4]=='interview' else '#EF444420' if app[4]=='rejected' else '#3B82F620' }; color:{ '#10B981' if app[4]=='accepted' else '#F59E0B' if app[4]=='interview' else '#EF4444' if app[4]=='rejected' else '#3B82F6' }; padding:0.2rem 1rem; border-radius:40px;">{app[4].upper()}</span></p>
            """, unsafe_allow_html=True)
            if app[14] == "scheduled":  # interview_status
                st.markdown(f"""
                <div style="background: #3B82F620; padding: 1rem; border-radius: 16px; margin: 0.5rem 0;">
                    <h4>🗓️ Interview Scheduled</h4>
                    <p><strong>Date:</strong> {app[13]}</p>
                    <p><strong>Meeting Link:</strong> <a href="{app[15]}" target="_blank">{app[15]}</a></p>
                </div>
                """, unsafe_allow_html=True)
            if st.button("📋 Details", key=f"details_{app[0]}_{i}"):
                st.session_state.show_details_for = app[0]
                st.rerun()
            if st.session_state.get("show_details_for") == app[0]:
                with st.expander("Application Details", expanded=True):
                    st.markdown(f"**Cover Letter:** {app[6]}")
                if st.button("Close", key=f"close_{app[0]}"):
                    del st.session_state.show_details_for
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

elif current_page == "Job Requests":
    st.markdown("## 📝 My Job Requests")
    if "job_request_tab" not in st.session_state:
        st.session_state.job_request_tab = "My Requests"
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 My Requests", use_container_width=True,
                     type="primary" if st.session_state.job_request_tab == "My Requests" else "secondary"):
            st.session_state.job_request_tab = "My Requests"
            st.rerun()
    with col2:
        if st.button("📝 Post a New Request", use_container_width=True,
                     type="primary" if st.session_state.job_request_tab == "Post a New Request" else "secondary"):
            st.session_state.job_request_tab = "Post a New Request"
            st.rerun()
    st.markdown("---")
    if st.session_state.job_request_tab == "My Requests":
        my_requests = get_user_requests(user_id)
        if not my_requests:
            st.info("You haven't posted any job requests yet.")
        else:
            for req in my_requests:
                with st.expander(f"{req[2]} ({req[7].upper()}) - {req[5]}"):
                    st.markdown(f"**Description:** {req[3]}")
                    st.markdown(f"**Category:** {req[4]}")
                    st.markdown(f"**Location:** {req[5]}")
                    st.markdown(f"**Budget:** {req[6]}")
                    posted_at_str = req[8].strftime('%Y-%m-%d') if req[8] else ''
                    st.markdown(f"**Posted on:** {posted_at_str}")
                    col1, col2, col3 = st.columns([1,1,2])
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{req[0]}"):
                            st.session_state.edit_request_id = req[0]
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{req[0]}"):
                            delete_job_request(req[0])
                            add_notification(user_id, "request", "Request Deleted",
                                           f"Your request '{req[2]}' has been deleted.")
                            st.rerun()
                    with col3:
                        new_status = "closed" if req[7] == "open" else "open"
                        btn_label = "🔒 Close" if req[7] == "open" else "🔓 Reopen"
                        if st.button(btn_label, key=f"status_{req[0]}"):
                            update_job_request(req[0], req[2], req[3], req[4], req[5], req[6], new_status)
                            st.rerun()
            if "edit_request_id" in st.session_state:
                st.markdown("---")
                st.markdown("### Edit Request")
                req_id = st.session_state.edit_request_id
                req_to_edit = next((r for r in my_requests if r[0] == req_id), None)
                if req_to_edit:
                    with st.form("edit_request_form"):
                        title = st.text_input("Title", value=req_to_edit[2])
                        description = st.text_area("Description", value=req_to_edit[3], height=150)
                        category = st.selectbox("Category", ["Technology", "Data Science", "Design", "Marketing", "Sales", "Other"],
                                                index=["Technology", "Data Science", "Design", "Marketing", "Sales", "Other"].index(req_to_edit[4]) if req_to_edit[4] in ["Technology", "Data Science", "Design", "Marketing", "Sales", "Other"] else 0)
                        location = st.text_input("Location", value=req_to_edit[5])
                        budget = st.text_input("Expected compensation", value=req_to_edit[6])
                        status = st.selectbox("Status", ["open", "closed"], index=0 if req_to_edit[7]=="open" else 1)
                        col_a, col_b = st.columns(2)
                        with col_a:
                            submitted = st.form_submit_button("💾 Update Request")
                        with col_b:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state.edit_request_id
                                st.rerun()
                        if submitted:
                            update_job_request(req_id, title, description, category, location, budget, status)
                            add_notification(user_id, "request", "Request Updated",
                                           f"Your request '{title}' has been updated.")
                            del st.session_state.edit_request_id
                            st.rerun()
                else:
                    st.error("Request not found")
                    if st.button("Back"):
                        del st.session_state.edit_request_id
                        st.rerun()
    else:
        st.markdown("### Post a New Job Request")
        with st.form("post_request_form", clear_on_submit=True):
            title = st.text_input("What kind of job are you looking for?")
            description = st.text_area("Describe your skills, experience, and what you're looking for", height=150)
            category = st.selectbox("Category", ["Technology", "Data Science", "Design", "Marketing", "Sales", "Other"])
            location = st.text_input("Location (or 'Remote')")
            budget = st.text_input("Expected compensation (e.g., '$80k/year' or 'Negotiable')")
            submitted = st.form_submit_button("Post Request")
            if submitted and title:
                add_job_request(user_id, title, description, category, location, budget)
                add_notification(user_id, "request", "Request Posted",
                               f"Your request '{title}' has been posted.")
                send_email(
                    st.session_state.user_email,
                    "Job Request Posted",
                    f"Your request '{title}' has been posted successfully.\n\nEmployers will be able to see it"
                )
                st.success("Request posted!")
                st.session_state.job_request_tab = "My Requests"
                st.rerun()

elif current_page == "Messages":
    st.markdown("## 💬 Messages")
    conversations = get_conversations(user_id)
    if not conversations:
        st.info("No messages yet.")
    else:
        for i, conv in enumerate(conversations):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                last_time_str = conv[8].strftime('%Y-%m-%d %H:%M') if conv[8] else ''
                st.markdown(f"""
                <div class="job-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <h4>{conv[5]}</h4>
                            <p style="color: var(--text-light);">{conv[6]}</p>
                            <p style="font-size: 0.9rem;">{conv[7][:100] if conv[7] else 'No messages'}...</p>
                            <p style="font-size:0.7rem; color:var(--text-light);">{last_time_str}</p>
                        </div>
                        {f'<span style="background:#EF4444; color:white; padding:0.2rem 0.6rem; border-radius:40px; font-size:0.7rem; align-self:center;">{conv[9]} new</span>' if conv[9] > 0 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                # empty
                pass
            with col3:
                if st.button("Open Chat", key=f"open_chat_{conv[4]}_{i}"):
                    st.session_state.chat_company_id = conv[4]
                    st.session_state.chat_company_name = conv[5]
                    st.rerun()
        if "chat_company_id" in st.session_state:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=10000, key="chat_autorefresh")
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### 💬 Chat with {st.session_state.chat_company_name}")
            with col2:
                if st.button("Close Chat"):
                    del st.session_state.chat_company_id
                    del st.session_state.chat_company_name
                    st.rerun()
            messages = get_messages(user_id, st.session_state.chat_company_id)
            mark_messages_read(user_id, st.session_state.chat_company_id)
            st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
            for msg in messages:
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                if msg[2] == "employee":
                    st.markdown(f"""
                    <div style="text-align: right; margin: 0.5rem 0;">
                        <div class="chat-bubble-employee">{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="text-align: left; margin: 0.5rem 0;">
                        <div class="chat-bubble-company"><strong>{st.session_state.chat_company_name}</strong><br>{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("""
            <script>
                var chatContainer = document.getElementById('chat-container');
                if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
            </script>
            """, unsafe_allow_html=True)
            message = st.text_area("Type your message", height=100, key="chat_message_input")
            if st.button("📤 Send", key="send_message_btn"):
                if message:
                    try:
                        send_message(user_id, "employee",
                                st.session_state.chat_company_id, "company",
                                message, application_id=None)
                        st.success("Message sent!")
                        st.session_state["chat_message_input"] = ""
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to send message: {e}")
                else:
                    st.warning("Please enter a message.")

elif current_page == "Notifications":
    st.markdown("## 🔔 All Notifications")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Mark all as read", use_container_width=True):
            mark_notifications_read(user_id)
            st.rerun()
    
    all_notifications = get_user_notifications(user_id, limit=50)
    
    if not all_notifications:
        st.info("No notifications yet.")
    else:
        for notif in all_notifications:
            icon = "📝" if notif[2] == 'application' else "💬" if notif[2] == 'message' else "🔔"
            bg = "#DCFCE7" if notif[2] == 'application' else "#DBEAFE" if notif[2] == 'message' else "#FEF3C7"
            time_str = notif[7].strftime('%Y-%m-%d %H:%M') if notif[7] else ''
            is_read = notif[6]  # assuming is_read is at index 6
            opacity = "1" if not is_read else "0.7"
            st.markdown(f"""
            <div class="notification-card" style="opacity: {opacity};">
                <div class="notification-icon" style="background: {bg};">{icon}</div>
                <div class="notification-title">{notif[3]}</div>
                <div class="notification-content">{notif[4]}</div>
                <div class="notification-time">{time_str}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")


elif current_page == "Profile":
    st.markdown("## 👤 My Profile")
    user = get_user_by_id(user_id)
    profile = get_or_create_profile(user_id)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="width:120px; height:120px; border-radius:50%; background:linear-gradient(135deg, var(--primary), #3B82F6); display:flex; align-items:center; justify-content:center; color:white; font-size:3rem; font-weight:bold; margin:0 auto 1rem;">{user[1][0].upper() if user[1] else 'U'}</div>
            <h3>{user[1]}</h3>
            <p>📧 {user[2]}</p>
            {f'<p>📱 {profile[1]}</p>' if profile[1] else ''}
            {f'<p>📍 {profile[2]}</p>' if profile[2] else ''}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### 📄 Resume/CV")
        if profile[4]:
            st.markdown(get_resume_download_link(profile[4], "📥 Download Current Resume"), unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload New Resume (PDF)", type=['pdf'])
        if uploaded_file:
            resume_dir = "resumes"
            os.makedirs(resume_dir, exist_ok=True)
            resume_path = os.path.join(resume_dir, f"{user[2]}_{uploaded_file.name}")
            with open(resume_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            update_profile(user_id, resume_path=resume_path)
            st.success("Resume uploaded!")
            st.rerun()
        st.markdown("---")
        st.markdown("#### 🌐 Social Links")
        if profile[10]: st.markdown(f"[LinkedIn]({profile[10]})")
        if profile[11]: st.markdown(f"[GitHub]({profile[11]})")
        if profile[12]: st.markdown(f"[Portfolio]({profile[12]})")

        # --- New: Change Password Section ---
        st.markdown("---")
        st.markdown("#### 🔐 Change Password")
        if "password_change_step" not in st.session_state:
            st.session_state.password_change_step = 1  # 1: request OTP, 2: verify, 3: new password
            st.session_state.otp = None
            st.session_state.otp_sent = False

        if st.session_state.password_change_step == 1:
            if st.button("Send Verification Code"):
                otp = generate_otp()
                st.session_state.otp = otp
                if send_otp_email(st.session_state.user_email, otp):
                    st.success("OTP sent to your email. Please check your inbox.")
                    st.session_state.password_change_step = 2
                    st.rerun()
                else:
                    st.error("Failed to send OTP. Try again later.")
        elif st.session_state.password_change_step == 2:
            otp_input = st.text_input("Enter 6-digit OTP", max_chars=6)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Verify OTP"):
                    if otp_input == st.session_state.otp:
                        st.success("OTP verified. Now set your new password.")
                        st.session_state.password_change_step = 3
                        st.rerun()
                    else:
                        st.error("Invalid OTP. Please try again.")
            with col_b:
                if st.button("Cancel"):
                    st.session_state.password_change_step = 1
                    st.session_state.otp = None
                    st.rerun()
        elif st.session_state.password_change_step == 3:
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Update Password"):
                    if new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    elif len(new_pass) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        new_pass_hash = hash_password(new_pass)
                        update_user_password(st.session_state.user_id, new_pass_hash)
                        st.success("Password updated successfully!")
                        st.session_state.password_change_step = 1
                        time.sleep(2)
                        st.session_state.otp = None
                        st.rerun()
            with col_b:
                if st.button("Cancel"):
                    st.session_state.password_change_step = 1
                    st.session_state.otp = None
                    st.rerun()

    with col2:
        with st.form("profile_edit_form"):
            st.markdown("#### ✏️ Edit Profile")
            col_a, col_b = st.columns(2)
            with col_a:
                name = st.text_input("Full Name", value=user[1] or "")
                phone = st.text_input("Phone", value=profile[1] or "")
                location = st.text_input("Location", value=profile[2] or "")
            with col_b:
                exp_levels = ["Entry", "Junior", "Mid", "Senior", "Lead"]
                exp_index = exp_levels.index(profile[6]) if profile[6] in exp_levels else 0
                experience = st.selectbox("Experience Level", exp_levels, index=exp_index)
                job_types = ["Full-time", "Part-time", "Remote", "Hybrid", "Contract"]
                pref_index = job_types.index(profile[7]) if profile[7] in job_types else 0
                job_type = st.selectbox("Preferred Job Type", job_types, index=pref_index)
                salary = st.text_input("Expected Salary", value=profile[8] or "")
            skills = st.text_area("Skills (comma separated)", value=profile[5] or "")
            bio = st.text_area("Bio/Summary", value=profile[9] or "", height=100)
            st.markdown("#### Social Links")
            col_c, col_d = st.columns(2)
            with col_c:
                linkedin = st.text_input("LinkedIn URL", value=profile[10] or "")
                github = st.text_input("GitHub URL", value=profile[11] or "")
            with col_d:
                portfolio = st.text_input("Portfolio URL", value=profile[12] or "")
            submitted = st.form_submit_button("💾 Save Changes")
            if submitted:
                update_user_name(user_id, name)
                update_profile(user_id,
                               phone=phone, location=location, experience_level=experience,
                               preferred_job_type=job_type, expected_salary=salary, skills=skills,
                               bio=bio, linkedin_url=linkedin, github_url=github, portfolio_url=portfolio)
                st.success("Profile updated!")
                st.rerun()

    # --- Logout and Admin buttons (text links) ---
    st.markdown("---")
    col_logout, col_admin = st.columns(2)
    with col_logout:
        if st.button("🚪 Logout", type="secondary"):
            for key in ['authenticated', 'user_id', 'user_name', 'user_email', 'main_tab', 'sub_tab', 'reg_face', 'verify_img']:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")
    with col_admin:
        if st.session_state.get("is_admin", False):
            if st.button("🛡️ Admin Panel", type="secondary"):
                st.session_state.previous_page = "pages/employee_dashboard.py"
                st.switch_page("pages/admin_dashboard.py")

elif current_page == "Analytics":
    st.markdown("## 📊 My Analytics")
    stats = get_application_stats(user_id)
    timeline = get_applications_over_time(user_id)
    interview_count = get_interview_count(user_id)
    total = sum(s[1] for s in stats)
    pending = next((s[1] for s in stats if s[0] == 'pending'), 0)
    accepted = next((s[1] for s in stats if s[0] == 'accepted'), 0)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>Total Applications</h3><p>{total}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>Pending</h3><p style="color:#F59E0B;">{pending}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>Interviews</h3><p style="color:#3B82F6;">{interview_count}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>Accepted</h3><p style="color:#10B981;">{accepted}</p></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if stats:
            df = pd.DataFrame(stats, columns=['status', 'count'])
            fig = px.pie(df, values='count', names='status', title='Application Status',
                        color_discrete_sequence=['#10B981', '#F59E0B', '#3B82F6', '#EF4444'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='var(--text)')
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if timeline:
            df = pd.DataFrame(timeline, columns=['date', 'count'])
            fig = px.line(df, x='date', y='count', title='Applications Over Time', markers=True)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='var(--text)')
            st.plotly_chart(fig, use_container_width=True)
    if total > 0:
        success_rate = (accepted / total) * 100
        st.markdown(f"""
        <div class="stat-card" style="text-align: center;">
            <h3>Success Rate</h3>
            <p style="font-size: 3rem; font-weight: 600; color: var(--primary);">{success_rate:.1f}%</p>
            <div style="height:8px; background:#e2e8f0; border-radius:4px; width:100%;">
                <div style="width:{success_rate}%; height:8px; background:var(--primary); border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


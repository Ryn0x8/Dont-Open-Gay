import streamlit as st
import pandas as pd
import numpy as np
import os
import base64
import time
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu
from auth_utils import send_email  
from database import (
    get_user_by_id, get_or_create_profile, update_profile,
    update_user_name, get_all_companies, get_company_jobs, search_jobs, get_job_by_id,
    add_application, get_user_applications, save_job, unsave_job, get_saved_jobs,
    add_notification, get_user_notifications, mark_notifications_read,
    add_job_request, get_user_requests,
    get_conversations, get_messages, send_message, mark_messages_read,
    get_application_stats, get_applications_over_time, get_interview_count,
    delete_job_request, update_job_request
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

def calculate_match_score(job_skills, employee_skills):
    if not job_skills or not employee_skills:
        return 0
    job_set = set(s.strip().lower() for s in job_skills.split(','))
    emp_set = set(s.strip().lower() for s in employee_skills.split(','))
    if not job_set:
        return 0
    matches = len(job_set & emp_set)
    return int((matches / len(job_set)) * 100)

def get_resume_download_link(resume_path, text="Download Resume"):
    if resume_path and os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(resume_path)}" class="badge badge-info">{text}</a>'
        return href
    return None

# --- Custom CSS (same as before, keep it) ---
st.markdown("""
<style>
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
    .request-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
        transition: all 0.3s;
    }
    .request-card:hover {
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-color: var(--primary);
    }
    .badge-open { background: #10B98120; color: #10B981; }
    .badge-assigned { background: #F59E0B20; color: #F59E0B; }
    .badge-completed { background: #64748B20; color: #64748B; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(f"""
<div class="dashboard-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1>👋 Welcome, {st.session_state.user_name}!</h1>
            <p>Your personalized employee dashboard</p>
        </div>
        <div style="text-align: right;">
            <p style="margin: 0; opacity: 0.9;">{datetime.now().strftime('%B %d, %Y')}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Find Jobs", "Companies", "My Applications", "Job Requests", "Messages", "Saved Jobs", "Profile", "Analytics"],
    icons=["house", "search", "building", "file-text", "clipboard", "chat", "bookmark", "person", "graph-up"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "white", "border-radius": "12px", "margin-bottom": "2rem"},
        "icon": {"color": "var(--primary)", "font-size": "1.2rem"},
        "nav-link": {"font-size": "1rem", "text-align": "center", "margin": "0", "padding": "0.75rem"},
        "nav-link-selected": {"background-color": "var(--primary)", "color": "white"},
    }
)

def profile_section():
    st.markdown("<h2>👤 My Profile</h2>", unsafe_allow_html=True)

    user_id = st.session_state.user_id
    user = get_user_by_id(user_id)
    profile = get_or_create_profile(user_id)

    col1, col2 = st.columns([1, 2])

    with col1:
        # Avatar
        st.markdown(f"""
            <div style="display:flex; justify-content:center; align-items:center;">
                <div style="
                    width:120px;
                    height:120px;
                    border-radius:50%;
                    background:linear-gradient(135deg, #2563EB, #14B8A6);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    color:white;
                    font-size:3rem;
                    font-weight:bold;">
                    {user[1][0].upper() if user[1] else 'U'}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"### {user[1]}")
        st.markdown(f"📧 {user[2]}")
        if profile[1]:  # phone
            st.markdown(f"📱 {profile[1]}")
        if profile[2]:  # location
            st.markdown(f"📍 {profile[2]}")

        st.markdown("---")
        st.markdown("#### 📄 Resume/CV")
        if profile[4]:  # resume_path
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
        # Correct indices: linkedin = 10, github = 11, portfolio = 12
        if profile[10] and profile[10].strip():
            st.markdown(f"[LinkedIn]({profile[10]})")
        if profile[11] and profile[11].strip():
            st.markdown(f"[GitHub]({profile[11]})")
        if profile[12] and profile[12].strip():
            st.markdown(f"[Portfolio]({profile[12]})")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ['authenticated', 'user_id', 'user_name', 'user_email']:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")

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
                # profile[6] is experience_level
                exp_index = exp_levels.index(profile[6]) if profile[6] in exp_levels else 0
                experience = st.selectbox("Experience Level", exp_levels, index=exp_index)
                job_types = ["Full-time", "Part-time", "Remote", "Hybrid", "Contract"]
                # profile[7] is preferred_job_type
                pref_index = job_types.index(profile[7]) if profile[7] in job_types else 0
                job_type = st.selectbox("Preferred Job Type", job_types, index=pref_index)
                salary = st.text_input("Expected Salary", value=profile[8] or "")

            # profile[5] is skills
            skills = st.text_area("Skills (comma separated)", value=profile[5] or "")
            # profile[9] is bio
            bio = st.text_area("Bio/Summary", value=profile[9] or "", height=100)

            st.markdown("#### Social Links")
            col_c, col_d = st.columns(2)
            with col_c:
                linkedin = st.text_input("LinkedIn URL", value=profile[10] or "")
                github = st.text_input("GitHub URL", value=profile[11] or "")
            with col_d:
                portfolio = st.text_input("Portfolio URL", value=profile[12] or "")

            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if submitted:
                update_user_name(user_id, name)
                update_profile(user_id,
                               phone=phone, location=location, experience_level=experience,
                               preferred_job_type=job_type, expected_salary=salary, skills=skills,
                               bio=bio, linkedin_url=linkedin, github_url=github, portfolio_url=portfolio)
                st.success("Profile updated!")
                st.rerun()


def companies_section():
    st.markdown("<h2>🏢 Recruiting Companies</h2>", unsafe_allow_html=True)

    # If we are in the middle of applying, show the apply form
    if "apply_job_id" in st.session_state:
        # Fetch the job details
        job = get_job_by_id(st.session_state.apply_job_id)
        if job:
            # Convert to dict for clarity (jobs.* columns only)
            job_dict = {
                'id': job[0],
                'company_id': job[1],
                'company_name': job[2],
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
            }
            # Display apply form (similar to apply_job_section but without the column layout)
            st.markdown(f"### Apply for: {job_dict['title']}")
            profile = get_or_create_profile(st.session_state.user_id)

            with st.form("inline_application_form"):
                match_score = calculate_match_score(job_dict['skills_required'], profile[5])
                if match_score > 0:
                    st.markdown(f"""
                    <div style="margin: 1rem 0;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>AI Match Score</span>
                            <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                        </div>
                        <div class="match-score" style="width: {match_score}%;"></div>
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
                        add_application(job_dict['id'], st.session_state.user_id, job_dict['company_id'], match_score, cover_letter)
                        add_notification(st.session_state.user_id, "application", "Application Submitted",
                                       f"You applied for {job_dict['title']} at {job_dict['company_name']}")
                        send_email(
                            st.session_state.user_email,
                            "Application Submitted",
                            f"Hi {st.session_state.user_name},\n\nYour application for '{job_dict['title']}' at {job_dict['company_name']} has been received.\n\nWe'll notify you of any updates.\n\nThanks,\nAnvaya Team"
                        )
                        st.success("✅ Application submitted successfully!")
                        time.sleep(2)
                        del st.session_state.apply_job_id
                        del st.session_state.apply_job_title
                        st.rerun()
        else:
            st.error("Job not found")
            if st.button("Back"):
                del st.session_state.apply_job_id
                del st.session_state.apply_job_title
                st.rerun()
        return 

    # Normal companies listing
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
            <div class="company-card">
                <div class="company-logo">{logo_text}</div>
                <h4>{company[1]}</h4>
                <p style="color: var(--text-secondary);">{company[5] or 'Technology'}</p>
                <p style="font-size: 0.9rem;">📍 {company[6] or 'Remote'}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"View Jobs", key=f"view_{company[0]}"):
                st.session_state.selected_company = company[0]
                st.session_state.selected_company_name = company[1]
                st.rerun()

    if "selected_company" in st.session_state:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📋 Jobs at {st.session_state.selected_company_name}")
        with col2:
            if st.button("← Back to Companies"):
                del st.session_state.selected_company
                del st.session_state.selected_company_name
                st.rerun()

        jobs = get_company_jobs(st.session_state.selected_company, st.session_state.user_id)
        if jobs:
            for job in jobs:
                # jobs.* (15 columns) + applied (1) = 16 columns → applied at index 15
                st.markdown(f"""
                <div class="job-card">
                    <h3>{job[3]}</h3>
                    <p>📍 {job[7]} | 💼 {job[8]} | 💰 {job[9]}</p>
                    <p>{job[5][:150]}...</p>
                </div>
                """, unsafe_allow_html=True)
                if job[15] == 0:  # applied flag
                    if st.button(f"📝 Apply Now", key=f"apply_{job[0]}"):
                        st.session_state.apply_job_id = job[0]
                        st.session_state.apply_job_title = job[3]
                        st.rerun()
                else:
                    st.info("✅ Already applied")
        else:
            st.info("No active jobs from this company.")

# --- Job Search Section ---
def job_search_section():
    st.markdown("<h2>🔍 Find Jobs</h2>", unsafe_allow_html=True)

    profile = get_or_create_profile(st.session_state.user_id)
    employee_skills = profile[5] if profile else ""

    jobs = search_jobs(st.session_state.user_id)  # returns tuples with many columns

    # Convert each job tuple to a dict with meaningful keys
    def job_to_dict(job_tuple):
        return {
            'id': job_tuple[0],
            'company_id': job_tuple[1],
            'company_name': job_tuple[2],          # from jobs table (original)
            'company_name2': job_tuple[15],        # from companies table (prefer this one)
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

    # Filters
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

    for job in filtered:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                match_score = job['match_score']
                match_color = "success" if match_score >= 70 else "warning" if match_score >= 40 else "danger"
                st.markdown(f"""
                <div class="job-card">
                    <h3>{job['title']}</h3>
                    <p style="color: var(--primary);">{job['company_name2']}</p>
                    <p>📍 {job['location']} | 💼 {job['job_type']} | 💰 {job['salary_range']}</p>
                    <p>{job['description'][:200]}...</p>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <span class="badge badge-info">{job['category']}</span>
                        <span class="badge badge-success">{job['experience_level']}</span>
                        {','.join(job['skills_required'].split(',')[:3]) if job['skills_required'] else ''}
                    </div>
                """, unsafe_allow_html=True)

                if match_score > 0:
                    st.markdown(f"""
                    <div style="margin: 0.5rem 0;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>AI Match Score</span>
                            <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                        </div>
                        <div class="match-score" style="width: {match_score}%;"></div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                if job['applied'] == 0:
                    if st.button("📝 Apply Now", key=f"apply_{job['id']}", use_container_width=True):
                        st.session_state.apply_job_id = job['id']
                        st.session_state.apply_job_title = job['title']
                        st.rerun()
                else:
                    st.success("✅ Applied")

                if job['saved'] == 0:
                    if st.button("🔖 Save", key=f"save_{job['id']}", use_container_width=True):
                        save_job(st.session_state.user_id, job['id'])
                        add_notification(st.session_state.user_id, "save", "Job Saved",
                                       f"You saved {job['title']}")
                        st.rerun()
                else:
                    if st.button("📌 Saved", key=f"unsave_{job['id']}", use_container_width=True):
                        unsave_job(st.session_state.user_id, job['id'])
                        st.rerun()
            st.markdown("---")


# --- Apply Job Section ---
def apply_job_section():
    if "apply_job_id" not in st.session_state:
        return

    job_tuple = get_job_by_id(st.session_state.apply_job_id)
    if not job_tuple:
        st.error("Job not found")
        return

    # Convert job tuple to dict (jobs.* columns)
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

    profile = get_or_create_profile(st.session_state.user_id)

    st.markdown(f"<h2>📝 Apply for {st.session_state.apply_job_title}</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        <div class="job-card">
            <h3>{job['title']}</h3>
            <p><strong>Company:</strong> {job['company_name']}</p>
            <p><strong>Location:</strong> {job['location']}</p>
            <p><strong>Type:</strong> {job['job_type']}</p>
            <p><strong>Salary:</strong> {job['salary_range']}</p>
            <p><strong>Description:</strong> {job['description']}</p>
            <p><strong>Requirements:</strong> {job['requirements']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("application_form"):
            match_score = calculate_match_score(job['skills_required'], profile[5])
            if match_score > 0:
                st.markdown(f"""
                <div style="margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>AI Match Score</span>
                        <span style="font-weight: 600; color: {'#10B981' if match_score >= 70 else '#F59E0B' if match_score >= 40 else '#EF4444'};">{match_score}%</span>
                    </div>
                    <div class="match-score" style="width: {match_score}%;"></div>
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
                    add_application(job['id'], st.session_state.user_id, job['company_id'], match_score, cover_letter)
                    add_notification(st.session_state.user_id, "application", "Application Submitted",
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

    with col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; border: 1px solid var(--border-color);">
            <h4>📋 Application Tips</h4>
            <ul style="color: var(--text-secondary);">
                <li>Tailor your cover letter</li>
                <li>Highlight relevant skills</li>
                <li>Proofread before submitting</li>
                <li>Make sure resume is up to date</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# --- My Applications Section ---
def my_applications_section():
    st.markdown("<h2>📋 My Applications</h2>", unsafe_allow_html=True)

    applications = get_user_applications(st.session_state.user_id)

    if not applications:
        st.info("You haven't applied to any jobs yet.")
        return

    statuses = ["All", "Pending", "Reviewed", "Interview", "Accepted", "Rejected"]
    selected_status = st.selectbox("Filter by status", statuses)

    filtered = applications
    if selected_status != "All":
        filtered = [a for a in applications if a[4].capitalize() == selected_status]  # status at index 4

    # Track which application details are expanded
    if "show_details_for" not in st.session_state:
        st.session_state.show_details_for = None

    for i, app in enumerate(filtered):
        status_color = {
            "pending": "warning",
            "reviewed": "info",
            "interview": "success",
            "accepted": "success",
            "rejected": "danger"
        }.get(app[4], "info")

        with st.container():
            applied_at_str = app[7].strftime('%Y-%m-%d') if app[7] else ''

            st.markdown(f"""
            <div class="job-card">
                <h3>{app[9]}</h3>                <!-- job_title -->
                <p style="color: var(--primary);">{app[10]}</p>  <!-- company_name -->
                <p>📍 {app[11]} | 💰 {app[12]}</p> <!-- location, salary_range -->
                <p><strong>Applied:</strong> {applied_at_str}</p>  <!-- applied_at -->
                <p><strong>Status:</strong> <span class="badge-{status_color}">{app[4].upper()}</span></p>
                {f'<p><strong>Match Score:</strong> <span style="color: #10B981;">{app[5]}%</span></p>' if app[5] else ''}
            """, unsafe_allow_html=True)

            # Interview details if scheduled
            if app[14] == "scheduled":  # interview_status at index 14
                st.markdown(f"""
                <div style="background: #3B82F620; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                    <h4>🗓️ Interview Scheduled</h4>
                    <p><strong>Date:</strong> {app[13]}</p>  <!-- scheduled_date -->
                    <p><strong>Meeting Link:</strong> <a href="{app[15]}" target="_blank">{app[15]}</a></p>  <!-- meeting_link -->
                </div>
                """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Details", key=f"details_{app[0]}_{i}"):
                    if st.session_state.show_details_for == app[0]:
                        st.session_state.show_details_for = None
                    else:
                        st.session_state.show_details_for = app[0]
                    st.rerun()
            with col2:
                if app[4] == "accepted":
                    st.success("🎉 Hired!")

            # Expanded details
            if st.session_state.show_details_for == app[0]:
                with st.expander("Application Details", expanded=True):
                    st.markdown(f"**Cover Letter:** {app[6]}")
                    if app[14] == "scheduled":
                        st.markdown(f"**Interview Date:** {app[13]}")
                        st.markdown(f"**Meeting Link:** {app[15]}")
                    else:
                        st.info("No interview scheduled yet.")

            st.markdown("---")

# --- Job Requests Section ---
def job_requests_section():
    st.markdown("<h2>📋 My Job Requests (I'm looking for work)</h2>", unsafe_allow_html=True)

    # Initialize session state for tab
    if "job_request_tab" not in st.session_state:
        st.session_state.job_request_tab = "My Requests"

    # Custom tab navigation using buttons styled as tabs
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
        st.markdown("### Your current job requests")
        my_requests = get_user_requests(st.session_state.user_id)

        if not my_requests:
            st.info("You haven't posted any job requests yet. Go to 'Post a New Request' to create one.")
        else:
            for req in my_requests:
                with st.expander(f"{req[2]} ({req[7].upper()}) - {req[5]}"):
                    st.markdown(f"**Description:** {req[3]}")
                    st.markdown(f"**Category:** {req[4]}")
                    st.markdown(f"**Location:** {req[5]}")
                    st.markdown(f"**Budget/Compensation:** {req[6]}")
                    posted_at_str = req[8].strftime('%Y-%m-%d') if req[8] else ''
                    st.markdown(f"**Posted on:** {posted_at_str}")

                    col1, col2, col3, col4 = st.columns([1,1,1,2])
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{req[0]}"):
                            st.session_state.edit_request_id = req[0]
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{req[0]}"):
                            delete_job_request(req[0])
                            add_notification(st.session_state.user_id, "request", "Request Deleted",
                                           f"Your request '{req[2]}' has been deleted.")
                            st.rerun()
                    with col3:
                        new_status = "closed" if req[7] == "open" else "open"
                        btn_label = "🔒 Close" if req[7] == "open" else "🔓 Reopen"
                        if st.button(btn_label, key=f"status_{req[0]}"):
                            update_job_request(req[0], req[2], req[3], req[4], req[5], req[6], new_status)
                            st.rerun()

            # Edit form (appears when an edit button is clicked)
            if "edit_request_id" in st.session_state:
                st.markdown("---")
                st.markdown("### Edit Request")
                req_id = st.session_state.edit_request_id
                # Find the request
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
                            add_notification(st.session_state.user_id, "request", "Request Updated",
                                           f"Your request '{title}' has been updated.")
                            del st.session_state.edit_request_id
                            st.rerun()
                else:
                    st.error("Request not found")
                    if st.button("Back"):
                        del st.session_state.edit_request_id
                        st.rerun()

    else:  # Post a New Request tab
        st.markdown("### Post a New Job Request")
        st.write("Let employers know you're available for work.")
        with st.form("post_request_form", clear_on_submit=True):
            title = st.text_input("What kind of job are you looking for? (e.g., 'Senior Python Developer')")
            description = st.text_area("Describe your skills, experience, and what you're looking for", height=150)
            category = st.selectbox("Category", ["Technology", "Data Science", "Design", "Marketing", "Sales", "Other"])
            location = st.text_input("Location (or 'Remote')")
            budget = st.text_input("Expected compensation (e.g., '$80k/year' or 'Negotiable')")
            submitted = st.form_submit_button("Post Request")
            if submitted and title:
                add_job_request(st.session_state.user_id, title, description, category, location, budget)
                add_notification(st.session_state.user_id, "request", "Request Posted",
                               f"Your request '{title}' has been posted.")
                send_email(
                    st.session_state.user_email,
                    "Job Request Posted",
                    f"Your request '{title}' has been posted successfully.\n\nEmployers will be able to see it"
                )
                st.success("Request posted!")
                # Switch to My Requests tab after successful post
                st.session_state.job_request_tab = "My Requests"
                st.rerun()

# --- Messages Section ---
from streamlit_autorefresh import st_autorefresh

def messages_section():
    st.markdown("<h2>💬 Messages</h2>", unsafe_allow_html=True)

    conversations = get_conversations(st.session_state.user_id)

    if not conversations:
        st.info("No messages yet. Apply to jobs to start conversations!")
        return

    for i, conv in enumerate(conversations):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            last_time_str = conv[8].strftime('%Y-%m-%d %H:%M') if conv[8] else ''
            st.markdown(f"""
            <div style="background: white; padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h4>{conv[5]}</h4>
                        <p style="color: var(--text-secondary);">{conv[6]}</p>
                        <p style="font-size: 0.9rem;">{conv[7][:100] if conv[7] else 'No messages'}...</p>
                        <p style="font-size:0.7rem; color:var(--text-secondary);">{last_time_str}</p>
                    </div>
                    {f'<span class="badge-danger" style="align-self: center;">{conv[9]} new</span>' if conv[9] > 0 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            # This column can be empty or removed; keeping it for layout but not using it.
            pass
        with col3:
            if st.button("Open Chat", key=f"open_chat_{conv[4]}_{i}"):
                st.session_state.chat_company_id = conv[4]
                st.session_state.chat_company_name = conv[5]
                st.rerun()

    if "chat_company_id" in st.session_state:
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

        messages = get_messages(st.session_state.user_id, st.session_state.chat_company_id)
        mark_messages_read(st.session_state.user_id, st.session_state.chat_company_id)

        for msg in messages:
            msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
            if msg[2] == "employee":
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div style="background-color: #2563EB; color: white; padding: 0.75rem; border-radius: 12px 12px 0 12px; display: inline-block; max-width: 70%;">
                        {msg[6]}<br>
                        <span style="font-size:0.7rem; opacity:0.8;">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div style="background: #F1F5F9; color: #1e293b; padding: 0.75rem; border-radius: 12px 12px 12px 0; display: inline-block; max-width: 70%;">
                        <strong>{st.session_state.chat_company_name}</strong><br>
                        {msg[6]}<br>
                        <span style="font-size:0.7rem; color: var(--text-secondary);">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Message input and send button (no form)
        message = st.text_area("Type your message", height=100, key="chat_message_input")
        if st.button("📤 Send", key="send_message_btn"):
            if message:
                try:
                    send_message(st.session_state.user_id, "employee",
                            st.session_state.chat_company_id, "company",
                            message, application_id=None)
                    st.success("Message sent!")
                    # Clear the input by resetting the widget key
                    st.session_state["chat_message_input"] = ""
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to send message: {e}")
            else:
                st.warning("Please enter a message.")

# --- Saved Jobs Section ---
def saved_jobs_section():
    st.markdown("<h2>🔖 Saved Jobs</h2>", unsafe_allow_html=True)

    saved = get_saved_jobs(st.session_state.user_id)  # list of tuples

    if not saved:
        st.info("No saved jobs yet.")
        return

    # The tuple from get_saved_jobs contains: jobs.* (15 columns) + company_name (1) + applied (1) = 17 columns.
    # So applied is at index 16.
    for job in saved:
        # Convert to dict for readability (and to avoid index mistakes)
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
            'company_name': job[15],   # from companies table
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
                unsave_job(st.session_state.user_id, job_dict['id'])
                st.rerun()
        st.markdown("---")

def analytics_section():
    st.markdown("<h2>📊 My Analytics</h2>", unsafe_allow_html=True)

    stats = get_application_stats(st.session_state.user_id)
    timeline = get_applications_over_time(st.session_state.user_id)
    interview_count = get_interview_count(st.session_state.user_id)

    total = sum(s[1] for s in stats)
    pending = next((s[1] for s in stats if s[0] == 'pending'), 0)
    accepted = next((s[1] for s in stats if s[0] == 'accepted'), 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>Total Applications</h3><p style="font-size:2rem; font-weight:600; color:var(--primary);">{total}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>Pending</h3><p style="font-size:2rem; font-weight:600; color:#F59E0B;">{pending}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>Interviews</h3><p style="font-size:2rem; font-weight:600; color:#3B82F6;">{interview_count}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>Accepted</h3><p style="font-size:2rem; font-weight:600; color:#10B981;">{accepted}</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if stats:
            df = pd.DataFrame(stats, columns=['status', 'count'])
            fig = px.pie(df, values='count', names='status', title='Application Status',
                        color_discrete_sequence=['#10B981', '#F59E0B', '#3B82F6', '#EF4444'])
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if timeline:
            df = pd.DataFrame(timeline, columns=['date', 'count'])
            fig = px.line(df, x='date', y='count', title='Applications Over Time', markers=True)
            st.plotly_chart(fig, use_container_width=True)

    if total > 0:
        success_rate = (accepted / total) * 100
        st.markdown(f"""
        <div class="stat-card" style="text-align: center;">
            <h3>Success Rate</h3>
            <p style="font-size: 3rem; font-weight: 600; color: var(--primary);">{success_rate:.1f}%</p>
            <div class="match-score" style="width: {success_rate}%;"></div>
        </div>
        """, unsafe_allow_html=True)

# --- Main routing ---
if selected == "Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    # Quick stats (simplified, you can add more)
    total_apps = len(get_user_applications(st.session_state.user_id))
    total_saved = len(get_saved_jobs(st.session_state.user_id))
    unread_msgs = sum(c[9] for c in get_conversations(st.session_state.user_id))
    interview_count = get_interview_count(st.session_state.user_id)

    with col1:
        st.markdown(f'<div class="stat-card"><h3>📋 Applications</h3><p style="font-size:2rem;">{total_apps}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>🗓️ Interviews</h3><p style="font-size:2rem;">{interview_count}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>💬 Unread</h3><p style="font-size:2rem;">{unread_msgs}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>🔖 Saved</h3><p style="font-size:2rem;">{total_saved}</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Recent Applications")
        recent = get_user_applications(st.session_state.user_id)[:5]
        if recent:
            for app in recent:
                applied_at_str = app[7].strftime('%Y-%m-%d') if app[7] else ''
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 8px; margin:0.5rem 0; border:1px solid var(--border-color);">
                    <p><strong>{app[10]}</strong> at {app[11]}</p>
                    <p style="font-size:0.9rem;">Applied: {applied_at_str}</p>
                    <span class="badge-{app[4]}">{app[4].upper()}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No applications yet")

    with col2:
        st.markdown("### 🔔 Recent Notifications")
        notifs = get_user_notifications(st.session_state.user_id, 5)
        if notifs:
            for n in notifs:
                is_read = n[6]
                badge = "🆕 " if not is_read else ""
                # Format the timestamp
                created_at_str = n[7].strftime('%Y-%m-%d %H:%M') if n[7] else ''
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 8px; margin:0.5rem 0; border:1px solid var(--border-color); {'' if is_read else 'border-left: 4px solid var(--primary);'}">
                    <p><strong>{badge}{n[3]}</strong></p>
                    <p>{n[4]}</p>
                    <p style="font-size:0.8rem;">{created_at_str}</p>
                </div>
                """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("Mark all as read", use_container_width=True):
                    mark_notifications_read(st.session_state.user_id)
                    st.success("✅ All notifications marked as read!")
                    time.sleep(1)
                    st.rerun()
            with col_b:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
        else:
            st.info("No notifications")

elif selected == "Find Jobs":
    if "apply_job_id" in st.session_state:
        apply_job_section()
    else:
        job_search_section()

elif selected == "Companies":
    companies_section()

elif selected == "My Applications":
    my_applications_section()

elif selected == "Job Requests":
    job_requests_section()

elif selected == "Messages":
    messages_section()

elif selected == "Saved Jobs":
    saved_jobs_section()

elif selected == "Profile":
    profile_section()

elif selected == "Analytics":
    analytics_section()
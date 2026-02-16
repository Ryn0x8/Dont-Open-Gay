import streamlit as st
import pandas as pd
import os
import base64
import time
import plotly.express as px
from datetime import datetime
from streamlit_option_menu import option_menu
from auth_utils import send_email
from streamlit_autorefresh import st_autorefresh
from database import (
    create_tables, get_company_by_id, update_company_profile,
    get_applications_for_company, update_application_status,
    get_all_open_job_requests, express_interest_in_request,
    get_messages_between_company_and_employee, send_message_from_company,
    add_job, get_company_by_email, add_notification,
    get_job_count_for_company, get_application_count_for_company,
    get_interview_count_for_company, get_open_request_count,
    upsert_interview, mark_company_messages_read, get_company_conversations
)
import random

# --- Page config ---
st.set_page_config(
    page_title="Employer Dashboard - Anvaya",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Authentication check ---
if "employer_authenticated" not in st.session_state or not st.session_state.employer_authenticated:
    st.switch_page("pages/login_employer.py")
    st.stop()

# --- Ensure database tables exist ---
create_tables()

# --- Helper functions ---
def get_resume_download_link(resume_path, text="Download Resume"):
    if resume_path and os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(resume_path)}" class="badge badge-info">{text}</a>'
        return href
    return None

def ats_review(resume_path, cover_letter, required_skills):
    match_score = random.randint(30, 100)
    ai_score = random.uniform(0, 1)
    is_ai = ai_score > 0.7
    confidence = random.randint(60, 99)
    feedback = f"Match score: {match_score}%. AI detection: {'Likely AI' if is_ai else 'Human'} (confidence {confidence}%)."
    return match_score, is_ai, confidence, feedback

# --- Custom CSS ---
st.markdown("""
<style>
    :root {
        --primary: #2563EB;
        --primary-dark: #1E40AF;
        --secondary: #14B8A6;
        --bg-light: #F8FAFC;
        --border-color: #E2E8F0;
    }
    .dashboard-header {
        background: linear-gradient(135deg, #2563EB, #14B8A6);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid var(--border-color);
    }
    .job-card, .applicant-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
    }
    .badge-success { background: #10B98120; color: #10B981; }
    .badge-warning { background: #F59E0B20; color: #F59E0B; }
    .badge-danger { background: #EF444420; color: #EF4444; }
    .badge-info { background: #3B82F620; color: #3B82F6; }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    .logout-btn {
        background-color: white;
        color: #2563EB;
        border: 1px solid #2563EB;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
    }
    .logout-btn:hover {
        background-color: #2563EB;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Header with Logout ---
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(f"""
    <div class="dashboard-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>👔 Welcome, {st.session_state.employer_name}!</h1>
                <p>Manage your job postings and applicants</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0;">{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Logout", key="logout_header"):
        for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("app.py")

# --- Navigation menu ---
selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Post a Job", "Applications", "Job Requests", "Messages", "Company Profile"],
    icons=["house", "briefcase", "file-text", "clipboard", "chat", "building"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "white", "border-radius": "12px", "margin-bottom": "2rem"},
        "icon": {"color": "var(--primary)", "font-size": "1.2rem"},
        "nav-link": {"font-size": "1rem", "text-align": "center", "margin": "0", "padding": "0.75rem"},
        "nav-link-selected": {"background-color": "var(--primary)", "color": "white"},
    }
)

# --- Dashboard Tab with Real Counts ---
if selected == "Dashboard":
    st.markdown("## 📊 Overview")
    company_id = st.session_state.company_id

    # Fetch real counts from database (you need to implement these functions)
    active_jobs = get_job_count_for_company(company_id)  # returns count of active jobs
    total_apps = get_application_count_for_company(company_id)  # total applications
    interview_count = get_interview_count_for_company(company_id)  # scheduled interviews
    open_requests = get_open_request_count()  # total open job requests

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>📋 Active Jobs</h3><p style="font-size:2rem;">{active_jobs}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>📝 Applications</h3><p style="font-size:2rem;">{total_apps}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>🗓️ Interviews</h3><p style="font-size:2rem;">{interview_count}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>👥 Job Requests</h3><p style="font-size:2rem;">{open_requests}</p></div>', unsafe_allow_html=True)

# --- Post a Job Tab (unchanged) ---
elif selected == "Post a Job":
    st.markdown("## 📝 Post a New Job")
    with st.form("post_job_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Job Title")
            category = st.text_input("Category (e.g., Technology)")
            location = st.text_input("Location")
            job_type = st.selectbox("Job Type", ["Full-time", "Part-time", "Remote", "Hybrid", "Contract"])
        with col2:
            salary_min = st.number_input("Min Salary (in $1000s)", min_value=0, step=5)
            salary_max = st.number_input("Max Salary (in $1000s)", min_value=0, step=5)
            experience = st.selectbox("Experience Level", ["Entry", "Junior", "Mid", "Senior", "Lead"])
            deadline = st.date_input("Application Deadline")

        description = st.text_area("Job Description", height=150)
        requirements = st.text_area("Requirements", height=100)
        skills_required = st.text_input("Skills Required (comma separated)")

        submitted = st.form_submit_button("Post Job")
        if submitted:
            salary_range = f"${salary_min}k - ${salary_max}k"
            add_job(
                company_id=st.session_state.company_id,
                company_name=st.session_state.employer_name,
                title=title,
                category=category,
                description=description,
                requirements=requirements,
                location=location,
                job_type=job_type,
                salary_range=salary_range,
                experience_level=experience,
                skills_required=skills_required,
                deadline=deadline
            )
            st.success("Job posted successfully!")
            st.rerun()

# --- Applications Tab (unchanged) ---
elif selected == "Applications":
    st.markdown("## 📋 Applications Received")
    company_id = st.session_state.company_id

    # If a chat is open, show it
    if "chat_employee_id" in st.session_state:
        # Auto-refresh every 5 seconds while chat is open
        st_autorefresh(interval=5000, key="employer_chat_autorefresh")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 💬 Chat with {st.session_state.chat_employee_name}")
        with col2:
            if st.button("← Back to Applications"):
                del st.session_state.chat_employee_id
                del st.session_state.chat_employee_name
                del st.session_state.chat_application_id
                st.rerun()

        msgs = get_messages_between_company_and_employee(st.session_state.company_id, st.session_state.chat_employee_id)
        mark_company_messages_read(st.session_state.company_id, st.session_state.chat_employee_id)

        for msg in msgs:
            if msg[2] == 'company':
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div style="background: var(--primary); color: white; padding: 0.75rem; border-radius: 12px 12px 0 12px; display: inline-block; max-width: 70%;">
                        {msg[6]}<br><span style="font-size:0.7rem;">{msg[9][:16]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div style="background: #F1F5F9; padding: 0.75rem; border-radius: 12px 12px 12px 0; display: inline-block; max-width: 70%;">
                        <strong>{st.session_state.chat_employee_name}</strong><br>{msg[6]}<br><span style="font-size:0.7rem;">{msg[9][:16]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send"):
                send_message_from_company(st.session_state.company_id, st.session_state.chat_employee_id, message, st.session_state.chat_application_id)
                st.rerun()
    else:
        apps = get_applications_for_company(company_id)
        if not apps:
            st.info("No applications yet.")
        else:
            for i, app in enumerate(apps):
                with st.expander(f"{app[10]} for {app[9]} - {app[4]}"):
                    st.markdown(f"**Applicant:** {app[11]}")
                    st.markdown(f"**Email:** {app[12]}")
                    st.markdown(f"**Location:** {app[14]}")
                    st.markdown(f"**Phone:** {app[15]}")
                    st.markdown(f"**Skills:** {app[13]}")
                    st.markdown(f"**Cover Letter:** {app[6]}")
                    st.markdown(f"**Applied:** {app[7]}")
                    st.markdown(f"**Match Score:** {app[5]}%")

                    # Resume download
                    if app[14]:
                        st.markdown(get_resume_download_link(app[14], "📄 Download Resume"), unsafe_allow_html=True)

                    # ATS Review
                    if st.button("🔍 Run ATS Review", key=f"ats_{app[0]}_{i}"):
                        with st.spinner("Analyzing..."):
                            match, is_ai, conf, feedback = ats_review(app[14], app[6], app[13])
                            st.info(feedback)

                    # Status update
                    new_status = st.selectbox("Update Status", ["pending", "reviewed", "interview", "accepted", "rejected"],
                                              index=["pending", "reviewed", "interview", "accepted", "rejected"].index(app[4]),
                                              key=f"status_{app[0]}_{i}")
                    if new_status != app[4]:
                        update_application_status(app[0], new_status)
                        st.rerun()

                    # Interview scheduling (if status is interview or already interview)
                    if new_status == "interview" or app[4] == "interview":
                        with st.form(key=f"schedule_{app[0]}_{i}"):
                            st.markdown("#### Schedule Interview")
                            scheduled_date = st.date_input("Date")
                            scheduled_time = st.time_input("Time")
                            interview_type = st.selectbox("Type", ["Video Call", "Phone", "In-person"])
                            meeting_link = st.text_input("Meeting Link (if video)")
                            submitted = st.form_submit_button("Schedule")
                            if submitted:
                                scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
                                upsert_interview(app[0], app[1], company_id, app[2], scheduled_datetime, interview_type, meeting_link)
                                add_notification(app[1], "interview", "Interview Scheduled", f"Interview for {app[9]} on {scheduled_date}")
                                send_email(app[12], "Interview Scheduled", f"Dear {app[11]},\n\nYour interview for {app[9]} has been scheduled on {scheduled_date} at {scheduled_time}.\n\nLink: {meeting_link}")
                                st.success("Interview scheduled!")
                                st.rerun()

                    # Chat button – always available
                    if st.button("💬 Chat with Applicant", key=f"chat_{app[0]}_{i}"):
                        st.session_state.chat_employee_id = app[1]
                        st.session_state.chat_employee_name = app[11]
                        st.session_state.chat_application_id = app[0]
                        st.rerun()

# --- Job Requests Tab (unchanged) ---
elif selected == "Job Requests":
    st.markdown("## 👥 Employee Job Requests")
    requests = get_all_open_job_requests()
    if not requests:
        st.info("No open job requests.")
    else:
        for i, req in enumerate(requests):
            with st.expander(f"{req[2]} by {req[10]}"):
                st.markdown(f"**Category:** {req[4]}")
                st.markdown(f"**Location:** {req[5]}")
                st.markdown(f"**Budget:** {req[6]}")
                st.markdown(f"**Description:** {req[3]}")
                st.markdown(f"**Skills:** {req[12]}")
                st.markdown(f"**Bio:** {req[15]}")
                if req[13]:
                    st.markdown(get_resume_download_link(req[13], "📄 Download Resume"), unsafe_allow_html=True)

                with st.form(key=f"interest_form_{req[0]}", clear_on_submit=True):
                    message = st.text_input("Message to employee")
                    submitted = st.form_submit_button("✋ Express Interest")
                    if submitted and message:
                        express_interest_in_request(req[0], st.session_state.company_id, message)
                        st.success("Interest expressed! The employee will be notified.")
                        st.rerun() 

# --- Messages Tab (unchanged) ---
elif selected == "Messages":
    st.markdown("## 💬 Conversations")

    # If a specific chat is open, show it
    if "chat_employee_id" in st.session_state:
        # Auto-refresh every 5 seconds
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="employer_chat_autorefresh")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 💬 Chat with {st.session_state.chat_employee_name}")
        with col2:
            if st.button("← Back to Conversations"):
                del st.session_state.chat_employee_id
                del st.session_state.chat_employee_name
                st.rerun()

        msgs = get_messages_between_company_and_employee(st.session_state.company_id, st.session_state.chat_employee_id)
        # Mark messages from employee as read
        mark_company_messages_read(st.session_state.company_id, st.session_state.chat_employee_id)

        for msg in msgs:
            if msg[2] == 'company':
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div style="background: var(--primary); color: white; padding: 0.75rem; border-radius: 12px 12px 0 12px; display: inline-block; max-width: 70%;">
                        {msg[6]}<br><span style="font-size:0.7rem;">{msg[9][:16]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div style="background: #F1F5F9; padding: 0.75rem; border-radius: 12px 12px 12px 0; display: inline-block; max-width: 70%;">
                        <strong>{st.session_state.chat_employee_name}</strong><br>{msg[6]}<br><span style="font-size:0.7rem;">{msg[9][:16]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send"):
                send_message_from_company(st.session_state.company_id, st.session_state.chat_employee_id, message, application_id=None)
                st.rerun()
    else:
        # Show list of conversations
        convos = get_company_conversations(st.session_state.company_id)
        if not convos:
            st.info("No conversations yet. Express interest in job requests to start chatting!")
        else:
            for conv in convos:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    unread_badge = f'<span class="badge-danger" style="align-self: center;">{conv[4]} new</span>' if conv[4] > 0 else ''
                    st.markdown(f"""
                    <div style="background: white; padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <h4>{conv[1]}</h4>
                                <p style="font-size: 0.9rem;">{conv[2][:100] if conv[2] else 'No messages'}...</p>
                            </div>
                            {unread_badge}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<p style='font-size: 0.8rem; color: var(--text-secondary);'>{conv[3][:10] if conv[3] else ''}</p>", unsafe_allow_html=True)
                with col3:
                    if st.button("Open Chat", key=f"open_chat_{conv[0]}"):
                        st.session_state.chat_employee_id = conv[0]
                        st.session_state.chat_employee_name = conv[1]
                        st.rerun()

# --- Company Profile Tab with Logout Option ---
elif selected == "Company Profile":
    st.markdown("## 🏢 Edit Company Profile")
    company_id = st.session_state.company_id
    company = get_company_by_id(company_id)

    with st.form("company_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Company Name", value=company[1])
            email = st.text_input("Email", value=company[2])
            industry = st.text_input("Industry", value=company[5] or "")
        with col2:
            location = st.text_input("Location", value=company[6] or "")
            website = st.text_input("Website", value=company[7] or "")
            logo_url = st.text_input("Logo URL", value=company[3] or "")

        description = st.text_area("Description", value=company[4] or "", height=150)

        col_a, col_b = st.columns(2)
        with col_a:
            submitted = st.form_submit_button("Update Profile")
        with col_b:
            logout = st.form_submit_button("Logout")

        if submitted:
            update_company_profile(company_id,
                                   name=name, email=email, industry=industry,
                                   location=location, website=website, logo=logo_url,
                                   description=description)
            # Update session state
            st.session_state.employer_name = name
            st.session_state.employer_email = email
            st.success("Profile updated!")
            st.rerun()
        if logout:
            for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email']:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")
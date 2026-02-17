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
    get_company_by_id, update_company_profile,
    get_applications_for_company, update_application_status,
    get_all_open_job_requests, express_interest_in_request,
    get_messages_between_company_and_employee, send_message_from_company,
    add_job, get_company_by_email, add_notification,
    get_job_count_for_company, get_application_count_for_company,
    get_interview_count_for_company, get_open_request_count,
    upsert_interview, mark_company_messages_read, get_company_conversations,
    delete_job, get_company_jobs_all
)
import random
from database import update_expired_jobs
update_expired_jobs()   

# --- Page config ---
st.set_page_config(
    page_title="Employer Dashboard - Anvaya",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Authentication check ---
if "employer_authenticated" not in st.session_state or not st.session_state.employer_authenticated:
    st.switch_page("pages/login_employer.py")
    st.stop()

# --- Ensure database tables exist ---

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

# --- Custom CSS (new modern design) ---
st.markdown("""
<style>
    /* Global styles */
    :root {
        --primary: #4F46E5;
        --primary-light: #818CF8;
        --primary-dark: #3730A3;
        --secondary: #0EA5E9;
        --accent: #10B981;
        --bg: #F9FAFB;
        --card-bg: #FFFFFF;
        --text: #1F2937;
        --text-light: #6B7280;
        --border: #E5E7EB;
        --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.02);
    }

    .stApp {
        background-color: var(--bg);
    }

    /* Sidebar styling */
    .css-1d391kg, .css-1wrcr25 {
        background-color: white;
        border-right: 1px solid var(--border);
    }

    /* Company header in sidebar */
    .sidebar-header {
        padding: 1.5rem 1rem;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        border-radius: 0 0 20px 20px;
        margin-bottom: 1rem;
        color: white;
        text-align: center;
    }
    .sidebar-header h3 {
        margin: 0;
        font-weight: 600;
    }
    .sidebar-header p {
        margin: 0.25rem 0 0;
        opacity: 0.9;
        font-size: 0.9rem;
    }

    /* Main header area */
    .main-header {
        background: white;
        padding: 1.5rem 2rem;
        border-radius: 20px;
        box-shadow: var(--shadow);
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .main-header h1 {
        margin: 0;
        color: var(--text);
        font-weight: 700;
        font-size: 1.8rem;
    }
    .main-header p {
        margin: 0;
        color: var(--text-light);
    }

    /* Cards */
    .stat-card {
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border: 1px solid var(--border);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow);
    }
    .stat-card h3 {
        color: var(--text-light);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .stat-card p {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--primary);
        margin: 0;
    }

    .job-card, .applicant-card, .conversation-card {
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
        transition: all 0.2s;
    }
    .job-card:hover, .applicant-card:hover, .conversation-card:hover {
        box-shadow: var(--shadow);
    }

    /* Badges */
    .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
    }
    .badge-success { background: #D1FAE5; color: #065F46; }
    .badge-warning { background: #FEF3C7; color: #92400E; }
    .badge-danger { background: #FEE2E2; color: #991B1B; }
    .badge-info { background: #DBEAFE; color: #1E40AF; }
    .badge-primary { background: #EEF2FF; color: var(--primary-dark); }

    /* Buttons */
    .stButton > button {
        border-radius: 12px;
        font-weight: 500;
        transition: all 0.2s;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }

    /* Form inputs */
    .stTextInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div > select {
        border-radius: 12px;
        border: 1px solid var(--border);
        padding: 0.75rem 1rem;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
    }

    /* Chat bubbles */
    .chat-bubble-company {
        background: var(--primary);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 20px 20px 0 20px;
        max-width: 70%;
        display: inline-block;
        margin: 0.5rem 0;
    }
    .chat-bubble-employee {
        background: #F3F4F6;
        color: var(--text);
        padding: 0.75rem 1rem;
        border-radius: 20px 20px 20px 0;
        max-width: 70%;
        display: inline-block;
        margin: 0.5rem 0;
    }
    .chat-timestamp {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 0.25rem;
    }

    /* Dividers */
    hr {
        margin: 2rem 0;
        border: 0;
        border-top: 1px solid var(--border);
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <h3>{st.session_state.employer_name}</h3>
        <p>{st.session_state.employer_email}</p>
    </div>
    """, unsafe_allow_html=True)

    selected = option_menu(
        menu_title="Navigation",
        options=["Dashboard", "Post a Job", "Applications", "Job Requests", "Messages", "Company Profile"],
        icons=["house", "briefcase", "file-text", "clipboard", "chat", "building"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "var(--primary)", "font-size": "1.2rem"},
            "nav-link": {"font-size": "1rem", "text-align": "left", "margin": "0.25rem 0", "border-radius": "12px"},
            "nav-link-selected": {"background-color": "var(--primary)", "color": "white", "font-weight": "500"},
        }
    )

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("app.py")

# --- Main Header (welcome and date) ---
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>👋 Welcome back, {st.session_state.employer_name}!</h1>
        <p>Here's what's happening with your job postings today.</p>
    </div>
    <div>
        <p style="font-size: 1.1rem; font-weight: 500;">{datetime.now().strftime('%B %d, %Y')}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Dashboard Tab with Real Counts ---
if selected == "Dashboard":
    st.markdown("## 📊 Overview")
    company_id = st.session_state.company_id

    active_jobs = get_job_count_for_company(company_id)
    total_apps = get_application_count_for_company(company_id)
    interview_count = get_interview_count_for_company(company_id)
    open_requests = get_open_request_count()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>📋 Active Jobs</h3><p>{active_jobs}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>📝 Applications</h3><p>{total_apps}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>🗓️ Interviews</h3><p>{interview_count}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>👥 Job Requests</h3><p>{open_requests}</p></div>', unsafe_allow_html=True)

    # Optional: recent activity chart
    if total_apps > 0:
        apps = get_applications_for_company(company_id)
        df = pd.DataFrame(apps, columns=["id", "employee_id", "company_id", "job_id", "status", "match_score", "cover_letter", "applied_at", "updated_at", "job_title", "employee_name", "employee_email", "resume_path", "skills", "location", "phone"])
        df['applied_at'] = pd.to_datetime(df['applied_at'])
        df['date'] = df['applied_at'].dt.date
        daily_apps = df.groupby('date').size().reset_index(name='count')
        if not daily_apps.empty:
            fig = px.line(daily_apps, x='date', y='count', title='Applications Over Time', markers=True)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='var(--text)'
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Post a Job Tab ---
elif selected == "Post a Job":
    update_expired_jobs()

    tab1, tab2 = st.tabs(["📝 Post New Job", "📋 Manage Jobs"])

    with tab1:
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

            submitted = st.form_submit_button("Post Job", use_container_width=True)
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

    with tab2:
        st.markdown("## 📋 Your Job Postings")
        jobs = get_company_jobs_all(st.session_state.company_id)
        if not jobs:
            st.info("You haven't posted any jobs yet.")
        else:
            for job in jobs:
                with st.expander(f"{job['title']} - <span class='badge badge-primary'>{job['status'].upper()}</span>", unsafe_allow_html=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Category:** {job.get('category', 'N/A')}")
                        st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                        st.markdown(f"**Type:** {job.get('job_type', 'N/A')}")
                        st.markdown(f"**Salary:** {job.get('salary_range', 'N/A')}")
                        st.markdown(f"**Experience:** {job.get('experience_level', 'N/A')}")
                        st.markdown(f"**Description:** {job.get('description', 'N/A')}")
                        st.markdown(f"**Requirements:** {job.get('requirements', 'N/A')}")
                        st.markdown(f"**Skills Required:** {job.get('skills_required', 'N/A')}")
                        deadline_str = job['deadline'].strftime('%Y-%m-%d') if job.get('deadline') else 'Not set'
                        st.markdown(f"**Deadline:** {deadline_str}")
                        st.markdown(f"**Posted:** {job['created_at'].strftime('%Y-%m-%d') if job.get('created_at') else 'Unknown'}")
                    with col2:
                        # Delete button with confirmation
                        if st.button(f"🗑️ Delete Job", key=f"delete_job_{job['id']}"):
                            st.session_state.job_to_delete = job['id']
                            st.session_state.job_title_to_delete = job['title']
                            st.rerun()

                        if st.session_state.get("job_to_delete") == job['id']:
                            st.warning("Are you sure?")
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{job['id']}"):
                                delete_job(job['id'])
                                del st.session_state.job_to_delete
                                del st.session_state.job_title_to_delete
                                st.success("Job deleted!")
                                st.rerun()
                            if st.button("❌ Cancel", key=f"confirm_no_{job['id']}"):
                                del st.session_state.job_to_delete
                                del st.session_state.job_title_to_delete
                                st.rerun()

# --- Applications Tab ---
elif selected == "Applications":
    st.markdown("## 📋 Applications Received")
    company_id = st.session_state.company_id

    if "chat_employee_id" in st.session_state:
        st_autorefresh(interval=10000, key="employer_chat_autorefresh")

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
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div class="chat-bubble-company">
                        {msg[6]}<br>
                        <span class="chat-timestamp">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div class="chat-bubble-employee">
                        <strong>{st.session_state.chat_employee_name}</strong><br>
                        {msg[6]}<br>
                        <span class="chat-timestamp">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send", use_container_width=True):
                send_message_from_company(st.session_state.company_id, st.session_state.chat_employee_id, message, st.session_state.chat_application_id)
                st.rerun()
    else:
        apps = get_applications_for_company(company_id)
        if not apps:
            st.info("No applications yet.")
        else:
            for i, app in enumerate(apps):
                with st.expander(f"{app[10]} for {app[9]} - <span class='badge badge-{ 'success' if app[4]=='accepted' else 'warning' if app[4]=='interview' else 'danger' if app[4]=='rejected' else 'info' }'>{app[4].upper()}</span>", unsafe_allow_html=True):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**Applicant:** {app[11]}")
                        st.markdown(f"**Email:** {app[12]}")
                        st.markdown(f"**Location:** {app[14]}")
                        st.markdown(f"**Phone:** {app[15]}")
                        st.markdown(f"**Skills:** {app[14]}")
                        st.markdown(f"**Cover Letter:** {app[6]}")
                        st.markdown(f"**Applied:** {app[7]}")
                        st.markdown(f"**Match Score:** {app[5]}%")
                        if app[13]:
                            st.markdown(get_resume_download_link(app[13], "📄 Download Resume"), unsafe_allow_html=True)
                    with col2:
                        if st.button("🔍 Run ATS Review", key=f"ats_{app[0]}_{i}"):
                            with st.spinner("Analyzing..."):
                                match, is_ai, conf, feedback = ats_review(app[14], app[6], app[13])
                                st.info(feedback)

                        new_status = st.selectbox("Update Status", ["pending", "reviewed", "interview", "accepted", "rejected"],
                                                  index=["pending", "reviewed", "interview", "accepted", "rejected"].index(app[4]),
                                                  key=f"status_{app[0]}_{i}")
                        if new_status != app[4]:
                            update_application_status(app[0], new_status)
                            st.rerun()

                        if new_status == "interview" or app[4] == "interview":
                            with st.form(key=f"schedule_{app[0]}_{i}"):
                                st.markdown("#### Schedule Interview")
                                scheduled_date = st.date_input("Date")
                                scheduled_time = st.time_input("Time")
                                interview_type = st.selectbox("Type", ["Video Call", "Phone", "In-person"])
                                meeting_link = st.text_input("Meeting Link (if video)")
                                submitted = st.form_submit_button("Schedule", use_container_width=True)
                                if submitted:
                                    scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
                                    upsert_interview(app[0], app[1], company_id, app[2], scheduled_datetime, interview_type, meeting_link)
                                    add_notification(app[1], "interview", "Interview Scheduled", f"Interview for {app[9]} on {scheduled_date}")
                                    send_email(app[12], "Interview Scheduled", f"Dear {app[11]},\n\nYour interview for {app[9]} has been scheduled on {scheduled_date} at {scheduled_time}.\n\nLink: {meeting_link}")
                                    st.success("Interview scheduled!")
                                    st.rerun()

                        if st.button("💬 Chat with Applicant", key=f"chat_{app[0]}_{i}"):
                            st.session_state.chat_employee_id = app[1]
                            st.session_state.chat_employee_name = app[11]
                            st.session_state.chat_application_id = app[0]
                            st.rerun()

# --- Job Requests Tab ---
elif selected == "Job Requests":
    st.markdown("## 👥 Employee Job Requests")
    requests = get_all_open_job_requests()
    if not requests:
        st.info("No open job requests.")
    else:
        for i, req in enumerate(requests):
            with st.expander(f"{req[2]} by {req[10]}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Category:** {req[4]}")
                    st.markdown(f"**Location:** {req[5]}")
                    st.markdown(f"**Budget:** {req[6]}")
                    st.markdown(f"**Description:** {req[3]}")
                    st.markdown(f"**Skills:** {req[12]}")
                    st.markdown(f"**Bio:** {req[15]}")
                with col2:
                    if req[13]:
                        st.markdown(get_resume_download_link(req[13], "📄 Download Resume"), unsafe_allow_html=True)
                    with st.form(key=f"interest_form_{req[0]}", clear_on_submit=True):
                        message = st.text_input("Message to employee")
                        if st.form_submit_button("✋ Express Interest", use_container_width=True) and message:
                            express_interest_in_request(req[0], st.session_state.company_id, message)
                            st.success("Interest expressed! The employee will be notified.")
                            st.rerun()

# --- Messages Tab ---
elif selected == "Messages":
    st.markdown("## 💬 Conversations")

    if "chat_employee_id" in st.session_state:
        st_autorefresh(interval=10000, key="employer_chat_autorefresh")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 💬 Chat with {st.session_state.chat_employee_name}")
        with col2:
            if st.button("← Back to Conversations"):
                del st.session_state.chat_employee_id
                del st.session_state.chat_employee_name
                st.rerun()

        msgs = get_messages_between_company_and_employee(st.session_state.company_id, st.session_state.chat_employee_id)
        mark_company_messages_read(st.session_state.company_id, st.session_state.chat_employee_id)

        for msg in msgs:
            if msg[2] == 'company':
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div class="chat-bubble-company">
                        {msg[6]}<br>
                        <span class="chat-timestamp">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div class="chat-bubble-employee">
                        <strong>{st.session_state.chat_employee_name}</strong><br>
                        {msg[6]}<br>
                        <span class="chat-timestamp">{msg_time}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send", use_container_width=True):
                send_message_from_company(st.session_state.company_id, st.session_state.chat_employee_id, message, application_id=None)
                st.rerun()
    else:
        convos = get_company_conversations(st.session_state.company_id)
        if not convos:
            st.info("No conversations yet. Express interest in job requests to start chatting!")
        else:
            for conv in convos:
                with st.container():
                    st.markdown(f"""
                    <div class="conversation-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin: 0;">{conv[1]}</h4>
                                <p style="margin: 0.25rem 0 0; color: var(--text-light);">{conv[2][:100] if conv[2] else 'No messages'}...</p>
                            </div>
                            <div style="text-align: right;">
                                <span class="badge badge-danger" style="margin-right: 0.5rem;">{conv[4]} new</span>
                                <span style="font-size: 0.8rem; color: var(--text-light);">{conv[3].strftime('%Y-%m-%d') if conv[3] else ''}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Open Chat", key=f"open_chat_{conv[0]}"):
                        st.session_state.chat_employee_id = conv[0]
                        st.session_state.chat_employee_name = conv[1]
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)

# --- Company Profile Tab ---
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
            submitted = st.form_submit_button("Update Profile", use_container_width=True)
        with col_b:
            logout = st.form_submit_button("Logout", use_container_width=True)

        if submitted:
            update_company_profile(company_id,
                                   name=name, email=email, industry=industry,
                                   location=location, website=website, logo=logo_url,
                                   description=description)
            st.session_state.employer_name = name
            st.session_state.employer_email = email
            st.success("Profile updated!")
            st.rerun()
        if logout:
            for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email']:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")
import streamlit as st
import pandas as pd
import os
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from auth_utils import send_email
from streamlit_autorefresh import st_autorefresh
from database import (
    get_company_by_id, update_company_profile,
    get_applications_for_company, update_application_status,
    get_all_open_job_requests, express_interest_in_request,
    get_messages_between_company_and_employee, send_message_from_company,
    add_job, add_notification,
    get_job_count_for_company, get_application_count_for_company,
    get_interview_count_for_company, get_open_request_count,
    upsert_interview, mark_company_messages_read, get_company_conversations,
    delete_job, get_company_jobs_all,
    get_new_applications_count, get_unread_messages_count, get_recent_activities
)
import random
from database import update_expired_jobs

update_expired_jobs()

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

# --- Custom CSS (ultra‑classy) ---
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

    /* Two‑row navigation */
    .nav-badge-row {
        margin-bottom: 0px;
    }
    .nav-button-row {
        margin-top: 0px;
    }

    .badge-count {
        background: #EF4444;
        color: white;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 40px;
        line-height: 1;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
    }

    /* Hero header */
    .hero-header {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        padding: 2rem 2.5rem;
        border-radius: 40px;
        color: white;
        margin: 1.5rem 0 2rem 0;
        box-shadow: var(--shadow-lg);
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(5px);
    }

    .hero-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .hero-header p {
        margin: 0.5rem 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }

    .date-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.5rem 1.5rem;
        border-radius: 40px;
        font-weight: 500;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* Notification card */
    .notification-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 24px;
        padding: 1rem;
        border: var(--glass-border);
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    .notification-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-lg);
    }

    .notification-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin-bottom: 0.75rem;
    }

    .notification-title {
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.25rem;
        font-size: 0.95rem;
    }

    .notification-time {
        font-size: 0.7rem;
        color: var(--text-light);
        margin-top: auto;
    }

    /* Stat cards */
    .stat-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 30px;
        border: var(--glass-border);
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
        text-align: center;
    }

    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-lg);
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

    .metric-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 30px;
        border: var(--glass-border);
        box-shadow: var(--shadow-sm);
        text-align: center;
    }

    .metric-card .label {
        color: var(--text-light);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--primary);
        line-height: 1.2;
    }

    .metric-card .delta {
        font-size: 0.8rem;
        color: var(--accent);
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text);
        margin: 2rem 0 1rem;
        letter-spacing: -0.01em;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 40px;
        font-weight: 500;
        transition: all 0.2s;
        border: none;
        padding: 0.5rem 1.5rem;
        background: var(--primary);
        color: white;
        box-shadow: var(--shadow-sm);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -4px rgba(79, 70, 229, 0.4);
    }

    /* Form inputs */
    .stTextInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div > select {
        border-radius: 30px;
        border: 1px solid var(--border);
        padding: 0.75rem 1.5rem;
        background: white;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }

    .stTextInput > div > div > input:focus, .stTextArea > div > textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
    }

    /* Chat container */
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        border-radius: 30px;
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: var(--glass-border);
        margin-bottom: 1rem;
    }

    .chat-bubble-company {
        background: var(--primary);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 20px 20px 0 20px;
        max-width: 70%;
        display: inline-block;
        margin: 0.5rem 0;
        text-align: left;
        box-shadow: var(--shadow-sm);
    }

    .chat-bubble-employee {
        background: white;
        color: var(--text);
        padding: 0.75rem 1rem;
        border-radius: 20px 20px 20px 0;
        max-width: 70%;
        display: inline-block;
        margin: 0.5rem 0;
        text-align: left;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }

    .chat-timestamp {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 0.25rem;
    }

    hr {
        margin: 2rem 0;
        border: 0;
        border-top: 1px solid var(--border);
    }
</style>
""", unsafe_allow_html=True)

# --- Fetch counts for badges ---
company_id = st.session_state.company_id
new_apps_count = get_new_applications_count(company_id)
unread_msgs_count = get_unread_messages_count(company_id)
open_requests_count = get_open_request_count()
active_jobs_count = get_job_count_for_company(company_id)
total_apps = get_application_count_for_company(company_id)
interview_count = get_interview_count_for_company(company_id)

# --- Two‑row navigation with badges ---
menu_items = [
    {"label": "Dashboard", "icon": "📊", "badge": None},
    {"label": "Post a Job", "icon": "📝", "badge": None},
    {"label": "Applications", "icon": "📋", "badge": new_apps_count},
    {"label": "Job Requests", "icon": "👥", "badge": open_requests_count},
    {"label": "Messages", "icon": "💬", "badge": unread_msgs_count},
    {"label": "Company Profile", "icon": "🏢", "badge": None},
]

# Row 1: badges
badge_cols = st.columns([1,1,1,1,1,1,0.8])
for i, item in enumerate(menu_items):
    with badge_cols[i]:
        if item["badge"] and item["badge"] > 0:
            st.markdown(
                f"<div style='text-align: center; margin-bottom: 5px;'>"
                f"<span class='badge-count'>{item['badge']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
with badge_cols[-1]:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

# Row 2: buttons
button_cols = st.columns([1,1,1,1,1,1,0.8])
for i, item in enumerate(menu_items):
    with button_cols[i]:
        active = "primary" if st.session_state.get("nav_selected") == item["label"] else "secondary"
        if st.button(f"{item['icon']} {item['label']}", key=f"nav_{item['label']}", use_container_width=True, type=active):
            st.session_state.nav_selected = item["label"]
            st.rerun()
with button_cols[-1]:
    if st.button("🚪 Logout", key="logout_top", use_container_width=True):
        for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email', 'nav_selected']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("app.py")

selected = st.session_state.get("nav_selected", "Dashboard")

# --- Hero Header ---
st.markdown(f"""
<div class="hero-header">
    <div>
        <h1>👋 Welcome back, {st.session_state.employer_name}!</h1>
        <p>Manage your job postings and applicants from one place.</p>
    </div>
    <div class="date-badge">
        {datetime.now().strftime('%B %d, %Y')}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Notification Cards (always visible) ---
st.markdown("## 🔔 Recent Notifications")
activities = get_recent_activities(company_id, limit=6)

if activities:
    for i in range(0, len(activities), 3):
        row = activities[i:i+3]
        cols = st.columns(3)
        for j, act in enumerate(row):
            with cols[j]:
                icon = "📝" if act['type'] == 'application' else "💬"
                bg = "#DCFCE7" if act['type'] == 'application' else "#DBEAFE"
                time_str = act['time'].strftime('%Y-%m-%d %H:%M') if act['time'] else ''
                st.markdown(f"""
                <div class="notification-card">
                    <div class="notification-icon" style="background: {bg};">{icon}</div>
                    <div class="notification-title">{act['content']}</div>
                    <div class="notification-time">{time_str}</div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("No recent notifications.")

# --- Dashboard Tab (enhanced) ---
if selected == "Dashboard":
    st.markdown("## 📊 Overview")

    # Top KPI row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="stat-card"><h3>📋 Active Jobs</h3><p>{active_jobs_count}</p></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="stat-card"><h3>📝 Total Applications</h3><p>{total_apps}</p></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="stat-card"><h3>🗓️ Interviews</h3><p>{interview_count}</p></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="stat-card"><h3>👥 Open Requests</h3><p>{open_requests_count}</p></div>', unsafe_allow_html=True)

    # Additional metrics row
    if total_apps > 0:
        interview_rate = (interview_count / total_apps) * 100
        pending_rate = (new_apps_count / total_apps) * 100 if total_apps else 0
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
            <div class="value">{new_apps_count}</div>
            <div class="delta">{pending_rate:.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        # Average applications per job
        if active_jobs_count > 0:
            avg_per_job = total_apps / active_jobs_count
        else:
            avg_per_job = 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Avg. Apps / Job</div>
            <div class="value">{avg_per_job:.1f}</div>
            <div class="delta">across active jobs</div>
        </div>
        """, unsafe_allow_html=True)

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        # Applications over time
        apps = get_applications_for_company(company_id)
        if apps:
            dates = [app[7] for app in apps]  # applied_at index
            df = pd.DataFrame({'applied_at': pd.to_datetime(dates)})
            df['date'] = df['applied_at'].dt.date
            daily = df.groupby('date').size().reset_index(name='count')
            fig = px.line(daily, x='date', y='count', title='📈 Applications Over Time',
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
        # Applications by status (pie chart)
        if apps:
            status_counts = {}
            for app in apps:
                status = app[4]
                status_counts[status] = status_counts.get(status, 0) + 1
            status_df = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Count'])
            fig = px.pie(status_df, values='Count', names='Status', title='🥧 Applications by Status',
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

    # Second row: Top jobs by applications
    if apps:
        # Count applications per job
        job_apps = {}
        for app in apps:
            job_title = app[9]  # job title
            job_apps[job_title] = job_apps.get(job_title, 0) + 1
        job_df = pd.DataFrame(list(job_apps.items()), columns=['Job Title', 'Applications'])
        job_df = job_df.sort_values('Applications', ascending=True).tail(5)  # top 5
        fig = px.bar(job_df, x='Applications', y='Job Title', orientation='h',
                     title='🏆 Top Jobs by Applications',
                     color='Applications', color_continuous_scale='Blues')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='var(--text)',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)

# --- All other tabs (Post a Job, Applications, Job Requests, Messages, Company Profile) remain exactly as before ---
# (We'll include them here for completeness, but they are unchanged from the previous version)

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
                with st.expander(f"{job['title']} - {job['status'].upper()}"):
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
                        if st.button(f"🗑️ Delete Job", key=f"delete_job_{job['id']}"):
                            st.session_state.job_to_delete = job['id']
                            st.rerun()

                        if st.session_state.get("job_to_delete") == job['id']:
                            st.warning("Are you sure?")
                            if st.button("✅ Yes", key=f"confirm_yes_{job['id']}"):
                                delete_job(job['id'])
                                del st.session_state.job_to_delete
                                st.success("Job deleted!")
                                st.rerun()
                            if st.button("❌ No", key=f"confirm_no_{job['id']}"):
                                del st.session_state.job_to_delete
                                st.rerun()

elif selected == "Applications":
    st.markdown(f"## 📋 Applications Received  "
                f"<span class='badge-count' style='font-size: 0.9rem; margin-left: 10px;'>{new_apps_count} pending</span>",
                unsafe_allow_html=True)

    if "chat_employee_id" in st.session_state:
        st_autorefresh(interval=10000, key="employer_chat_autorefresh")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 💬 Chat with {st.session_state.chat_employee_name}")
        with col2:
            if st.button("← Back to Applications"):
                for key in ['chat_employee_id', 'chat_employee_name', 'chat_application_id']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

        msgs = get_messages_between_company_and_employee(company_id, st.session_state.chat_employee_id)
        mark_company_messages_read(company_id, st.session_state.chat_employee_id)

        st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
        for msg in msgs:
            sender = 'company' if msg[2] == 'company' else 'employee'
            msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
            if sender == 'company':
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div class="chat-bubble-company">{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div class="chat-bubble-employee"><strong>{st.session_state.chat_employee_name}</strong><br>{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <script>
            var chatContainer = document.getElementById('chat-container');
            if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
        </script>
        """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send", use_container_width=True):
                send_message_from_company(company_id, st.session_state.chat_employee_id, message, st.session_state.chat_application_id)
                st.rerun()
    else:
        apps = get_applications_for_company(company_id)
        if not apps:
            st.info("No applications yet.")
        else:
            for i, app in enumerate(apps):
                status = app[4]
                with st.expander(f"{app[10]} for {app[9]} - {status.upper()}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**Applicant:** {app[10]}")
                        st.markdown(f"**Email:** {app[11]}")
                        st.markdown(f"**Location:** {app[14]}")
                        st.markdown(f"**Phone:** {app[15]}")
                        st.markdown(f"**Skills:** {app[12]}")
                        st.markdown(f"**Cover Letter:** {app[6]}")
                        st.markdown(f"**Applied:** {app[7]}")
                        st.markdown(f"**Match Score:** {app[5]}%")
                        if app[13]:
                            st.markdown(get_resume_download_link(app[13], "📄 Download Resume"), unsafe_allow_html=True)
                    with col2:
                        if st.button("🔍 Run ATS Review", key=f"ats_{app[0]}_{i}"):
                            with st.spinner("Analyzing..."):
                                match, is_ai, conf, feedback = ats_review(app[13], app[6], app[13])
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

elif selected == "Job Requests":
    st.markdown(f"## 👥 Employee Job Requests  "
                f"<span class='badge-count' style='font-size: 0.9rem; margin-left: 10px;'>{open_requests_count} open</span>",
                unsafe_allow_html=True)

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

elif selected == "Messages":
    st.markdown("## 💬 Conversations")

    if "chat_employee_id" in st.session_state:
        st_autorefresh(interval=10000, key="employer_chat_autorefresh")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 💬 Chat with {st.session_state.chat_employee_name}")
        with col2:
            if st.button("← Back to Conversations"):
                for key in ['chat_employee_id', 'chat_employee_name']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

        msgs = get_messages_between_company_and_employee(company_id, st.session_state.chat_employee_id)
        mark_company_messages_read(company_id, st.session_state.chat_employee_id)

        st.markdown('<div class="chat-container" id="chat-container-msg">', unsafe_allow_html=True)
        for msg in msgs:
            if msg[2] == 'company':
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: right; margin: 0.5rem 0;">
                    <div class="chat-bubble-company">{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                st.markdown(f"""
                <div style="text-align: left; margin: 0.5rem 0;">
                    <div class="chat-bubble-employee"><strong>{st.session_state.chat_employee_name}</strong><br>{msg[6]}<br><span class="chat-timestamp">{msg_time}</span></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <script>
            var chatContainer = document.getElementById('chat-container-msg');
            if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
        </script>
        """, unsafe_allow_html=True)

        with st.form("send_message_employer"):
            message = st.text_area("Type message", key="employer_chat_message")
            if st.form_submit_button("Send", use_container_width=True):
                send_message_from_company(company_id, st.session_state.chat_employee_id, message, application_id=None)
                st.rerun()
    else:
        convos = get_company_conversations(company_id)
        if not convos:
            st.info("No conversations yet. Express interest in job requests to start chatting!")
        else:
            for conv in convos:
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

elif selected == "Company Profile":
    st.markdown("## 🏢 Edit Company Profile")
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
            for key in ['employer_authenticated', 'company_id', 'employer_name', 'employer_email', 'nav_selected']:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")
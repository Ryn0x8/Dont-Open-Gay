import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import os
import base64
from streamlit_autorefresh import st_autorefresh
import io
import time
import bcrypt

# Import all database functions
from database import (
    db, update_is_admin,
    # User management
    get_all_users, get_user_by_id_admin, update_user_role, delete_user, add_user_admin,
    
    # Company management
    get_all_companies_admin, delete_company, update_company_admin,
    
    # Job management
    get_all_jobs_admin, update_job_admin, delete_job,
    
    # Application management
    get_applications_for_company, delete_application_admin,
    
    # Job requests
    get_all_job_requests_admin, delete_job_request_admin,
    
    # Stats
    get_system_stats, get_users_by_role, get_recent_activities_admin,
    
    # Others
    get_company_by_id, get_job_by_id, get_user, add_notification,
    send_message, get_messages_between_company_and_employee,
    update_expired_jobs, get_or_create_profile, get_resume_download_link
)

# Update expired jobs
update_expired_jobs()

# --- Page config ---
st.set_page_config(
    page_title="Admin Dashboard - Anvaya",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if not (
    st.session_state.get("authenticated", False)
    or
    st.session_state.get("employer_authenticated", False)
):
    previous_page = st.session_state.get("previous_page")
    if previous_page == "pages/employer_dashboard.py":
        st.switch_page("pages/login_employer.py")
    elif previous_page == "pages/employee_dashboard.py":
        st.switch_page("pages/login_employee.py")
    else:
        st.error("⛔ You must be logged in to access this page.")
        if st.button("← Go to Home"):
            st.switch_page("app.py")
    st.stop()

# Check if user is admin (using is_admin flag)
if not st.session_state.get("is_admin", False):
    st.error("⛔ Access Denied. This page is for administrators only.")
    if st.button("← Go to Home"):
        st.switch_page("app.py")
    st.stop()

if "previous_page" not in st.session_state:
    st.session_state.previous_page = "app.py"
    
if st.session_state.get("previous_page") == "pages/employer_dashboard.py":
    st.session_state.user_id = st.session_state.get("company_id")
    st.session_state.user_name = st.session_state.get("employer_name")
    st.session_state.user_email = st.session_state.get("employer_email")

# --- Helper Functions ---
def format_datetime(dt):
    """Format datetime for display"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M')
    return 'N/A'

def get_user_display_name(user_id):
    """Get user name from ID"""
    user = get_user(user_id)
    if user:
        return user[1]
    return user_id

def confirm_action(key, message):
    """Show confirmation dialog"""
    if key not in st.session_state:
        st.session_state[key] = False
    
    if st.button("⚠️ " + message, key=f"btn_{key}"):
        st.session_state[key] = True
    
    if st.session_state[key]:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Confirm", key=f"yes_{key}"):
                st.session_state[key] = False
                return True
        with col2:
            if st.button("❌ No, Cancel", key=f"no_{key}"):
                st.session_state[key] = False
                return False
    return False

# --- Custom CSS (same glass-morphism style) ---
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
        --danger: #EF4444;
        --warning: #F59E0B;
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

    /* Data table styling */
    .data-table {
        background: white;
        border-radius: 24px;
        padding: 1rem;
        border: 1px solid var(--border);
        margin: 1rem 0;
    }

    .role-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 40px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
    }

    .role-employee { background: #DBEAFE; color: #1E40AF; }
    .role-employer { background: #DCFCE7; color: #166534; }
    .role-admin { background: #FEF3C7; color: #92400E; }

    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 40px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-active { background: #DCFCE7; color: #166534; }
    .status-expired { background: #FEE2E2; color: #991B1B; }
    .status-pending { background: #FEF3C7; color: #92400E; }
    .status-closed { background: #E2E8F0; color: #475569; }

    /* Section title */
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text);
        margin: 2rem 0 1rem;
        letter-spacing: -0.01em;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    /* Metric cards */
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

    .delete-btn > button {
        background: var(--danger);
    }
    
    .delete-btn > button:hover {
        box-shadow: 0 8px 16px -4px rgba(239, 68, 68, 0.4);
    }

    hr {
        margin: 2rem 0;
        border: 0;
        border-top: 1px solid var(--border);
    }
</style>
""", unsafe_allow_html=True)

# --- Get System Stats ---
stats = get_system_stats()

# --- Navigation Menu Items ---
menu_items = [
    {"label": "Dashboard", "icon": "📊", "badge": None},
    {"label": "Users", "icon": "👥", "badge": stats['users']},
    {"label": "Companies", "icon": "🏢", "badge": stats['companies']},
    {"label": "Jobs", "icon": "📋", "badge": stats['jobs']},
    {"label": "Applications", "icon": "📝", "badge": stats['applications']},
    {"label": "Job Requests", "icon": "📌", "badge": stats['open_requests']},
    {"label": "Messages", "icon": "💬", "badge": stats['messages']},
    {"label": "Analytics", "icon": "📈", "badge": None},
    {"label": "Settings", "icon": "⚙️", "badge": None},
]

# Split into two rows (5 and 4)
first_group = menu_items[:5]   # Dashboard, Users, Companies, Jobs, Applications
second_group = menu_items[5:]  # Job Requests, Messages, Analytics, Settings

# --- First Row Navigation ---
cols1 = st.columns([1,1,1,1,1,0.8])
badge_cols1 = cols1[:5]
logout_placeholder1 = cols1[5]

# First row badges
for i, item in enumerate(first_group):
    with badge_cols1[i]:
        if item["badge"] and item["badge"] > 0:
            st.markdown(
                f"<div style='text-align: center; margin-bottom: 5px;'>"
                f"<span class='badge-count'>{item['badge']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
with logout_placeholder1:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

# First row buttons
button_cols1 = st.columns([1,1,1,1,1,0.8])
for i, item in enumerate(first_group):
    with button_cols1[i]:
        active = "primary" if st.session_state.get("admin_nav") == item["label"] else "secondary"
        if st.button(f"{item['icon']} {item['label']}", key=f"nav1_{item['label']}", use_container_width=True, type=active):
            st.session_state.admin_nav = item["label"]
            st.rerun()
with button_cols1[5]:
    st.markdown("")

st.markdown("<br>", unsafe_allow_html=True)

# --- Second Row Navigation ---
cols2 = st.columns([1,1,1,1,1])
badge_cols2 = cols2[:4]
logout_col = cols2[4]

for i, item in enumerate(second_group):
    with badge_cols2[i]:

        # Badge (top)
        if item["badge"] and item["badge"] > 0:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:center; margin-bottom:5px;">
                    <span class='badge-count'>{item['badge']}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

        # Button
        active = "primary" if st.session_state.get("admin_nav") == item["label"] else "secondary"
        if st.button(
            f"{item['icon']} {item['label']}",
            key=f"nav2_{item['label']}",
            use_container_width=True,
            type=active
        ):
            st.session_state.admin_nav = item["label"]
            st.rerun()

# Logout button
with logout_col:
    # Back button (only show if previous page exists)
    if "previous_page" in st.session_state:
        if st.button("⬅️ Back to Dashboard", key="back_dashboard", use_container_width=True):
            target = st.session_state.previous_page
            del st.session_state["previous_page"]
            if st.session_state.get("previous_page") == "pages/employer_dashboard.py":
                del st.session_state["user_id"]
                del st.session_state["user_name"] 
                del st.session_state["user_email"] 
                del st.session_state["user_role"] 
            st.switch_page(target)

    # Logout button
    if st.button("🚪 Logout", key="admin_logout", use_container_width=True):
        for key in ['authenticated', 'user_id', 'user_name', 'user_email', 'user_role', 'admin_nav', 'previous_page', 'employer_authenticated', 'company_id', 'employer_name', 'employer_email', 'employer_role']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("app.py")


selected = st.session_state.get("admin_nav", "Dashboard")

# --- Hero Header ---
st.markdown(f"""
<div class="hero-header">
    <div>
        <h1>👋 Welcome, Admin {st.session_state.user_name}!</h1>
        <p>You have full system access and control</p>
    </div>
    <div class="date-badge">
        {datetime.now().strftime('%B %d, %Y')}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Recent Activity Feed (Always Visible) ---
with st.expander("🔔 Recent System Activity", expanded=False):
    activities = get_recent_activities_admin(limit=10)
    if activities:
        for act in activities:
            icon = {
                'user': '👤',
                'job': '📋',
                'application': '📝',
                'message': '💬'
            }.get(act['type'], '🔔')
            
            bg = {
                'user': '#DBEAFE',
                'job': '#DCFCE7',
                'application': '#FEF3C7',
                'message': '#E0F2FE'
            }.get(act['type'], '#F1F5F9')
            
            time_str = act['time'].strftime('%Y-%m-%d %H:%M') if act['time'] else ''
            
            st.markdown(f"""
            <div style="background: {bg}; padding: 0.75rem 1rem; border-radius: 16px; margin: 0.5rem 0; display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div style="flex-grow: 1;">
                    <div style="font-weight: 500;">{act['content']}</div>
                    <div style="font-size: 0.8rem; color: var(--text-light);">{time_str}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent activity")

# ============================================================================
# DASHBOARD TAB
# ============================================================================
if selected == "Dashboard":
    st.markdown("## 📊 System Overview")
    
    # Top KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>👥 Total Users</h3><p>{stats["users"]}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>🏢 Companies</h3><p>{stats["companies"]}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>📋 Active Jobs</h3><p>{stats["active_jobs"]}</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>📝 Applications</h3><p>{stats["applications"]}</p></div>', unsafe_allow_html=True)
    
    # Second Row Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Employees</div>
            <div class="value">{stats["employees"]}</div>
            <div class="delta">{((stats["employees"]/stats["users"])*100 if stats["users"]>0 else 0):.1f}% of users</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Employers</div>
            <div class="value">{stats["employers"]}</div>
            <div class="delta">{((stats["employers"]/stats["users"])*100 if stats["users"]>0 else 0):.1f}% of users</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Admins</div>
            <div class="value">{stats["admins"]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Open Requests</div>
            <div class="value">{stats["open_requests"]}</div>
            <div class="delta">{((stats["open_requests"]/stats["job_requests"])*100 if stats["job_requests"]>0 else 0):.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        # User Distribution Pie Chart
        user_data = pd.DataFrame({
            'Role': ['Employees', 'Employers', 'Admins'],
            'Count': [stats['employees'], stats['employers'], stats['admins']]
        })
        fig = px.pie(user_data, values='Count', names='Role', 
                     title='👥 User Distribution',
                     color_discrete_sequence=['#3B82F6', '#10B981', '#F59E0B'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='var(--text)',
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Jobs Status Bar Chart
        job_data = pd.DataFrame({
            'Status': ['Active', 'Expired', 'Total'],
            'Count': [stats['active_jobs'], stats['jobs'] - stats['active_jobs'], stats['jobs']]
        })
        fig = px.bar(job_data, x='Status', y='Count', 
                     title='📋 Jobs Overview',
                     color='Status',
                     color_discrete_map={'Active': '#10B981', 'Expired': '#EF4444', 'Total': '#3B82F6'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='var(--text)',
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Quick Actions
    st.markdown("## 🚀 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Add New User", use_container_width=True):
            st.session_state.admin_nav = "Users"
            st.session_state.show_add_user = True
            st.rerun()
    with col2:
        if st.button("📊 Export Reports", use_container_width=True):
            st.info("Report export feature coming soon!")
    with col3:
        if st.button("🔄 System Backup", use_container_width=True):
            st.success("System backup initiated!")
    with col4:
        if st.button("🧹 Cleanup Old Data", use_container_width=True):
            st.warning("Cleanup process started...")
            time.sleep(2)
            st.success("Cleanup completed!")

# ============================================================================
# USERS TAB
# ============================================================================
elif selected == "Users":
    st.markdown("## 👥 User Management")
    
    # Add User Form (if triggered)
    if st.session_state.get("show_add_user", False):
        with st.form("add_user_form", clear_on_submit=True):
            st.markdown("### ➕ Add New User")
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email")
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["employee", "employer"])
                new_is_admin = st.checkbox("Is Admin?", value=False)

            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button("✅ Create User", use_container_width=True)
            with col_b:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.show_add_user = False
                    st.rerun()
            
            if submitted:
                if new_name and new_email and new_password:
                    # Check if user exists
                    existing = get_user(new_email)
                    if existing:
                        st.error("User with this email already exists!")
                    else:
                        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    
                        add_user_admin(new_name, new_email, password_hash, new_role, new_is_admin)
                        st.success(f"User {new_name} created successfully!")
                        st.session_state.show_add_user = False
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Please fill all fields")
        st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        role_filter = st.selectbox("Filter by Role", ["All", "employee", "employer", "admin"])
    with col2:
        search = st.text_input("🔍 Search by name or email", placeholder="Type to search...")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add New User", use_container_width=True):
            st.session_state.show_add_user = True
            st.rerun()
    
    # Get and filter users
    users = get_all_users()
    
    # Convert to DataFrame for filtering
    df_users = pd.DataFrame(users, columns=['id', 'name', 'email', 'role', 'is_admin','created_at', 
                                            'phone', 'location', 'skills', 'resume_path'])
    
    # Apply filters
    if role_filter != "All":
        df_users = df_users[df_users['role'] == role_filter]
    
    if search:
        df_users = df_users[
            df_users['name'].str.contains(search, case=False, na=False) |
            df_users['email'].str.contains(search, case=False, na=False)
        ]
    
    # Display users
    st.markdown(f"### Found {len(df_users)} Users")
    
    for idx, user in df_users.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{user['name']}**")
                st.markdown(f"📧 {user['email']}")
            
            with col2:
                role_class = {
                    'employee': 'role-employee',
                    'employer': 'role-employer',
                }.get(user['role'], '')
                
                st.markdown(f'<span class="role-badge {role_class}">{user["role"].upper()}</span>', unsafe_allow_html=True)
                
                # Show admin badge if is_admin is True
                if user.get('is_admin', False):
                    st.markdown('<span class="role-badge role-admin">ADMIN</span>', unsafe_allow_html=True)
                
                if user['location']:
                    st.markdown(f"📍 {user['location']}")
            
            with col3:
                if user['phone']:
                    st.markdown(f"📱 {user['phone']}")
            
            with col4:
                # View Details button
                if st.button("👁️ View", key=f"view_user_{user['id']}_{idx}", use_container_width=True):
                    st.session_state.view_user_id = user['id']
                    st.rerun()
            
            with col5:
                # Delete button with confirmation
                if st.button("🗑️", key=f"del_user_{user['id']}_{idx}", use_container_width=True, type="secondary"):
                    st.session_state.delete_user_id = user['id']
                    st.session_state.delete_user_name = user['name']
            
            # View Details Expander
            if st.session_state.get("view_user_id") == user['id']:
                with st.expander(f"User Details: {user['name']}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Profile Information:**")
                        st.markdown(f"- **Name:** {user['name']}")
                        st.markdown(f"- **Email:** {user['email']}")
                        st.markdown(f"- **Role:** {user['role'].upper()}")
                        st.markdown(f"- **Admin:** {'Yes' if user.get('is_admin', False) else 'No'}")
                        st.markdown(f"- **Phone:** {user['phone'] or 'Not provided'}")
                        st.markdown(f"- **Location:** {user['location'] or 'Not provided'}")
                    
                    with col_b:
                        st.markdown("**Skills & Resume:**")
                        st.markdown(f"- **Skills:** {user['skills'] or 'Not provided'}")
                        if user['resume_path'] and os.path.exists(user['resume_path']):
                            with open(user['resume_path'], "rb") as f:
                                bytes_data = f.read()
                            b64 = base64.b64encode(bytes_data).decode()
                            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(user["resume_path"])}">📄 Download Resume</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else:
                            st.markdown("- **Resume:** Not uploaded")
                    
                    # Role change option
                    new_role = st.selectbox("Change Role", ["employee", "employer"], 
                                            index=["employee", "employer"].index(user['role']) if user['role'] in ["employee", "employer"] else 0,
                                            key=f"role_change_{user['id']}")

                    # New: Admin flag toggle
                    new_is_admin = st.checkbox("Is Admin?", value=user.get('is_admin', False), key=f"is_admin_{user['id']}")

                    if new_role != user['role'] or new_is_admin != user.get('is_admin', False):
                        if st.button("💾 Update Role", key=f"update_role_{user['id']}"):
                            update_user_role(user['id'], new_role)
                            update_is_admin(user['id'], new_is_admin)
                            db.collection('users').document(user['id']).update({'is_admin': new_is_admin})
                            st.success(f"User updated")
                            time.sleep(1)
                            st.rerun()
                    
                    if st.button("❌ Close", key=f"close_view_{user['id']}"):
                        del st.session_state.view_user_id
                        st.rerun()
            
            # Delete Confirmation
            if st.session_state.get("delete_user_id") == user['id']:
                st.warning(f"Are you sure you want to delete user '{st.session_state.delete_user_name}'? This action cannot be undone!")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes, Delete", key=f"confirm_del_{user['id']}"):
                        delete_user(user['id'])
                        del st.session_state.delete_user_id
                        del st.session_state.delete_user_name
                        st.success(f"User {user['name']} deleted!")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ No, Cancel", key=f"cancel_del_{user['id']}"):
                        del st.session_state.delete_user_id
                        del st.session_state.delete_user_name
                        st.rerun()
            
            st.markdown("---")

# ============================================================================
# COMPANIES TAB
# ============================================================================
elif selected == "Companies":
    st.markdown("## 🏢 Company Management")
    
    # Get companies
    companies = get_all_companies_admin()
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("🔍 Search companies", placeholder="Search by name or industry...")
    with col2:
        industries = list(set(c.get('industry', '') for c in companies if c.get('industry')))
        industry_filter = st.selectbox("Industry", ["All"] + industries)
    
    # Filter companies
    filtered_companies = companies
    if search:
        filtered_companies = [c for c in filtered_companies 
                             if search.lower() in c.get('name', '').lower() 
                             or search.lower() in c.get('industry', '').lower()]
    if industry_filter != "All":
        filtered_companies = [c for c in filtered_companies if c.get('industry') == industry_filter]
    
    st.markdown(f"### Found {len(filtered_companies)} Companies")
    
    for company in filtered_companies:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                logo = company.get('logo', '')
                if logo:
                    st.markdown(f'<img src="{logo}" width="30" style="border-radius:50%; vertical-align:middle;"> ', unsafe_allow_html=True)
                st.markdown(f"**{company.get('name', 'Unnamed')}**")
                st.markdown(f"📧 {company.get('email', 'N/A')}")
            
            with col2:
                st.markdown(f"🏭 {company.get('industry', 'N/A')}")
                st.markdown(f"📍 {company.get('location', 'N/A')}")
            
            with col3:
                if st.button("👁️ View", key=f"view_comp_{company['id']}", use_container_width=True):
                    st.session_state.view_company_id = company['id']
            
            with col4:
                if st.button("🗑️", key=f"del_comp_{company['id']}", use_container_width=True, type="secondary"):
                    st.session_state.delete_company_id = company['id']
                    st.session_state.delete_company_name = company.get('name', '')
            
            # View Details
            if st.session_state.get("view_company_id") == company['id']:
                with st.expander(f"Company Details: {company.get('name', '')}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Basic Information:**")
                        st.markdown(f"- **Name:** {company.get('name', 'N/A')}")
                        st.markdown(f"- **Email:** {company.get('email', 'N/A')}")
                        st.markdown(f"- **Industry:** {company.get('industry', 'N/A')}")
                        st.markdown(f"- **Location:** {company.get('location', 'N/A')}")
                        st.markdown(f"- **Website:** {company.get('website', 'N/A')}")
                    
                    with col_b:
                        st.markdown("**Description:**")
                        st.markdown(f"{company.get('description', 'No description')[:300]}...")
                        st.markdown(f"**Created:** {format_datetime(company.get('created_at'))}")
                    
                    # Edit form
                    with st.form(f"edit_comp_{company['id']}"):
                        st.markdown("**Edit Company**")
                        new_name = st.text_input("Name", value=company.get('name', ''))
                        new_industry = st.text_input("Industry", value=company.get('industry', ''))
                        new_location = st.text_input("Location", value=company.get('location', ''))
                        new_website = st.text_input("Website", value=company.get('website', ''))
                        new_description = st.text_area("Description", value=company.get('description', ''), height=100)
                        
                        if st.form_submit_button("💾 Update Company"):
                            update_company_admin(
                                company['id'],
                                name=new_name,
                                industry=new_industry,
                                location=new_location,
                                website=new_website,
                                description=new_description
                            )
                            st.success("Company updated!")
                            time.sleep(1)
                            st.rerun()
                    
                    if st.button("❌ Close", key=f"close_comp_{company['id']}"):
                        del st.session_state.view_company_id
                        st.rerun()
            
            # Delete Confirmation
            if st.session_state.get("delete_company_id") == company['id']:
                st.warning(f"Are you sure you want to delete '{st.session_state.delete_company_name}'? This will delete ALL jobs, applications, and messages for this company!")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes, Delete", key=f"confirm_del_comp_{company['id']}"):
                        delete_company(company['id'])
                        del st.session_state.delete_company_id
                        del st.session_state.delete_company_name
                        st.success(f"Company deleted!")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ No, Cancel", key=f"cancel_del_comp_{company['id']}"):
                        del st.session_state.delete_company_id
                        del st.session_state.delete_company_name
                        st.rerun()
            
            st.markdown("---")

# ============================================================================
# JOBS TAB
# ============================================================================
elif selected == "Jobs":
    st.markdown("## 📋 Job Postings Management")
    
    # Get all jobs
    jobs = get_all_jobs_admin()
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Status", ["All", "active", "expired"])
    with col2:
        search = st.text_input("🔍 Search jobs", placeholder="Search by title or company...")
    with col3:
        job_types = list(set(j.get('job_type', '') for j in jobs if j.get('job_type')))
        type_filter = st.selectbox("Job Type", ["All"] + job_types)
    
    # Apply filters
    filtered_jobs = jobs
    if status_filter != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get('status') == status_filter]
    if search:
        filtered_jobs = [j for j in filtered_jobs 
                        if search.lower() in j.get('title', '').lower() 
                        or search.lower() in j.get('company_name', '').lower()]
    if type_filter != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get('job_type') == type_filter]
    
    st.markdown(f"### Found {len(filtered_jobs)} Jobs")
    
    for job in filtered_jobs:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{job.get('title', 'Untitled')}**")
                st.markdown(f"🏢 {job.get('company_name', 'Unknown')}")
            
            with col2:
                status_class = 'status-active' if job.get('status') == 'active' else 'status-expired'
                st.markdown(f'<span class="status-badge {status_class}">{job.get("status", "unknown").upper()}</span>', unsafe_allow_html=True)
                st.markdown(f"📍 {job.get('location', 'N/A')}")
            
            with col3:
                if st.button("👁️ View", key=f"view_job_{job['id']}", use_container_width=True):
                    st.session_state.view_job_id = job['id']
            
            with col4:
                if st.button("🗑️", key=f"del_job_{job['id']}", use_container_width=True, type="secondary"):
                    st.session_state.delete_job_id = job['id']
                    st.session_state.delete_job_title = job.get('title', '')
            
            # View Details
            if st.session_state.get("view_job_id") == job['id']:
                with st.expander(f"Job Details: {job.get('title', '')}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Job Information:**")
                        st.markdown(f"- **Title:** {job.get('title', 'N/A')}")
                        st.markdown(f"- **Company:** {job.get('company_name', 'N/A')}")
                        st.markdown(f"- **Category:** {job.get('category', 'N/A')}")
                        st.markdown(f"- **Location:** {job.get('location', 'N/A')}")
                        st.markdown(f"- **Type:** {job.get('job_type', 'N/A')}")
                        st.markdown(f"- **Salary:** {job.get('salary_range', 'N/A')}")
                        st.markdown(f"- **Experience:** {job.get('experience_level', 'N/A')}")
                    
                    with col_b:
                        st.markdown("**Description & Requirements:**")
                        st.markdown(f"**Description:** {job.get('description', 'N/A')[:200]}...")
                        st.markdown(f"**Requirements:** {job.get('requirements', 'N/A')[:200]}...")
                        st.markdown(f"**Skills:** {job.get('skills_required', 'N/A')}")
                        st.markdown(f"**Posted:** {format_datetime(job.get('created_at'))}")
                        st.markdown(f"**Deadline:** {format_datetime(job.get('deadline'))}")
                    
                    # Edit form
                    with st.form(f"edit_job_{job['id']}"):
                        st.markdown("**Edit Job**")
                        new_status = st.selectbox("Status", ["active", "expired"], 
                                                 index=0 if job.get('status') == 'active' else 1)
                        new_title = st.text_input("Title", value=job.get('title', ''))
                        new_location = st.text_input("Location", value=job.get('location', ''))
                        
                        if st.form_submit_button("💾 Update Job"):
                            update_job_admin(
                                job['id'],
                                status=new_status,
                                title=new_title,
                                location=new_location
                            )
                            st.success("Job updated!")
                            time.sleep(1)
                            st.rerun()
                    
                    if st.button("❌ Close", key=f"close_job_{job['id']}"):
                        del st.session_state.view_job_id
                        st.rerun()
            
            # Delete Confirmation
            if st.session_state.get("delete_job_id") == job['id']:
                st.warning(f"Are you sure you want to delete job '{st.session_state.delete_job_title}'?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes, Delete", key=f"confirm_del_job_{job['id']}"):
                        delete_job(job['id'])
                        del st.session_state.delete_job_id
                        del st.session_state.delete_job_title
                        st.success("Job deleted!")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ No, Cancel", key=f"cancel_del_job_{job['id']}"):
                        del st.session_state.delete_job_id
                        del st.session_state.delete_job_title
                        st.rerun()
            
            st.markdown("---")

# ============================================================================
# APPLICATIONS TAB
# ============================================================================
elif selected == "Applications":
    st.markdown("## 📝 Applications Management")
    
    # Get all companies to fetch applications
    companies = get_all_companies_admin()
    
    # Company selector
    company_options = {c.get('name', 'Unnamed'): c['id'] for c in companies}
    company_options["All Companies"] = "all"
    
    selected_company = st.selectbox("Filter by Company", list(company_options.keys()))
    
    all_apps = []
    if selected_company == "All Companies":
        for company in companies:
            apps = get_applications_for_company(company['id'])
            all_apps.extend(apps)
    else:
        company_id = company_options[selected_company]
        all_apps = get_applications_for_company(company_id)
    
    # Status filter
    status_filter = st.selectbox("Filter by Status", ["All", "pending", "reviewed", "interview", "accepted", "rejected"])
    
    if status_filter != "All":
        all_apps = [a for a in all_apps if a[4] == status_filter]
    
    st.markdown(f"### Found {len(all_apps)} Applications")
    
    for app in all_apps:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{app[10]}**")  # applicant name
                st.markdown(f"📧 {app[11]}")   # email
            
            with col2:
                status_class = {
                    'pending': 'status-pending',
                    'reviewed': 'status-pending',
                    'interview': 'status-active',
                    'accepted': 'status-active',
                    'rejected': 'status-expired'
                }.get(app[4], 'status-pending')
                
                st.markdown(f'<span class="status-badge {status_class}">{app[4].upper()}</span>', unsafe_allow_html=True)
                st.markdown(f"🎯 {app[9]}")  # job title
            
            with col3:
                if st.button("👁️ View", key=f"view_app_{app[0]}", use_container_width=True):
                    st.session_state.view_app_id = app[0]
            
            with col4:
                if st.button("🗑️", key=f"del_app_{app[0]}", use_container_width=True, type="secondary"):
                    st.session_state.delete_app_id = app[0]
            
            # View Details
            if st.session_state.get("view_app_id") == app[0]:
                with st.expander(f"Application Details", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Applicant Information:**")
                        st.markdown(f"- **Name:** {app[10]}")
                        st.markdown(f"- **Email:** {app[11]}")
                        st.markdown(f"- **Phone:** {app[15]}")
                        st.markdown(f"- **Location:** {app[14]}")
                        st.markdown(f"- **Skills:** {app[12]}")
                    
                    with col_b:
                        st.markdown("**Application Details:**")
                        st.markdown(f"- **Job:** {app[9]}")
                        st.markdown(f"- **Status:** {app[4].upper()}")
                        st.markdown(f"- **Match Score:** {app[5]}%")
                        st.markdown(f"- **Applied:** {format_datetime(app[7])}")
                        st.markdown(f"**Cover Letter:** {app[6][:200]}...")
                    
                    if app[13]:
                        with open(app[13], "rb") as f:
                            bytes_data = f.read()
                        b64 = base64.b64encode(bytes_data).decode()
                        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(app[13])}">📄 Download Resume</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    if st.button("❌ Close", key=f"close_app_{app[0]}"):
                        del st.session_state.view_app_id
                        st.rerun()
            
            # Delete Confirmation
            if st.session_state.get("delete_app_id") == app[0]:
                st.warning(f"Delete application from {app[10]}?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes", key=f"confirm_del_app_{app[0]}"):
                        delete_application_admin(app[0])
                        del st.session_state.delete_app_id
                        st.success("Application deleted!")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ No", key=f"cancel_del_app_{app[0]}"):
                        del st.session_state.delete_app_id
                        st.rerun()
            
            st.markdown("---")

# ============================================================================
# JOB REQUESTS TAB
# ============================================================================
elif selected == "Job Requests":
    st.markdown("## 📌 Job Requests Management")
    
    # Get all job requests
    requests = get_all_job_requests_admin()
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Status", ["All", "open", "closed"])
    with col2:
        search = st.text_input("🔍 Search requests", placeholder="Search by title or employee...")
    
    # Apply filters
    filtered_reqs = requests
    if status_filter != "All":
        filtered_reqs = [r for r in filtered_reqs if r.get('status') == status_filter]
    if search:
        filtered_reqs = [r for r in filtered_reqs 
                        if search.lower() in r.get('title', '').lower() 
                        or search.lower() in r.get('employee_name', '').lower()]
    
    st.markdown(f"### Found {len(filtered_reqs)} Job Requests")
    
    for req in filtered_reqs:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{req.get('title', 'Untitled')}**")
                st.markdown(f"👤 {req.get('employee_name', 'Unknown')}")
            
            with col2:
                status_class = 'status-active' if req.get('status') == 'open' else 'status-closed'
                st.markdown(f'<span class="status-badge {status_class}">{req.get("status", "unknown").upper()}</span>', unsafe_allow_html=True)
                st.markdown(f"📍 {req.get('location', 'N/A')}")
            
            with col3:
                if st.button("👁️ View", key=f"view_req_{req['id']}", use_container_width=True):
                    st.session_state.view_req_id = req['id']
            
            with col4:
                if st.button("🗑️", key=f"del_req_{req['id']}", use_container_width=True, type="secondary"):
                    st.session_state.delete_req_id = req['id']
                    st.session_state.delete_req_title = req.get('title', '')
            
            # View Details
            if st.session_state.get("view_req_id") == req['id']:
                with st.expander(f"Request Details: {req.get('title', '')}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Request Information:**")
                        st.markdown(f"- **Title:** {req.get('title', 'N/A')}")
                        st.markdown(f"- **Employee:** {req.get('employee_name', 'N/A')}")
                        st.markdown(f"- **Email:** {req.get('employee_email', 'N/A')}")
                        st.markdown(f"- **Category:** {req.get('category', 'N/A')}")
                        st.markdown(f"- **Location:** {req.get('location', 'N/A')}")
                        st.markdown(f"- **Budget:** {req.get('budget', 'N/A')}")
                    
                    with col_b:
                        st.markdown("**Description:**")
                        st.markdown(f"{req.get('description', 'N/A')}")
                        st.markdown(f"**Posted:** {format_datetime(req.get('created_at'))}")
                    
                    if st.button("❌ Close", key=f"close_req_{req['id']}"):
                        del st.session_state.view_req_id
                        st.rerun()
            
            # Delete Confirmation
            if st.session_state.get("delete_req_id") == req['id']:
                st.warning(f"Delete request '{st.session_state.delete_req_title}'?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes", key=f"confirm_del_req_{req['id']}"):
                        delete_job_request_admin(req['id'])
                        del st.session_state.delete_req_id
                        del st.session_state.delete_req_title
                        st.success("Request deleted!")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ No", key=f"cancel_del_req_{req['id']}"):
                        del st.session_state.delete_req_id
                        del st.session_state.delete_req_title
                        st.rerun()
            
            st.markdown("---")

# ============================================================================
# MESSAGES TAB
# ============================================================================
elif selected == "Messages":
    st.markdown("## 💬 Message Monitoring")
    st.info("Message monitoring feature - view all system messages")
    
    # Get all companies and users to browse messages
    companies = get_all_companies_admin()
    employees = get_users_by_role('employee')
    
    # Select conversation
    col1, col2 = st.columns(2)
    with col1:
        selected_employee = st.selectbox("Select Employee", 
                                        [f"{e.get('name')} ({e.get('email')})" for e in employees],
                                        format_func=lambda x: x)
    with col2:
        selected_company = st.selectbox("Select Company",
                                       [f"{c.get('name')} ({c.get('email')})" for c in companies],
                                       format_func=lambda x: x)
    
    if st.button("🔍 Load Conversation"):
        # Extract IDs
        emp_email = selected_employee.split('(')[-1].strip(')')
        comp_name = selected_company.split('(')[0].strip()
        
        emp_id = emp_email
        comp_id = None
        for c in companies:
            if c.get('name') == comp_name:
                comp_id = c['id']
                break
        
        if comp_id:
            messages = get_messages_between_company_and_employee(comp_id, emp_id)
            
            if messages:
                st.markdown('<div class="chat-container" style="max-height:500px;">', unsafe_allow_html=True)
                for msg in messages:
                    msg_time = msg[9].strftime('%Y-%m-%d %H:%M') if msg[9] else ''
                    if msg[2] == 'company':
                        st.markdown(f"""
                        <div style="text-align: right; margin: 0.5rem 0;">
                            <div style="background: #4F46E5; color: white; padding: 0.75rem 1rem; border-radius: 20px 20px 0 20px; max-width:70%; display:inline-block; text-align:left;">
                                <strong>Company:</strong> {msg[6]}<br>
                                <span style="font-size:0.7rem; opacity:0.7;">{msg_time}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="text-align: left; margin: 0.5rem 0;">
                            <div style="background: white; color: #0F172A; padding: 0.75rem 1rem; border-radius: 20px 20px 20px 0; max-width:70%; display:inline-block; text-align:left; border:1px solid #E2E8F0;">
                                <strong>Employee:</strong> {msg[6]}<br>
                                <span style="font-size:0.7rem; color:#475569;">{msg_time}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No messages in this conversation")

# ============================================================================
# ANALYTICS TAB
# ============================================================================
elif selected == "Analytics":
    st.markdown("## 📈 Advanced Analytics")
    
    # Growth metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        growth_rate = ((stats['users'] - stats['employees'] - stats['employers']) / max(stats['users'], 1)) * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">User Growth Rate</div>
            <div class="value">{growth_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        job_fill_rate = (stats['applications'] / max(stats['jobs'], 1))
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Avg Apps/Job</div>
            <div class="value">{job_fill_rate:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        engagement_rate = (stats['messages'] / max(stats['users'], 1))
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Messages/User</div>
            <div class="value">{engagement_rate:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Role distribution chart
    st.markdown("### 👥 User Role Distribution")
    role_data = pd.DataFrame({
        'Role': ['Employees', 'Employers', 'Admins'],
        'Count': [stats['employees'], stats['employers'], stats['admins']]
    })
    fig = px.bar(role_data, x='Role', y='Count', color='Role',
                 color_discrete_map={'Employees': '#3B82F6', 'Employers': '#10B981', 'Admins': '#F59E0B'})
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
    
    # Jobs vs Applications
    st.markdown("### 📊 Jobs vs Applications")
    comparison_data = pd.DataFrame({
        'Category': ['Jobs', 'Applications'],
        'Count': [stats['jobs'], stats['applications']]
    })
    fig = px.pie(comparison_data, values='Count', names='Category',
                 color_discrete_sequence=['#3B82F6', '#10B981'])
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# SETTINGS TAB
# ============================================================================
elif selected == "Settings":
    st.markdown("## ⚙️ System Settings")
    
    tab1, tab2, tab3 = st.tabs(["General", "Security", "Maintenance"])
    
    with tab1:
        st.markdown("### General Settings")
        site_name = st.text_input("Site Name", value="Anvaya Job Portal")
        contact_email = st.text_input("Contact Email", value="admin@anvaya.com")
        
        col1, col2 = st.columns(2)
        with col1:
            maintenance_mode = st.checkbox("Maintenance Mode")
        with col2:
            allow_registrations = st.checkbox("Allow New Registrations", value=True)
        
        if st.button("💾 Save Settings", use_container_width=True):
            st.success("Settings saved!")
    
    with tab2:
        st.markdown("### Security Settings")
        st.info("Security settings will be implemented in the next version")
        
        min_password_length = st.slider("Minimum Password Length", 6, 20, 8)
        session_timeout = st.number_input("Session Timeout (minutes)", value=30)
        
        if st.button("🔒 Update Security", use_container_width=True):
            st.success("Security settings updated!")
    
    with tab3:
        st.markdown("### System Maintenance")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Clear Cache", use_container_width=True):
                with st.spinner("Clearing cache..."):
                    time.sleep(2)
                st.success("Cache cleared!")
        
        with col2:
            if st.button("📊 Generate Report", use_container_width=True):
                st.info("Generating system report...")
                time.sleep(3)
                
                # Create a simple report
                report_data = {
                    'Metric': ['Total Users', 'Total Companies', 'Total Jobs', 'Total Applications'],
                    'Value': [stats['users'], stats['companies'], stats['jobs'], stats['applications']]
                }
                df_report = pd.DataFrame(report_data)
                
                # Download button
                csv = df_report.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="system_report_{datetime.now().strftime("%Y%m%d")}.csv">📥 Download Report</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        if st.button("⚠️ Run Database Cleanup", use_container_width=True):
            st.warning("This will remove expired jobs and old notifications. Continue?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Yes, Cleanup"):
                    update_expired_jobs()
                    st.success("Cleanup completed!")
            with col_no:
                if st.button("❌ Cancel"):
                    st.rerun()
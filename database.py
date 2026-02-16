import sqlite3

DB_PATH = "dbs/anvaya.db"

def connect():
    """Return a connection with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def create_tables():
    """Create all necessary tables if they don't exist."""
    conn = connect()
    c = conn.cursor()

    # Users table (already exists, but ensure columns)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    # Employee profiles (extends users)
    c.execute("""
    CREATE TABLE IF NOT EXISTS employee_profiles (
        user_id INTEGER PRIMARY KEY,
        phone TEXT,
        location TEXT,
        profile_pic TEXT,
        resume_path TEXT,
        skills TEXT,
        experience_level TEXT,
        preferred_job_type TEXT,
        expected_salary TEXT,
        bio TEXT,
        linkedin_url TEXT,
        github_url TEXT,
        portfolio_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # Companies
    c.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        logo TEXT,
        description TEXT,
        industry TEXT,
        location TEXT,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Jobs
    c.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        company_name TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT,
        description TEXT,
        requirements TEXT,
        location TEXT,
        job_type TEXT,
        salary_range TEXT,
        experience_level TEXT,
        skills_required TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deadline TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )""")

    # Applications
    c.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        match_score FLOAT,
        cover_letter TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (employee_id) REFERENCES users(id),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )""")

    # Interviews
    c.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        scheduled_date TIMESTAMP,
        interview_type TEXT,
        meeting_link TEXT,
        status TEXT DEFAULT 'scheduled',
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id),
        FOREIGN KEY (employee_id) REFERENCES users(id),
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )""")

    # Messages (chat)
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        sender_type TEXT NOT NULL,
        receiver_id INTEGER NOT NULL,
        receiver_type TEXT NOT NULL,
        application_id INTEGER,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT 0,
        attachment_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    )""")

    # Notifications
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        related_id INTEGER,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES users(id)
    )""")

    # Saved jobs
    c.execute("""
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES users(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        UNIQUE(employee_id, job_id)
    )""")

    # Job requests (user-posted tasks)
    c.execute("""
    CREATE TABLE IF NOT EXISTS job_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        location TEXT,
        budget TEXT,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_to INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (assigned_to) REFERENCES users(id)
    )""")

    # Applications to job requests (optional bidding)
    c.execute("""
    CREATE TABLE IF NOT EXISTS request_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        applicant_id INTEGER NOT NULL,
        message TEXT,
        status TEXT DEFAULT 'pending',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES job_requests(id),
        FOREIGN KEY (applicant_id) REFERENCES users(id)
    )""")

    conn.commit()
    conn.close()

# ========== USERS ==========
def add_user(name, email, password, role):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
              (name, email, password, role))
    conn.commit()
    conn.close()

def get_user(email):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

# ========== PROFILES ==========
def get_or_create_profile(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM employee_profiles WHERE user_id=?", (user_id,))
    profile = c.fetchone()
    if not profile:
        c.execute("INSERT INTO employee_profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM employee_profiles WHERE user_id=?", (user_id,))
        profile = c.fetchone()
    conn.close()
    return profile

def update_user_name(user_id, name):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))
    conn.commit()
    conn.close()

def update_profile(user_id, **kwargs):
    """Update profile fields. kwargs: phone, location, skills, etc."""
    conn = connect()
    c = conn.cursor()
    fields = []
    values = []
    for key, val in kwargs.items():
        fields.append(f"{key}=?")
        values.append(val)
    values.append(user_id)
    sql = f"UPDATE employee_profiles SET {', '.join(fields)}, updated_at=CURRENT_TIMESTAMP WHERE user_id=?"
    c.execute(sql, values)
    conn.commit()
    conn.close()

# ========== COMPANIES ==========
def get_all_companies():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM companies ORDER BY name")
    companies = c.fetchall()
    conn.close()
    return companies

def get_company_jobs(company_id, employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT j.*,
               (SELECT COUNT(*) FROM applications WHERE job_id=j.id AND employee_id=?) as applied
        FROM jobs j
        WHERE j.company_id=? AND j.status='active'
        ORDER BY j.created_at DESC
    """, (employee_id, company_id))
    jobs = c.fetchall()
    conn.close()
    return jobs

# ========== JOBS ==========
def search_jobs(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT j.*, c.name as company_name, c.logo,
               (SELECT COUNT(*) FROM applications WHERE job_id=j.id AND employee_id=?) as applied,
               (SELECT COUNT(*) FROM saved_jobs WHERE job_id=j.id AND employee_id=?) as saved
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.status='active'
        ORDER BY j.created_at DESC
    """, (employee_id, employee_id))
    jobs = c.fetchall()
    conn.close()
    return jobs

def get_job_by_id(job_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT j.*, c.name as company_name, c.email as company_email FROM jobs j JOIN companies c ON j.company_id=c.id WHERE j.id=?", (job_id,))
    job = c.fetchone()
    conn.close()
    return job

# ========== APPLICATIONS ==========
def add_application(job_id, employee_id, company_id, match_score, cover_letter):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications (job_id, employee_id, company_id, match_score, cover_letter)
        VALUES (?, ?, ?, ?, ?)
    """, (job_id, employee_id, company_id, match_score, cover_letter))
    conn.commit()
    conn.close()

def get_user_applications(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT a.*, j.title as job_title, j.company_name, j.location, j.salary_range,
               i.scheduled_date, i.status as interview_status, i.meeting_link
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN interviews i ON a.id = i.application_id
        WHERE a.employee_id = ?
        ORDER BY a.applied_at DESC
    """, (employee_id,))
    apps = c.fetchall()
    conn.close()
    return apps

# ========== SAVED JOBS ==========
def save_job(employee_id, job_id):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO saved_jobs (employee_id, job_id) VALUES (?, ?)", (employee_id, job_id))
    conn.commit()
    conn.close()

def unsave_job(employee_id, job_id):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM saved_jobs WHERE employee_id=? AND job_id=?", (employee_id, job_id))
    conn.commit()
    conn.close()

def get_saved_jobs(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT j.*, c.name as company_name,
               (SELECT COUNT(*) FROM applications WHERE job_id=j.id AND employee_id=?) as applied
        FROM saved_jobs sj
        JOIN jobs j ON sj.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE sj.employee_id = ?
        ORDER BY sj.saved_at DESC
    """, (employee_id, employee_id))
    jobs = c.fetchall()
    conn.close()
    return jobs

# ========== NOTIFICATIONS ==========
def add_notification(employee_id, type_, title, message, related_id=None):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO notifications (employee_id, type, title, message, related_id)
        VALUES (?, ?, ?, ?, ?)
    """, (employee_id, type_, title, message, related_id))
    conn.commit()
    conn.close()

def get_user_notifications(employee_id, limit=10):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM notifications
        WHERE employee_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (employee_id, limit))
    notifs = c.fetchall()
    conn.close()
    return notifs

def mark_notifications_read(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE employee_id=?", (employee_id,))
    conn.commit()
    conn.close()

# ========== JOB REQUESTS ==========
def add_job_request(user_id, title, description, category, location, budget):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO job_requests (user_id, title, description, category, location, budget)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, description, category, location, budget))
    conn.commit()
    conn.close()

def get_open_requests():
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT jr.*, u.name as user_name
        FROM job_requests jr
        JOIN users u ON jr.user_id = u.id
        WHERE jr.status='open'
        ORDER BY jr.created_at DESC
    """)
    requests = c.fetchall()
    conn.close()
    return requests

def get_user_requests(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM job_requests WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    reqs = c.fetchall()
    conn.close()
    return reqs

def express_interest(request_id, applicant_id, message):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO request_applications (request_id, applicant_id, message)
        VALUES (?, ?, ?)
    """, (request_id, applicant_id, message))
    conn.commit()
    conn.close()

def get_request_by_id(request_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM job_requests WHERE id=?", (request_id,))
    req = c.fetchone()
    conn.close()
    return req

# ========== MESSAGES ==========
def get_conversations(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT
               m.sender_id, m.sender_type, m.receiver_id, m.receiver_type,
               c.id as company_id, c.name as company_name,
               j.title as job_title,
               (SELECT message FROM messages
                WHERE (sender_id=? AND receiver_id=c.id AND sender_type='employee' AND receiver_type='company')
                   OR (sender_id=c.id AND receiver_id=? AND sender_type='company' AND receiver_type='employee')
                ORDER BY created_at DESC LIMIT 1) as last_message,
               (SELECT created_at FROM messages
                WHERE (sender_id=? AND receiver_id=c.id AND sender_type='employee' AND receiver_type='company')
                   OR (sender_id=c.id AND receiver_id=? AND sender_type='company' AND receiver_type='employee')
                ORDER BY created_at DESC LIMIT 1) as last_message_time,
               (SELECT COUNT(*) FROM messages
                WHERE receiver_id=? AND sender_id=c.id AND receiver_type='employee' AND is_read=0) as unread_count
        FROM messages m
        JOIN companies c ON (m.sender_id=c.id AND m.sender_type='company') OR (m.receiver_id=c.id AND m.receiver_type='company')
        JOIN jobs j ON m.application_id IS NOT NULL
        WHERE m.sender_id=? OR m.receiver_id=?
        ORDER BY last_message_time DESC
    """, (employee_id, employee_id, employee_id, employee_id, employee_id, employee_id, employee_id))
    convos = c.fetchall()
    conn.close()
    return convos

def get_messages(employee_id, company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM messages
        WHERE (sender_id=? AND receiver_id=? AND sender_type='employee' AND receiver_type='company')
           OR (sender_id=? AND receiver_id=? AND sender_type='company' AND receiver_type='employee')
        ORDER BY created_at ASC
    """, (employee_id, company_id, company_id, employee_id))
    msgs = c.fetchall()
    conn.close()
    return msgs

def send_message(sender_id, sender_type, receiver_id, receiver_type, message, application_id=None):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (sender_id, sender_type, receiver_id, receiver_type, application_id, message)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender_id, sender_type, receiver_id, receiver_type, application_id, message))
    conn.commit()
    conn.close()

def mark_messages_read(employee_id, company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE messages SET is_read=1
        WHERE receiver_id=? AND sender_id=? AND receiver_type='employee'
    """, (employee_id, company_id))
    conn.commit()
    conn.close()

# ========== ANALYTICS ==========
def get_application_stats(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) as count FROM applications WHERE employee_id=? GROUP BY status", (employee_id,))
    stats = c.fetchall()
    conn.close()
    return stats

def get_applications_over_time(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT DATE(applied_at) as date, COUNT(*) as count FROM applications WHERE employee_id=? GROUP BY DATE(applied_at) ORDER BY date", (employee_id,))
    data = c.fetchall()
    conn.close()
    return data

def get_interview_count(employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM interviews WHERE employee_id=?", (employee_id,))
    return c.fetchone()[0]

def update_job_request(request_id, title, description, category, location, budget, status):
    """Update an existing job request."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE job_requests
        SET title=?, description=?, category=?, location=?, budget=?, status=?
        WHERE id=?
    """, (title, description, category, location, budget, status, request_id))
    conn.commit()
    conn.close()

def delete_job_request(request_id):
    """Delete a job request."""
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM job_requests WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

def get_user_requests(user_id):
    """Get all requests posted by a specific user."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM job_requests
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (user_id,))
    requests = c.fetchall()
    conn.close()
    return requests

# --- Company Profile updates (companies table already exists, but ensure it has all fields) ---
def update_company_profile(company_id, **kwargs):
    """Update company details. kwargs: name, description, industry, location, website, logo."""
    conn = connect()
    c = conn.cursor()
    fields = []
    values = []
    for key, val in kwargs.items():
        fields.append(f"{key}=?")
        values.append(val)
    values.append(company_id)
    sql = f"UPDATE companies SET {', '.join(fields)} WHERE id=?"
    c.execute(sql, values)
    conn.commit()
    conn.close()

def get_company_by_id(company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM companies WHERE id=?", (company_id,))
    company = c.fetchone()
    conn.close()
    return company

# --- Applications with details ---
def get_applications_for_company(company_id):
    """Get all applications for jobs posted by this company, with applicant details."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT a.*, j.title as job_title, u.name as applicant_name, u.email as applicant_email,
               ep.skills, ep.resume_path, ep.location, ep.phone,
               (SELECT COUNT(*) FROM interviews WHERE application_id = a.id) as has_interview
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.employee_id = u.id
        LEFT JOIN employee_profiles ep ON u.id = ep.user_id
        WHERE j.company_id = ?
        ORDER BY a.applied_at DESC
    """, (company_id,))
    apps = c.fetchall()
    conn.close()
    return apps

def update_application_status(application_id, status):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE applications SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, application_id))
    conn.commit()
    conn.close()

def create_interview(application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO interviews (application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link))
    conn.commit()
    conn.close()

# --- Job Requests (employees looking for work) ---
def get_all_open_job_requests():
    """Get all open job requests from employees."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT jr.*, u.name as employee_name, u.email as employee_email,
               ep.skills, ep.resume_path, ep.location, ep.phone, ep.bio
        FROM job_requests jr
        JOIN users u ON jr.user_id = u.id
        LEFT JOIN employee_profiles ep ON u.id = ep.user_id
        WHERE jr.status = 'open'
        ORDER BY jr.created_at DESC
    """)
    requests = c.fetchall()
    conn.close()
    return requests

def express_interest_in_request(request_id, company_id, message):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT user_id FROM job_requests WHERE id=?", (request_id,))
    result = c.fetchone()
    if result:
        employee_id = result[0]
        # Create notification
        c.execute("""
            INSERT INTO notifications (employee_id, type, title, message)
            VALUES (?, 'employer_interest', 'An employer is interested in your request', ?)
        """, (employee_id, f"Company ID {company_id} says: {message}"))
        # Also create a chat message (optional)
        c.execute("""
            INSERT INTO messages (sender_id, sender_type, receiver_id, receiver_type, message)
            VALUES (?, 'company', ?, 'employee', ?)
        """, (company_id, employee_id, message))
        conn.commit()
    conn.close()

# --- Messaging (already have messages table) ---
def get_messages_between_company_and_employee(company_id, employee_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM messages
        WHERE (sender_id=? AND receiver_id=? AND sender_type='company' AND receiver_type='employee')
           OR (sender_id=? AND receiver_id=? AND sender_type='employee' AND receiver_type='company')
        ORDER BY created_at ASC
    """, (company_id, employee_id, employee_id, company_id))
    msgs = c.fetchall()
    conn.close()
    return msgs

def send_message_from_company(sender_company_id, receiver_employee_id, message, application_id=None):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (sender_id, sender_type, receiver_id, receiver_type, application_id, message)
        VALUES (?, 'company', ?, 'employee', ?, ?)
    """, (sender_company_id, receiver_employee_id, application_id, message))
    conn.commit()
    conn.close()

def get_job_count_for_company(company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs WHERE company_id=? AND status='active'", (company_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_application_count_for_company(company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.company_id=?
    """, (company_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_interview_count_for_company(company_id):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM interviews i
        JOIN jobs j ON i.job_id = j.id
        WHERE j.company_id=?
    """, (company_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_open_request_count():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM job_requests WHERE status='open'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_company_by_email(email):
    """Get a company by its email address."""
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM companies WHERE email=?", (email,))
    company = c.fetchone()
    conn.close()
    return company

def create_company_for_employer(user_id, company_name, email):
    """Create a company record for an employer and link it to the user."""
    conn = connect()
    c = conn.cursor()
    
    # Ensure users table has company_id column
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'company_id' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN company_id INTEGER")
    
    # Insert the company
    c.execute("INSERT INTO companies (name, email) VALUES (?, ?)", (company_name, email))
    company_id = c.lastrowid
    
    # Link the company to the user
    c.execute("UPDATE users SET company_id=? WHERE id=?", (company_id, user_id))
    
    conn.commit()
    conn.close()
    return company_id

def add_job(company_id, company_name, title, category, description, requirements,
            location, job_type, salary_range, experience_level, skills_required, deadline):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO jobs (company_id, company_name, title, category, description, requirements,
                          location, job_type, salary_range, experience_level, skills_required, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, company_name, title, category, description, requirements,
          location, job_type, salary_range, experience_level, skills_required, deadline))
    conn.commit()
    conn.close()

def upsert_interview(application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link):
    """Insert or update an interview for the given application."""
    conn = connect()
    c = conn.cursor()
    # Check if interview exists
    c.execute("SELECT id FROM interviews WHERE application_id=?", (application_id,))
    existing = c.fetchone()
    if existing:
        # Update
        c.execute("""
            UPDATE interviews SET scheduled_date=?, interview_type=?, meeting_link=?, status='scheduled'
            WHERE application_id=?
        """, (scheduled_date, interview_type, meeting_link, application_id))
    else:
        # Insert
        c.execute("""
            INSERT INTO interviews (application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link))
    conn.commit()
    conn.close()

def mark_company_messages_read(company_id, employee_id):
    """Mark all messages from an employee to the company as read."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE messages SET is_read=1
        WHERE sender_id=? AND receiver_id=? AND sender_type='employee' AND receiver_type='company'
    """, (employee_id, company_id))
    conn.commit()
    conn.close()

def get_company_conversations(company_id):
    """Get all distinct employees the company has chatted with, with last message and unread count."""
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT
               u.id as employee_id,
               u.name as employee_name,
               (SELECT message FROM messages
                WHERE (sender_id=? AND receiver_id=u.id AND sender_type='company' AND receiver_type='employee')
                   OR (sender_id=u.id AND receiver_id=? AND sender_type='employee' AND receiver_type='company')
                ORDER BY created_at DESC LIMIT 1) as last_message,
               (SELECT created_at FROM messages
                WHERE (sender_id=? AND receiver_id=u.id AND sender_type='company' AND receiver_type='employee')
                   OR (sender_id=u.id AND receiver_id=? AND sender_type='employee' AND receiver_type='company')
                ORDER BY created_at DESC LIMIT 1) as last_message_time,
               (SELECT COUNT(*) FROM messages
                WHERE sender_id=u.id AND receiver_id=? AND sender_type='employee' AND receiver_type='company' AND is_read=0) as unread_count
        FROM messages m
        JOIN users u ON (m.sender_id = u.id AND m.sender_type='employee') OR (m.receiver_id = u.id AND m.receiver_type='employee')
        WHERE m.sender_id=? OR m.receiver_id=?
        ORDER BY last_message_time DESC
    """, (company_id, company_id, company_id, company_id, company_id, company_id, company_id))
    convos = c.fetchall()
    conn.close()
    return convos
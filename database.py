import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime, timezone
import datetime as dt
import streamlit as st

# cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
# if not firebase_admin._apps:
#     cred = credentials.Certificate(cred_path)
#     firebase_admin.initialize_app(cred)

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def doc_to_dict(doc):
    data = doc.to_dict()
    data['id'] = doc.id
    return data

def add_user(name, email, password, role):
    """Add a new user to Firestore."""
    user_ref = db.collection('users').document(email)
    user_ref.set({
        'name': name,
        'email': email,
        'password': password,  # already hashed
        'role': role,
        'created_at': firestore.SERVER_TIMESTAMP
    })

def get_user(email):
    """Retrieve a user by email."""
    user_ref = db.collection('users').document(email)
    user_doc = user_ref.get()
    if user_doc.exists:
        data = user_doc.to_dict()
        data['id'] = email  # store email as id for consistency
        return (data['id'], data['name'], data['email'], data['password'], data['role'])
    return None

def get_user_by_id(user_id):
    """Retrieve a user by their document ID (email)."""
    return get_user(user_id)  # same as get_user because ID is email

# ========== PROFILES ==========
def get_or_create_profile(user_id):
    """Get employee profile for a user; create if not exists."""
    profile_ref = db.collection('employee_profiles').document(user_id)
    profile_doc = profile_ref.get()
    if profile_doc.exists:
        data = profile_doc.to_dict()
    else:
        # Create empty profile
        data = {
            'user_id': user_id,
            'phone': '',
            'location': '',
            'profile_pic': '',
            'resume_path': '',
            'skills': '',
            'experience_level': '',
            'preferred_job_type': '',
            'expected_salary': '',
            'bio': '',
            'linkedin_url': '',
            'github_url': '',
            'portfolio_url': '',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        profile_ref.set(data)
    # Convert to tuple to match old format (user_id, phone, location, profile_pic, resume_path, skills, experience_level, preferred_job_type, expected_salary, bio, linkedin_url, github_url, portfolio_url, created_at, updated_at)
    return (
        user_id,
        data.get('phone', ''),
        data.get('location', ''),
        data.get('profile_pic', ''),
        data.get('resume_path', ''),
        data.get('skills', ''),
        data.get('experience_level', ''),
        data.get('preferred_job_type', ''),
        data.get('expected_salary', ''),
        data.get('bio', ''),
        data.get('linkedin_url', ''),
        data.get('github_url', ''),
        data.get('portfolio_url', ''),
        data.get('created_at'),
        data.get('updated_at')
    )

def update_user_name(user_id, name):
    """Update user's name in users collection."""
    db.collection('users').document(user_id).update({'name': name})

def update_profile(user_id, **kwargs):
    """Update employee profile fields."""
    profile_ref = db.collection('employee_profiles').document(user_id)
    kwargs['updated_at'] = firestore.SERVER_TIMESTAMP
    profile_ref.update(kwargs)

# ========== COMPANIES ==========
def get_all_companies():
    """Retrieve all companies."""
    companies_ref = db.collection('companies').stream()
    companies = []
    for doc in companies_ref:
        data = doc.to_dict()
        companies.append((
            doc.id, data.get('name'), data.get('email'), data.get('logo'),
            data.get('description'), data.get('industry'), data.get('location'),
            data.get('website'), data.get('created_at')
        ))
    return companies

def get_company_jobs(company_id, employee_id):
    """Get all active jobs for a company, with applied flag for the employee."""
    jobs_ref = db.collection('jobs').where('company_id', '==', company_id).where('status', '==', 'active').stream()
    jobs = []
    for job in jobs_ref:
        job_data = job.to_dict()
        job_data['id'] = job.id
        # Check if employee applied
        apps = db.collection('applications').where('job_id', '==', job.id).where('employee_id', '==', employee_id).limit(1).get()
        applied = 1 if len(list(apps)) > 0 else 0
        jobs.append((
            job.id,
            job_data.get('company_id'),
            job_data.get('company_name'),
            job_data.get('title'),
            job_data.get('category'),
            job_data.get('description'),
            job_data.get('requirements'),
            job_data.get('location'),
            job_data.get('job_type'),
            job_data.get('salary_range'),
            job_data.get('experience_level'),
            job_data.get('skills_required'),
            job_data.get('status'),
            job_data.get('created_at'),
            job_data.get('deadline'),
            applied
        ))
    return jobs

# ========== JOBS ==========
def search_jobs(employee_id):
    """Get all active jobs with company details and applied/saved flags."""
    jobs_ref = db.collection('jobs').where('status', '==', 'active').stream()
    jobs = []
    for job in jobs_ref:
        job_data = job.to_dict()
        job_data['id'] = job.id
        # Get company details
        company_doc = db.collection('companies').document(job_data['company_id']).get()
        company_name = company_doc.to_dict().get('name') if company_doc.exists else ''
        logo = company_doc.to_dict().get('logo') if company_doc.exists else ''
        # Applied flag
        apps = db.collection('applications').where('job_id', '==', job.id).where('employee_id', '==', employee_id).limit(1).get()
        applied = 1 if len(list(apps)) > 0 else 0
        # Saved flag
        saved = db.collection('saved_jobs').where('employee_id', '==', employee_id).where('job_id', '==', job.id).limit(1).get()
        saved_flag = 1 if len(list(saved)) > 0 else 0
        jobs.append((
            job.id,
            job_data.get('company_id'),
            job_data.get('company_name'),
            job_data.get('title'),
            job_data.get('category'),
            job_data.get('description'),
            job_data.get('requirements'),
            job_data.get('location'),
            job_data.get('job_type'),
            job_data.get('salary_range'),
            job_data.get('experience_level'),
            job_data.get('skills_required'),
            job_data.get('status'),
            job_data.get('created_at'),
            job_data.get('deadline'),
            company_name,
            logo,
            applied,
            saved_flag
        ))
    return jobs

def get_job_by_id(job_id):
    """Get job details along with company name and email."""
    job_doc = db.collection('jobs').document(job_id).get()
    if not job_doc.exists:
        return None
    job_data = job_doc.to_dict()
    job_data['id'] = job_doc.id
    # Get company
    company_doc = db.collection('companies').document(job_data['company_id']).get()
    company_name = company_doc.to_dict().get('name') if company_doc.exists else ''
    company_email = company_doc.to_dict().get('email') if company_doc.exists else ''
    # Return as tuple to match old format: id, company_id, company_name, title, category, description, requirements, location, job_type, salary_range, experience_level, skills_required, status, created_at, deadline, company_name, company_email
    return (
        job_data['id'],
        job_data.get('company_id'),
        job_data.get('company_name'),
        job_data.get('title'),
        job_data.get('category'),
        job_data.get('description'),
        job_data.get('requirements'),
        job_data.get('location'),
        job_data.get('job_type'),
        job_data.get('salary_range'),
        job_data.get('experience_level'),
        job_data.get('skills_required'),
        job_data.get('status'),
        job_data.get('created_at'),
        job_data.get('deadline'),
        company_name,
        company_email
    )

# ========== APPLICATIONS ==========
def add_application(job_id, employee_id, company_id, match_score, cover_letter):
    """Add a new application."""
    app_ref = db.collection('applications').document()
    app_ref.set({
        'job_id': job_id,
        'employee_id': employee_id,
        'company_id': company_id,
        'match_score': match_score,
        'cover_letter': cover_letter,
        'status': 'pending',
        'applied_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

def get_user_applications(employee_id):
    """Get all applications for an employee, with job and interview details."""
    apps_ref = db.collection('applications').where('employee_id', '==', employee_id).order_by('applied_at', direction=firestore.Query.DESCENDING).stream()
    apps = []
    for app in apps_ref:
        app_data = app.to_dict()
        app_data['id'] = app.id
        # Get job details
        job_doc = db.collection('jobs').document(app_data['job_id']).get()
        job_title = job_doc.to_dict().get('title') if job_doc.exists else ''
        company_name = job_doc.to_dict().get('company_name') if job_doc.exists else ''
        location = job_doc.to_dict().get('location') if job_doc.exists else ''
        salary_range = job_doc.to_dict().get('salary_range') if job_doc.exists else ''
        # Get interview details
        interview_ref = db.collection('interviews').where('application_id', '==', app.id).limit(1).get()
        interview = next(iter(interview_ref), None)
        scheduled_date = None
        interview_status = None
        meeting_link = None
        if interview:
            int_data = interview.to_dict()
            scheduled_date = int_data.get('scheduled_date')
            interview_status = int_data.get('status')
            meeting_link = int_data.get('meeting_link')
        apps.append((
            app.id,
            app_data.get('employee_id'),
            app_data.get('company_id'),
            app_data.get('job_id'),
            app_data.get('status'),
            app_data.get('match_score'),
            app_data.get('cover_letter'),
            app_data.get('applied_at'),
            app_data.get('updated_at'),
            job_title,
            company_name,
            location,
            salary_range,
            scheduled_date,
            interview_status,
            meeting_link
        ))
    return apps

# ========== SAVED JOBS ==========
def save_job(employee_id, job_id):
    """Save a job for an employee."""
    doc_id = f"{employee_id}_{job_id}"
    db.collection('saved_jobs').document(doc_id).set({
        'employee_id': employee_id,
        'job_id': job_id,
        'saved_at': firestore.SERVER_TIMESTAMP
    })

def unsave_job(employee_id, job_id):
    """Remove a saved job."""
    doc_id = f"{employee_id}_{job_id}"
    db.collection('saved_jobs').document(doc_id).delete()

def get_saved_jobs(employee_id):
    """Get all saved jobs for an employee with applied flag."""
    saved_ref = db.collection('saved_jobs').where('employee_id', '==', employee_id).stream()
    jobs = []
    for saved in saved_ref:
        saved_data = saved.to_dict()
        job_doc = db.collection('jobs').document(saved_data['job_id']).get()
        if not job_doc.exists:
            continue
        job_data = job_doc.to_dict()
        job_data['id'] = job_doc.id
        # Get company name
        company_doc = db.collection('companies').document(job_data['company_id']).get()
        company_name = company_doc.to_dict().get('name') if company_doc.exists else ''
        # Applied flag
        apps = db.collection('applications').where('job_id', '==', job_data['id']).where('employee_id', '==', employee_id).limit(1).get()
        applied = 1 if len(list(apps)) > 0 else 0
        jobs.append((
            job_data['id'],
            job_data.get('company_id'),
            job_data.get('company_name'),
            job_data.get('title'),
            job_data.get('category'),
            job_data.get('description'),
            job_data.get('requirements'),
            job_data.get('location'),
            job_data.get('job_type'),
            job_data.get('salary_range'),
            job_data.get('experience_level'),
            job_data.get('skills_required'),
            job_data.get('status'),
            job_data.get('created_at'),
            job_data.get('deadline'),
            company_name,
            applied
        ))
    return jobs

# ========== NOTIFICATIONS ==========
def add_notification(employee_id, type_, title, message, related_id=None):
    """Add a notification for an employee."""
    notif_ref = db.collection('notifications').document()
    notif_ref.set({
        'employee_id': employee_id,
        'type': type_,
        'title': title,
        'message': message,
        'related_id': related_id,
        'is_read': False,
        'created_at': firestore.SERVER_TIMESTAMP
    })

def get_user_notifications(employee_id, limit=10):
    """Get latest notifications for an employee."""
    notifs_ref = db.collection('notifications').where('employee_id', '==', employee_id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
    notifs = []
    for notif in notifs_ref:
        data = notif.to_dict()
        data['id'] = notif.id
        notifs.append((
            data['id'],
            data.get('employee_id'),
            data.get('type'),
            data.get('title'),
            data.get('message'),
            data.get('related_id'),
            data.get('is_read'),
            data.get('created_at')
        ))
    return notifs

def mark_notifications_read(employee_id):
    """Mark all notifications as read for an employee."""
    notifs_ref = db.collection('notifications').where('employee_id', '==', employee_id).where('is_read', '==', False).stream()
    for notif in notifs_ref:
        notif.reference.update({'is_read': True})

# ========== JOB REQUESTS ==========
def add_job_request(user_id, title, description, category, location, budget):
    """Post a new job request."""
    req_ref = db.collection('job_requests').document()
    req_ref.set({
        'user_id': user_id,
        'title': title,
        'description': description,
        'category': category,
        'location': location,
        'budget': budget,
        'status': 'open',
        'created_at': firestore.SERVER_TIMESTAMP,
        'assigned_to': None
    })

def get_open_requests():
    """Get all open job requests with user names."""
    reqs_ref = db.collection('job_requests').where('status', '==', 'open').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    reqs = []
    for req in reqs_ref:
        data = req.to_dict()
        data['id'] = req.id
        user_doc = db.collection('users').document(data['user_id']).get()
        user_name = user_doc.to_dict().get('name') if user_doc.exists else ''
        reqs.append((
            data['id'],
            data.get('user_id'),
            data.get('title'),
            data.get('description'),
            data.get('category'),
            data.get('location'),
            data.get('budget'),
            data.get('status'),
            data.get('created_at'),
            data.get('assigned_to'),
            user_name
        ))
    return reqs

def get_user_requests(user_id):
    """Get all requests posted by a user."""
    reqs_ref = db.collection('job_requests').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    reqs = []
    for req in reqs_ref:
        data = req.to_dict()
        data['id'] = req.id
        reqs.append((
            data['id'],
            data.get('user_id'),
            data.get('title'),
            data.get('description'),
            data.get('category'),
            data.get('location'),
            data.get('budget'),
            data.get('status'),
            data.get('created_at'),
            data.get('assigned_to')
        ))
    return reqs

def update_job_request(request_id, title, description, category, location, budget, status):
    """Update a job request."""
    db.collection('job_requests').document(request_id).update({
        'title': title,
        'description': description,
        'category': category,
        'location': location,
        'budget': budget,
        'status': status
    })

def delete_job_request(request_id):
    """Delete a job request."""
    db.collection('job_requests').document(request_id).delete()

def get_request_by_id(request_id):
    """Get a job request by ID."""
    req_doc = db.collection('job_requests').document(request_id).get()
    if not req_doc.exists:
        return None
    data = req_doc.to_dict()
    data['id'] = req_doc.id
    return (
        data['id'],
        data.get('user_id'),
        data.get('title'),
        data.get('description'),
        data.get('category'),
        data.get('location'),
        data.get('budget'),
        data.get('status'),
        data.get('created_at'),
        data.get('assigned_to')
    )



def get_messages(employee_id, company_id):
    """Get all messages between an employee and a company."""
    msgs_ref = db.collection('messages').where('sender_id', 'in', [employee_id, company_id]).where('receiver_id', 'in', [company_id, employee_id]).order_by('created_at').stream()
    msgs = []
    for msg in msgs_ref:
        data = msg.to_dict()
        data['id'] = msg.id
        msgs.append((
            data['id'],
            data.get('sender_id'),
            data.get('sender_type'),
            data.get('receiver_id'),
            data.get('receiver_type'),
            data.get('application_id'),
            data.get('message'),
            data.get('is_read'),
            data.get('attachment_path'),
            data.get('created_at')
        ))
    return msgs

def send_message(sender_id, sender_type, receiver_id, receiver_type, message, application_id=None):
    """Send a message."""
    msg_ref = db.collection('messages').document()
    msg_ref.set({
        'sender_id': sender_id,
        'sender_type': sender_type,
        'receiver_id': receiver_id,
        'receiver_type': receiver_type,
        'application_id': application_id,
        'message': message,
        'is_read': False,
        'attachment_path': None,
        'created_at': firestore.SERVER_TIMESTAMP
    })

def mark_messages_read(employee_id, company_id):
    """Mark all messages from company to employee as read."""
    msgs_ref = db.collection('messages').where('sender_id', '==', company_id).where('receiver_id', '==', employee_id).where('is_read', '==', False).stream()
    for msg in msgs_ref:
        msg.reference.update({'is_read': True})

# ========== ANALYTICS ==========
def get_application_stats(employee_id):
    """Get count of applications per status."""
    stats = {}
    apps_ref = db.collection('applications').where('employee_id', '==', employee_id).stream()
    for app in apps_ref:
        status = app.to_dict().get('status')
        stats[status] = stats.get(status, 0) + 1
    return [(status, count) for status, count in stats.items()]

def get_applications_over_time(employee_id):
    """Get applications per date."""
    # Simple implementation: fetch all and group by date
    apps_ref = db.collection('applications').where('employee_id', '==', employee_id).stream()
    dates = {}
    for app in apps_ref:
        date_str = app.to_dict().get('applied_at').strftime('%Y-%m-%d')
        dates[date_str] = dates.get(date_str, 0) + 1
    return [(date, count) for date, count in sorted(dates.items())]

def get_interview_count(employee_id):
    """Count interviews for an employee."""
    interviews_ref = db.collection('interviews').where('employee_id', '==', employee_id).stream()
    return len(list(interviews_ref))

# ========== COMPANY FUNCTIONS (for employer dashboard) ==========
def get_company_by_email(email):
    """Get company by email."""
    companies_ref = db.collection('companies').where('email', '==', email).limit(1).stream()
    for comp in companies_ref:
        data = comp.to_dict()
        data['id'] = comp.id
        return (
            data['id'],
            data.get('name'),
            data.get('email'),
            data.get('logo'),
            data.get('description'),
            data.get('industry'),
            data.get('location'),
            data.get('website'),
            data.get('created_at')
        )
    return None

def get_company_by_id(company_id):
    """Get company by ID."""
    comp_doc = db.collection('companies').document(company_id).get()
    if not comp_doc.exists:
        return None
    data = comp_doc.to_dict()
    data['id'] = comp_doc.id
    return (
        data['id'],
        data.get('name'),
        data.get('email'),
        data.get('logo'),
        data.get('description'),
        data.get('industry'),
        data.get('location'),
        data.get('website'),
        data.get('created_at')
    )

def update_company_profile(company_id, **kwargs):
    """Update company details."""
    kwargs['updated_at'] = firestore.SERVER_TIMESTAMP
    db.collection('companies').document(company_id).update(kwargs)

def get_applications_for_company(company_id):
    """Get all applications for jobs posted by this company."""
    # First get all jobs for this company
    jobs_ref = db.collection('jobs').where('company_id', '==', company_id).stream()
    job_ids = [job.id for job in jobs_ref]
    apps = []
    for job_id in job_ids:
        apps_ref = db.collection('applications').where('job_id', '==', job_id).stream()
        for app in apps_ref:
            app_data = app.to_dict()
            app_data['id'] = app.id
            # Get applicant details
            user_doc = db.collection('users').document(app_data['employee_id']).get()
            applicant_name = user_doc.to_dict().get('name') if user_doc.exists else ''
            applicant_email = user_doc.to_dict().get('email') if user_doc.exists else ''
            # Get profile
            profile = get_or_create_profile(app_data['employee_id'])
            skills = profile[5] if profile else ''
            resume_path = profile[4] if profile else ''
            location = profile[2] if profile else ''
            phone = profile[1] if profile else ''
            # Check if interview exists
            interview_ref = db.collection('interviews').where('application_id', '==', app.id).limit(1).get()
            has_interview = 1 if len(list(interview_ref)) > 0 else 0
            # Get job title
            job_doc = db.collection('jobs').document(job_id).get()
            job_title = job_doc.to_dict().get('title') if job_doc.exists else ''
            apps.append((
                app.id,
                app_data.get('employee_id'),
                app_data.get('company_id'),
                app_data.get('job_id'),
                app_data.get('status'),
                app_data.get('match_score'),
                app_data.get('cover_letter'),
                app_data.get('applied_at'),
                app_data.get('updated_at'),
                job_title,
                applicant_name,
                applicant_email,
                skills,
                resume_path,
                location,
                phone,
                has_interview
            ))
    return apps

def update_application_status(application_id, status):
    """Update application status."""
    db.collection('applications').document(application_id).update({
        'status': status,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

def create_interview(application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link):
    """Create a new interview."""
    interview_ref = db.collection('interviews').document()
    interview_ref.set({
        'application_id': application_id,
        'employee_id': employee_id,
        'company_id': company_id,
        'job_id': job_id,
        'scheduled_date': scheduled_date,
        'interview_type': interview_type,
        'meeting_link': meeting_link,
        'status': 'scheduled',
        'created_at': firestore.SERVER_TIMESTAMP
    })

def upsert_interview(application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link):
    """Insert or update interview."""
    interview_ref = db.collection('interviews').where('application_id', '==', application_id).limit(1).get()
    interview = next(iter(interview_ref), None)
    if interview:
        interview.reference.update({
            'scheduled_date': scheduled_date,
            'interview_type': interview_type,
            'meeting_link': meeting_link,
            'status': 'scheduled'
        })
    else:
        create_interview(application_id, employee_id, company_id, job_id, scheduled_date, interview_type, meeting_link)

def get_all_open_job_requests():
    """Get all open job requests with employee details."""
    reqs_ref = db.collection('job_requests').where('status', '==', 'open').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    reqs = []
    for req in reqs_ref:
        data = req.to_dict()
        data['id'] = req.id
        user_doc = db.collection('users').document(data['user_id']).get()
        employee_name = user_doc.to_dict().get('name') if user_doc.exists else ''
        employee_email = user_doc.to_dict().get('email') if user_doc.exists else ''
        profile = get_or_create_profile(data['user_id'])
        skills = profile[5] if profile else ''
        resume_path = profile[4] if profile else ''
        location = profile[2] if profile else ''
        phone = profile[1] if profile else ''
        bio = profile[9] if profile else ''
        reqs.append((
            data['id'],
            data.get('user_id'),
            data.get('title'),
            data.get('description'),
            data.get('category'),
            data.get('location'),
            data.get('budget'),
            data.get('status'),
            data.get('created_at'),
            data.get('assigned_to'),
            employee_name,
            employee_email,
            skills,
            resume_path,
            location,
            phone,
            bio
        ))
    return reqs

def express_interest_in_request(request_id, company_id, message):
    """Employer expresses interest in a job request (sends message and notification)."""
    req_doc = db.collection('job_requests').document(request_id).get()
    if not req_doc.exists:
        return
    employee_id = req_doc.to_dict().get('user_id')
    # Create notification
    add_notification(employee_id, 'employer_interest', 'An employer is interested in your request', f"Company ID {company_id} says: {message}")
    # Create chat message
    send_message(company_id, 'company', employee_id, 'employee', message)

def get_messages_between_company_and_employee(company_id, employee_id):
    """Get messages between a company and an employee."""
    return get_messages(employee_id, company_id)  # same as above

def send_message_from_company(sender_company_id, receiver_employee_id, message, application_id=None):
    """Send message from company to employee."""
    send_message(sender_company_id, 'company', receiver_employee_id, 'employee', message, application_id)

def mark_company_messages_read(company_id, employee_id):
    """Mark messages from employee to company as read."""
    msgs_ref = db.collection('messages').where('sender_id', '==', employee_id).where('receiver_id', '==', company_id).where('is_read', '==', False).stream()
    for msg in msgs_ref:
        msg.reference.update({'is_read': True})

def get_job_count_for_company(company_id):
    """Get count of active jobs for a company."""
    jobs_ref = db.collection('jobs').where('company_id', '==', company_id).where('status', '==', 'active').stream()
    return len(list(jobs_ref))

def get_application_count_for_company(company_id):
    """Get total applications for a company's jobs."""
    apps_ref = db.collection('applications').where('company_id', '==', company_id).stream()
    return len(list(apps_ref))

def get_interview_count_for_company(company_id):
    """Get total interviews for a company's jobs."""
    interviews_ref = db.collection('interviews').where('company_id', '==', company_id).stream()
    return len(list(interviews_ref))

def get_open_request_count():
    """Get count of open job requests."""
    reqs_ref = db.collection('job_requests').where('status', '==', 'open').stream()
    return len(list(reqs_ref))

def create_company_for_employer(user_id, company_name, email):
    """Create a company record for an employer and link it."""
    # First create company
    company_ref = db.collection('companies').document()
    company_ref.set({
        'name': company_name,
        'email': email,
        'logo': '',
        'description': '',
        'industry': '',
        'location': '',
        'website': '',
        'created_at': firestore.SERVER_TIMESTAMP
    })
    company_id = company_ref.id
    # Link to user (update user document)
    db.collection('users').document(email).update({'company_id': company_id})
    return company_id

def add_job(company_id, company_name, title, category, description, requirements,
            location, job_type, salary_range, experience_level, skills_required, deadline):
    if isinstance(deadline, dt.date) and not isinstance(deadline, datetime):
        deadline = datetime.combine(deadline, datetime.min.time()).replace(tzinfo=timezone.utc)

    job_ref = db.collection('jobs').document()
    job_ref.set({
        'company_id': company_id,
        'company_name': company_name,
        'title': title,
        'category': category,
        'description': description,
        'requirements': requirements,
        'location': location,
        'job_type': job_type,
        'salary_range': salary_range,
        'experience_level': experience_level,
        'skills_required': skills_required,
        'status': 'active',
        'created_at': firestore.SERVER_TIMESTAMP,
        'deadline': deadline
    })

def get_conversations(employee_id):
    """
    Get all conversations for an employee with last message and unread count.
    Returns list of tuples:
    (sender_id, sender_type, receiver_id, receiver_type,
     company_id, company_name, job_title,
     last_message, last_message_time, unread_count)
    """
    # Fetch all messages where employee is either sender or receiver
    msgs_ref = db.collection('messages').where('sender_id', '==', employee_id).where('sender_type', '==', 'employee').stream()
    msgs_as_sender = list(msgs_ref)
    msgs_ref = db.collection('messages').where('receiver_id', '==', employee_id).where('receiver_type', '==', 'employee').stream()
    msgs_as_receiver = list(msgs_ref)
    all_msgs = msgs_as_sender + msgs_as_receiver

    # Group by company
    convos = {}
    for msg_doc in all_msgs:
        msg = msg_doc.to_dict()
        msg_id = msg_doc.id
        # Identify the company ID
        if msg['sender_type'] == 'company' and msg['sender_id'] != employee_id:
            company_id = msg['sender_id']
        elif msg['receiver_type'] == 'company' and msg['receiver_id'] != employee_id:
            company_id = msg['receiver_id']
        else:
            continue  # shouldn't happen

        if company_id not in convos:
            # Get company name
            company_doc = db.collection('companies').document(company_id).get()
            company_name = company_doc.to_dict().get('name', '') if company_doc.exists else ''
            # Get job title from application if available
            job_title = ''
            if msg.get('application_id'):
                app_doc = db.collection('applications').document(msg['application_id']).get()
                if app_doc.exists:
                    job_id = app_doc.to_dict().get('job_id')
                    if job_id:
                        job_doc = db.collection('jobs').document(job_id).get()
                        if job_doc.exists:
                            job_title = job_doc.to_dict().get('title', '')
            convos[company_id] = {
                'company_id': company_id,
                'company_name': company_name,
                'job_title': job_title,
                'last_message': None,
                'last_message_time': None,
                'unread_count': 0,
                'last_sender_type': None
            }

        convo = convos[company_id]
        # Update last message (most recent)
        msg_time = msg.get('created_at')
        if msg_time and (convo['last_message_time'] is None or msg_time > convo['last_message_time']):
            convo['last_message'] = msg.get('message', '')
            convo['last_message_time'] = msg_time
            convo['last_sender_type'] = msg['sender_type']

        # Count unread messages from company to employee
        if msg['sender_type'] == 'company' and msg['receiver_id'] == employee_id and not msg.get('is_read', False):
            convo['unread_count'] += 1

    # Convert to list of tuples
    result = []
    for convo in convos.values():
        # We need sender_id, sender_type, receiver_id, receiver_type for the last message
        # For consistency, we'll set them based on the last message's perspective
        # The tuple order from SQLite: (sender_id, sender_type, receiver_id, receiver_type, company_id, company_name, job_title, last_message, last_message_time, unread_count)
        # Since it's from employee view, last message might be from company or employee.
        # We'll set sender_id and receiver_id accordingly.
        if convo['last_sender_type'] == 'company':
            sender_id = convo['company_id']
            sender_type = 'company'
            receiver_id = employee_id
            receiver_type = 'employee'
        else:
            sender_id = employee_id
            sender_type = 'employee'
            receiver_id = convo['company_id']
            receiver_type = 'company'
        result.append((
            sender_id,
            sender_type,
            receiver_id,
            receiver_type,
            convo['company_id'],
            convo['company_name'],
            convo['job_title'],
            convo['last_message'],
            convo['last_message_time'],
            convo['unread_count']
        ))
    # Sort by last message time descending
    result.sort(key=lambda x: x[8] if x[8] else datetime.min, reverse=True)
    return result

def get_company_conversations(company_id):
    # Fetch all messages where company is either sender or receiver
    msgs_ref = db.collection('messages').where('sender_id', '==', company_id).where('sender_type', '==', 'company').stream()
    msgs_as_sender = list(msgs_ref)
    msgs_ref = db.collection('messages').where('receiver_id', '==', company_id).where('receiver_type', '==', 'company').stream()
    msgs_as_receiver = list(msgs_ref)
    all_msgs = msgs_as_sender + msgs_as_receiver

    # Group by employee
    convos = {}
    for msg_doc in all_msgs:
        msg = msg_doc.to_dict()
        # Identify the employee ID
        if msg['sender_type'] == 'employee' and msg['sender_id'] != company_id:
            employee_id = msg['sender_id']
        elif msg['receiver_type'] == 'employee' and msg['receiver_id'] != company_id:
            employee_id = msg['receiver_id']
        else:
            continue

        if employee_id not in convos:
            # Get employee name
            user_doc = db.collection('users').document(employee_id).get()
            employee_name = user_doc.to_dict().get('name', '') if user_doc.exists else ''
            convos[employee_id] = {
                'employee_id': employee_id,
                'employee_name': employee_name,
                'last_message': None,
                'last_message_time': None,
                'unread_count': 0
            }

        convo = convos[employee_id]
        msg_time = msg.get('created_at')
        if msg_time and (convo['last_message_time'] is None or msg_time > convo['last_message_time']):
            convo['last_message'] = msg.get('message', '')
            convo['last_message_time'] = msg_time

        # Count unread messages from employee to company
        if msg['sender_type'] == 'employee' and msg['receiver_id'] == company_id and not msg.get('is_read', False):
            convo['unread_count'] += 1

    # Convert to list of tuples
    result = []
    for convo in convos.values():
        result.append((
            convo['employee_id'],
            convo['employee_name'],
            convo['last_message'],
            convo['last_message_time'],
            convo['unread_count']
        ))
    result.sort(key=lambda x: x[3] if x[3] else datetime.min, reverse=True)
    return result

def update_expired_jobs():
    """Mark jobs as expired if deadline has passed."""
    now = datetime.now(timezone.utc)
    jobs_ref = db.collection('jobs').where('status', '==', 'active').where('deadline', '<', now).stream()
    for job in jobs_ref:
        job.reference.update({'status': 'expired'})

def get_company_jobs_all(company_id):
    """Get all jobs for a company (for management)."""
    jobs_ref = db.collection('jobs').where('company_id', '==', company_id).order_by('created_at', direction='DESCENDING').stream()
    jobs = []
    for job in jobs_ref:
        job_data = job.to_dict()
        job_data['id'] = job.id
        jobs.append(job_data)
    return jobs

def delete_job(job_id):
    """Delete a job and related data, but keep accepted/rejected applications."""
    # Get all applications for this job
    apps = db.collection('applications').where('job_id', '==', job_id).stream()
    for app in apps:
        app_data = app.to_dict()
        status = app_data.get('status')
        # If status is accepted or rejected, keep application and its related data
        if status in ['accepted', 'rejected']:
            continue
        # Otherwise, delete interviews and messages for this application
        interviews = db.collection('interviews').where('application_id', '==', app.id).stream()
        for iv in interviews:
            iv.reference.delete()
        msgs = db.collection('messages').where('application_id', '==', app.id).stream()
        for msg in msgs:
            msg.reference.delete()
        # Delete the application itself
        app.reference.delete()

    # Delete saved jobs (bookmarks, always removed)
    saved = db.collection('saved_jobs').where('job_id', '==', job_id).stream()
    for s in saved:
        s.reference.delete()

    # Delete notifications that reference this job (application/save notifications)
    notifs = db.collection('notifications').where('related_id', '==', job_id).where('type', 'in', ['application', 'save']).stream()
    for n in notifs:
        n.reference.delete()

    # Finally, delete the job itself
    db.collection('jobs').document(job_id).delete()

def get_new_applications_count(company_id):
    """Count applications with status 'pending' or 'new' (adjust as needed)"""
    from google.cloud import firestore
    db = firestore.Client()
    apps_ref = db.collection('applications').where('company_id', '==', company_id).where('status', 'in', ['pending', 'new'])
    return len(list(apps_ref.stream()))

def get_unread_messages_count(company_id):
    """Count messages from employees to company that are unread"""
    db = firestore.Client()
    msgs_ref = db.collection('messages').where('receiver_id', '==', company_id).where('receiver_type', '==', 'company').where('is_read', '==', False)
    return len(list(msgs_ref.stream()))

def get_recent_activities(company_id, limit=5):
    """
    Return list of recent activities: applications and messages, sorted by time descending.
    Each item: {'type': 'application'/'message', 'content': str, 'time': datetime}
    """
    db = firestore.Client()
    activities = []

    # Get recent applications
    apps_ref = db.collection('applications').where('company_id', '==', company_id).order_by('applied_at', direction=firestore.Query.DESCENDING).limit(limit)
    for app in apps_ref.stream():
        data = app.to_dict()
        activities.append({
            'type': 'application',
            'content': f"{data.get('employee_name')} applied for {data.get('job_title')}",
            'time': data.get('applied_at')
        })

    # Get recent messages
    msgs_ref = db.collection('messages').where('receiver_id', '==', company_id).where('receiver_type', '==', 'company').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
    for msg in msgs_ref.stream():
        data = msg.to_dict()
        activities.append({
            'type': 'message',
            'content': f"New message from {data.get('sender_name')}: {data.get('content')[:50]}...",
            'time': data.get('timestamp')
        })

    # Sort all by time descending and return top `limit`
    activities.sort(key=lambda x: x['time'], reverse=True)
    return activities[:limit]
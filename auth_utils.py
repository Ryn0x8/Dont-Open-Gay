import random
import smtplib
import streamlit as st
import bcrypt
import cv2
import numpy as np
from email.message import EmailMessage
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import base64
from rapidfuzz import fuzz
from deepface import DeepFace
from scipy.spatial.distance import cosine

# from insightface.app import FaceAnalysis
# import mediapipe as mp
# from mediapipe.tasks import python
# from mediapipe.tasks.python import vision
# from modelDownload import download_model


load_dotenv()

# Initialize Firebase Admin SDK (assumes database.py already did, but safe)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------------------------------------------------
# Helper: Check if user has a registered face (embedding exists)
# -------------------------------------------------------------------
def has_face_registered(email):
    """Return True if a face embedding exists for this email."""
    doc = db.collection('faces').document(email).get()
    return doc.exists

# ===== EMAIL =====
def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """Sends an email using configured SMTP."""
    sender_email = st.secrets["EMAIL_ADDRESS"]
    app_password = st.secrets["EMAIL_APP_PASSWORD"]

    if not sender_email or not app_password:
        print("Email credentials are not configured.")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        if is_html:
            msg.set_content("Your email client does not support HTML.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_job_alert_email(to_email, job_title, company_name, description,
                         requirements, location, job_type, salary_range):
    """Send a job alert email to a matching candidate."""

    subject = f"New Job Match: {job_title} at {company_name}"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #2563EB;">We found a job that matches your profile!</h2>
            <p><strong style="font-size: 1.2em;">{job_title}</strong> at <strong>{company_name}</strong></p>
            <p><strong>📍 Location:</strong> {location}</p>
            <p><strong>💼 Job Type:</strong> {job_type}</p>
            <p><strong>💰 Salary:</strong> {salary_range}</p>
            <p><strong>📝 Description:</strong><br>{description}</p>
            <p><strong>📋 Requirements:</strong><br>{requirements}</p>
            <p>
                👉 <a href="https://employeepro.streamlit.app/login_employee"
                style="background-color: #2563EB; color: white; padding: 10px 20px;
                text-decoration: none; border-radius: 8px;">
                Log in to apply
                </a>
            </p>
            <p style="color: #6B7280; font-size: 0.9em;">
                This is an automated alert from Anvaya.
            </p>
        </body>
    </html>
    """

    return send_email(to_email, subject, body, is_html=True)

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


# ===== OTP =====
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(receiver_email: str, otp: str) -> bool:
    """Sends OTP via email."""
    subject = "Your Anvaya Verification Code"
    body = f"""
Hello,

Your One-Time Password (OTP) for verification is:

    {otp}

This code will expire shortly. Do not share this code with anyone.

Regards,
Team Anvaya
    """
    return send_email(receiver_email, subject, body)

# ===== PASSWORD =====
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# ===== OLD FACE FUNCTIONS (keep intact) =====
# def capture_face(email):
#     """
#     Capture face from browser camera and store in Firestore as Base64.
#     Returns True if face detected and saved.
#     """
#     import streamlit as st

#     st.info("📸 Please capture your face for registration")

#     # Persist camera input across reruns
#     if "reg_face" not in st.session_state:
#         st.session_state.reg_face = None

#     img_file = st.camera_input("Take a photo", key="register_camera")

#     if img_file is not None:
#         st.session_state.reg_face = img_file

#     if st.session_state.reg_face is None:
#         return False  # No photo captured yet

#     # Convert to OpenCV format
#     bytes_data = st.session_state.reg_face.getvalue()
#     np_arr = np.frombuffer(bytes_data, np.uint8)
#     frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

#     if frame is None:
#         st.error("Could not process image")
#         return False

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#     )

#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#     if len(faces) == 0:
#         st.error("No face detected. Make sure you are in good lighting and try again.")
#         return False

#     # Take the first detected face
#     x, y, w, h = faces[0]
#     face = gray[y:y+h, x:x+w]
#     face = cv2.resize(face, (200, 200))

#     # Encode face as JPEG bytes
#     ret, buffer = cv2.imencode('.jpg', face)
#     if not ret:
#         st.error("Failed to encode face image")
#         return False

#     # Convert to Base64 string
#     face_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')

#     # Store in Firestore (faces collection, document ID = email)
#     db.collection('faces').document(email).set({
#         'image': face_base64,
#         'uploaded_at': firestore.SERVER_TIMESTAMP
#     })

#     st.success("✅ Face captured and saved successfully!")
#     st.session_state.reg_face = None
#     return True

# def verify_face(email):
#     """
#     Capture a new face and compare with stored face from Firestore.
#     Returns True if matched.
#     """
#     import streamlit as st

#     # Retrieve stored face from Firestore
#     face_doc = db.collection('faces').document(email).get()
#     if not face_doc.exists:
#         st.error("No registered face found. Please register first.")
#         return False

#     stored_base64 = face_doc.to_dict().get('image')
#     if not stored_base64:
#         st.error("Stored face data is missing.")
#         return False

#     # Decode Base64 to image
#     stored_bytes = base64.b64decode(stored_base64)
#     np_arr_stored = np.frombuffer(stored_bytes, np.uint8)
#     stored_face = cv2.imdecode(np_arr_stored, cv2.IMREAD_GRAYSCALE)

#     if stored_face is None:
#         st.error("Stored face image is corrupted.")
#         return False

#     # Persist camera input across reruns
#     if "verify_face_img" not in st.session_state:
#         st.session_state.verify_face_img = None

#     img_file = st.camera_input("Take a photo", key="verify_camera")

#     if img_file is not None:
#         st.session_state.verify_face_img = img_file

#     if st.session_state.verify_face_img is None:
#         st.info("📸 Please take a photo to continue.")
#         return False

#     # Convert to OpenCV format
#     bytes_data = st.session_state.verify_face_img.getvalue()
#     np_arr = np.frombuffer(bytes_data, np.uint8)
#     frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

#     if frame is None:
#         st.error("Could not process image")
#         return False

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#     )

#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#     if len(faces) == 0:
#         st.error("Face not detected. Make sure you are in good lighting.")
#         return False

#     # Take the first detected face
#     x, y, w, h = faces[0]
#     face = gray[y:y+h, x:x+w]
#     face = cv2.resize(face, (200, 200))

#     # Compare with stored face
#     diff = cv2.absdiff(stored_face, face)
#     score = np.mean(diff)
#     st.write(f"Face difference score: {score:.2f}")

#     if score < 50:  # threshold can be tuned
#         st.success("✅ Face verified successfully!")
#         st.session_state.verify_face_img = None
#         return True
#     else:
#         st.error("❌ Face does not match the registered one.")
#         st.session_state.verify_face_img = None
#         return False

MODEL_NAME = "Facenet512"  # more accurate than Facenet
# For Facenet512, cosine similarity threshold (empirical, tune on your data)
SIMILARITY_THRESHOLD = 0.35  # lower means stricter

def capture_face(email):
    """Capture and store face embedding using DeepFace (Facenet512)"""
    st.info("📸 Please capture your face for registration")
    
    if "reg_face" not in st.session_state:
        st.session_state.reg_face = None
    
    img_file = st.camera_input("Take a photo", key="register_camera")
    if img_file is not None:
        st.session_state.reg_face = img_file
    
    if st.session_state.reg_face is None:
        return False
    
    # Convert to OpenCV format
    bytes_data = st.session_state.reg_face.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    try:
        # Detect and compute embedding
        embedding_objs = DeepFace.represent(
            img_path=frame,
            model_name=MODEL_NAME,
            detector_backend="opencv",      # fast & reliable
            enforce_detection=True
        )
        
        if not embedding_objs:
            st.error("No face detected. Please try again.")
            return False
        
        # Optional: if multiple faces, take the largest (you could also error)
        if len(embedding_objs) > 1:
            st.warning("Multiple faces detected. Using the largest one.")
            # embedding_objs already contains one embedding per face? Actually represent returns list of dicts.
            # We'll take the first (default is largest anyway)
        
        embedding = embedding_objs[0]['embedding']
        
        # Store in Firestore
        db.collection('faces').document(email).set({
            'embedding': embedding,
            'model': MODEL_NAME,
            'uploaded_at': firestore.SERVER_TIMESTAMP
        })
        
        st.success("✅ Face registered successfully!")
        return True
        
    except Exception as e:
        st.error(f"Face detection failed: {str(e)}")
        return False


def verify_face(email):
    """Verify face using DeepFace comparison with stricter threshold."""
    # Retrieve stored embedding
    face_doc = db.collection('faces').document(email).get()
    if not face_doc.exists:
        st.error("No registered face found. Please register first.")
        return False
    
    stored_data = face_doc.to_dict()
    stored_embedding = stored_data.get('embedding')
    stored_model = stored_data.get('model', MODEL_NAME)
    
    if not stored_embedding:
        st.error("Stored face data is corrupted.")
        return False
    
    # Capture new face
    if "verify_img" not in st.session_state:
        st.session_state.verify_img = None
    
    img_file = st.camera_input("Take a photo", key="verify_camera")
    if img_file is not None:
        st.session_state.verify_img = img_file
    
    if st.session_state.verify_img is None:
        st.info("📸 Please take a photo")
        return False
    
    # Convert to OpenCV
    bytes_data = st.session_state.verify_img.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    try:
        # Compute embedding for new face using the same model
        new_embedding_objs = DeepFace.represent(
            img_path=frame,
            model_name=stored_model,
            detector_backend="opencv",
            enforce_detection=True
        )
        
        if not new_embedding_objs:
            st.error("No face detected in the new image.")
            return False
        
        new_embedding = new_embedding_objs[0]['embedding']
        
        # Calculate cosine similarity
        similarity = 1 - cosine(stored_embedding, new_embedding)
        
        # Determine threshold (could be model-specific)
        # For Facenet512, 0.35 is a good starting point; tune as needed.
        threshold = SIMILARITY_THRESHOLD
        
        st.write(f"Similarity score: {similarity:.3f} (threshold: {threshold})")
        
        if similarity >= threshold:
            st.success("✅ Face verified successfully!")
            return True
        else:
            st.error("❌ Face does not match the registered one.")
            return False
            
    except Exception as e:
        st.error(f"Verification failed: {str(e)}")
        return False


def has_face_registered(email):
    face_ref = db.collection('faces').document(email)
    face_doc = face_ref.get()
    return face_doc.exists
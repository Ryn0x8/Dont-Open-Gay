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

load_dotenv()

# Initialize Firebase Admin SDK (assumes database.py already did, but safe)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===== EMAIL =====
def send_email(to_email: str, subject: str, body: str) -> bool:
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
        msg.set_content(body)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

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

# ===== FACE =====
def capture_face(email):
    """
    Capture face from browser camera and store in Firestore as Base64.
    Returns True if face detected and saved.
    """
    import streamlit as st

    st.info("📸 Please capture your face for registration")

    # Persist camera input across reruns
    if "reg_face" not in st.session_state:
        st.session_state.reg_face = None

    img_file = st.camera_input("Take a photo", key="register_camera")

    if img_file is not None:
        st.session_state.reg_face = img_file

    if st.session_state.reg_face is None:
        return False  # No photo captured yet

    # Convert to OpenCV format
    bytes_data = st.session_state.reg_face.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        st.error("Could not process image")
        return False

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        st.error("No face detected. Make sure you are in good lighting and try again.")
        return False

    # Take the first detected face
    x, y, w, h = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    # Encode face as JPEG bytes
    ret, buffer = cv2.imencode('.jpg', face)
    if not ret:
        st.error("Failed to encode face image")
        return False

    # Convert to Base64 string
    face_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')

    # Store in Firestore (faces collection, document ID = email)
    db.collection('faces').document(email).set({
        'image': face_base64,
        'uploaded_at': firestore.SERVER_TIMESTAMP
    })

    st.success("✅ Face captured and saved successfully!")
    st.session_state.reg_face = None
    return True

def verify_face(email):
    """
    Capture a new face and compare with stored face from Firestore.
    Returns True if matched.
    """
    import streamlit as st

    # Retrieve stored face from Firestore
    face_doc = db.collection('faces').document(email).get()
    if not face_doc.exists:
        st.error("No registered face found. Please register first.")
        return False

    stored_base64 = face_doc.to_dict().get('image')
    if not stored_base64:
        st.error("Stored face data is missing.")
        return False

    # Decode Base64 to image
    stored_bytes = base64.b64decode(stored_base64)
    np_arr_stored = np.frombuffer(stored_bytes, np.uint8)
    stored_face = cv2.imdecode(np_arr_stored, cv2.IMREAD_GRAYSCALE)

    if stored_face is None:
        st.error("Stored face image is corrupted.")
        return False

    # Persist camera input across reruns
    if "verify_face_img" not in st.session_state:
        st.session_state.verify_face_img = None

    img_file = st.camera_input("Take a photo", key="verify_camera")

    if img_file is not None:
        st.session_state.verify_face_img = img_file

    if st.session_state.verify_face_img is None:
        st.info("📸 Please take a photo to continue.")
        return False

    # Convert to OpenCV format
    bytes_data = st.session_state.verify_face_img.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        st.error("Could not process image")
        return False

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        st.error("Face not detected. Make sure you are in good lighting.")
        return False

    # Take the first detected face
    x, y, w, h = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    # Compare with stored face
    diff = cv2.absdiff(stored_face, face)
    score = np.mean(diff)
    st.write(f"Face difference score: {score:.2f}")

    if score < 50:  # threshold can be tuned
        st.success("✅ Face verified successfully!")
        st.session_state.verify_face_img = None
        return True
    else:
        st.error("❌ Face does not match the registered one.")
        st.session_state.verify_face_img = None
        return False
import random
import smtplib
import  streamlit as st
import bcrypt
import cv2
import os
import numpy as np
from dotenv import load_dotenv  

load_dotenv()


# ===== OTP =====
def generate_otp():
    return str(random.randint(100000, 999999))

from email.message import EmailMessage

def send_otp(receiver_email: str, otp: str) -> bool:
    """
    Sends a One-Time Password (OTP) to the specified email address.

    Args:
        receiver_email (str): Recipient's email address
        otp (str): Generated OTP code

    Returns:
        bool: True if email sent successfully, False otherwise
    """

    sender_email = st.secrets["EMAIL_ADDRESS"]
    app_password = st.secrets["EMAIL_APP_PASSWORD"]
    print(sender_email, app_password)

    if not sender_email or not app_password:
        print("Email credentials are not configured.")
        return False

    try:
        # Create email message
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = "Your Anvaya Verification Code"

        msg.set_content(f"""
Hello,

Your One-Time Password (OTP) for verification is:

    {otp}

This code will expire shortly. Do not share this code with anyone.

If you did not request this, please ignore this email.

Regards,  
Team Anvaya
        """)

        # Send email securely
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)

        print(f"OTP successfully sent to {receiver_email}")
        return True

    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return False


# ===== PASSWORD =====
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# ===== FACE =====
import os
import cv2
import numpy as np
import streamlit as st

# -----------------------------
# Capture and save user face
# -----------------------------
def capture_face(email):
    """
    Capture face from browser camera and save for a given email.
    """
    if not os.path.exists("faces"):
        os.makedirs("faces")

    st.info("📸 Please capture your face for registration")

    img_file = st.camera_input("Take a photo")

    if img_file is None:
        return False

    # Convert to OpenCV format
    bytes_data = img_file.getvalue()
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
        st.error("No face detected. Try again in good lighting.")
        return False

    # Take the first face found
    x, y, w, h = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    cv2.imwrite(f"faces/{email}.jpg", face)
    st.success("✅ Face captured successfully!")
    return True

# -----------------------------
# Verify face against stored
# -----------------------------
# -----------------------------
# Capture and save user face (Registration)
# -----------------------------
def capture_face(email):
    """
    Capture face from browser camera and save for a given email.
    Returns True if a face is detected and saved.
    """
    if not os.path.exists("faces"):
        os.makedirs("faces")

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

    # Save to file
    cv2.imwrite(f"faces/{email}.jpg", face)
    st.success("✅ Face captured and saved successfully!")
    # Clear stored image for next attempt
    st.session_state.reg_face = None
    return True

# -----------------------------
# Verify face against stored face (Login)
# -----------------------------
def verify_face(email):
    """
    Capture a new face using st.camera_input and compare with stored face.
    Returns True if matched.
    """
    path = f"faces/{email}.jpg"
    if not os.path.exists(path):
        st.error("No registered face found. Please register first.")
        return False

    stored_face = cv2.imread(path, 0)  # stored grayscale face

    # Persist the captured image across reruns
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
    st.write(f"Face difference score: {score:.2f}")  # optional debug

    if score < 30:  # threshold can be tuned
        st.success("✅ Face verified successfully!")
        # Clear stored image for next attempt
        st.session_state.verify_face_img = None
        return True
    else:
        st.error("❌ Face does not match the registered one.")
        # Clear stored image so user can retry
        st.session_state.verify_face_img = None
        return False

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using the configured SMTP server.

    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        body (str): Plain text email body

    Returns:
        bool: True if email sent successfully, False otherwise
    """
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

        print(f"Email successfully sent to {to_email}")
        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


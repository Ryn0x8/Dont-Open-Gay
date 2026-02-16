import random
import smtplib
from streamlit import st
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
def capture_face(email):
    if not os.path.exists("faces"):
        os.makedirs("faces")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(0)
    for i in range(10):   # capture a few frames to warm up camera
        ret, frame = cap.read()
    cap.release()


    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return False

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))
        cv2.imwrite(f"faces/{email}.jpg", face)
        return True

def verify_face(email):
    path = f"faces/{email}.jpg"
    if not os.path.exists(path):
        return False

    stored_face = cv2.imread(path, 0)

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        print("Face not detected")
        return False

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))

        diff = cv2.absdiff(stored_face, face)
        score = np.mean(diff)
        print(score)

        if score < 30: 
            return True

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


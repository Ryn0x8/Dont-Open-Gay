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
from insightface.app import FaceAnalysis
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from modelDownload import download_model


load_dotenv()

# Initialize Firebase Admin SDK (assumes database.py already did, but safe)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

@st.cache_resource
def load_models():
    # InsightFace for detection + recognition
    model_root = os.path.join(os.getcwd(), "models")
    if not os.path.exists(model_root):
        success = download_model()
        if not success:
            st.error("Failed to load face recognition model. Please check your internet connection.")
            return None, None
    
    app = FaceAnalysis(name='buffalo_l', root=model_root, providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    # MediaPipe Tasks for blink detection (new API)
    # Download the face landmarker model if not present
    landmarker_model_path = os.path.join(model_root, "face_landmarker.task")
    if not os.path.exists(landmarker_model_path):
        # Download face landmarker model from MediaPipe
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        urllib.request.urlretrieve(url, landmarker_model_path)
    
    # Create FaceLandmarker from the model
    base_options = python.BaseOptions(model_asset_path=landmarker_model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)
    
    return app, landmarker

app, landmarker = load_models()

# -------------------------------------------------------------------
# Helper: Get face embedding using InsightFace
# -------------------------------------------------------------------
def get_face_embedding(image):
    """
    Detect face and return embedding (512-dim) or None.
    """
    faces = app.get(image)  # insightface detects and returns face objects
    if len(faces) == 0:
        return None
    # Use the first face (largest)
    embedding = faces[0].normed_embedding  # already normalized
    return np.array(embedding)

# -------------------------------------------------------------------
# Helper: Eye Aspect Ratio (EAR) for blink detection using MediaPipe Tasks
# -------------------------------------------------------------------
def eye_aspect_ratio(landmarks, eye_indices):
    """
    Compute EAR from MediaPipe landmarks.
    landmarks: list of NormalizedLandmark objects
    eye_indices: list of landmark indices for the eye
    """
    points = []
    for idx in eye_indices:
        landmark = landmarks[idx]
        points.append([landmark.x, landmark.y])
    points = np.array(points)
    A = np.linalg.norm(points[1] - points[5])
    B = np.linalg.norm(points[2] - points[4])
    C = np.linalg.norm(points[0] - points[3])
    ear = (A + B) / (2.0 * C)
    return ear

def get_ear_from_image(image):
    """
    Process image with MediaPipe FaceLandmarker and return EAR.
    Returns (ear_value, success_flag)
    """
    # Convert to MediaPipe Image
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    
    # Detect face landmarks
    detection_result = landmarker.detect(mp_image)
    
    if not detection_result.face_landmarks:
        return None, False
    
    # Get landmarks for the first face
    landmarks = detection_result.face_landmarks[0]
    
    # Eye landmark indices for MediaPipe Face Landmarker
    # These are the standard indices for eye contours
    left_eye_indices = [33, 133, 157, 158, 159, 160]
    right_eye_indices = [362, 263, 387, 386, 385, 384]
    
    left_ear = eye_aspect_ratio(landmarks, left_eye_indices)
    right_ear = eye_aspect_ratio(landmarks, right_eye_indices)
    ear = (left_ear + right_ear) / 2.0
    
    return ear, True

# -------------------------------------------------------------------
# New: Capture face (registration) – stores embedding
# -------------------------------------------------------------------
def capture_face(email):
    st.info("📸 Look at the camera to register your face")
    if "reg_face" not in st.session_state:
        st.session_state.reg_face = None

    img_file = st.camera_input("Take a photo", key="register_camera")
    if img_file is not None:
        st.session_state.reg_face = img_file

    if st.session_state.reg_face is None:
        return False

    # Convert to OpenCV
    bytes_data = st.session_state.reg_face.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    embedding = get_face_embedding(frame)
    if embedding is None:
        st.error("No face detected. Please try again.")
        return False

    # Store embedding in Firestore
    db.collection('faces').document(email).set({
        'embedding': embedding.tolist(),
        'uploaded_at': firestore.SERVER_TIMESTAMP
    })
    st.success("✅ Face registered!")
    st.session_state.reg_face = None
    return True

# -------------------------------------------------------------------
# New: Verify face with liveness (blink detection)
# -------------------------------------------------------------------
def verify_face(email):
    """
    1. Liveness: detect a blink via webcam.
    2. Capture final photo, compute embedding, compare with stored.
    """
    # ---- Liveness check ----
    st.markdown("### 👁️ Liveness Check – Please Blink")
    
    # Capture photo with eyes open
    st.write("Take a photo with your eyes open.")
    open_img = st.camera_input("Open eyes", key="open_eyes")
    if open_img is None:
        return False

    # Convert open eyes frame
    bytes_data = open_img.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    open_frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Compute EAR on open eyes
    ear_open, success = get_ear_from_image(open_frame)
    if not success:
        st.error("No face detected. Please try again.")
        return False

    # Capture photo with eyes closed
    st.write("Now take a photo with your eyes **closed**.")
    closed_img = st.camera_input("Closed eyes", key="closed_eyes")
    if closed_img is None:
        return False

    bytes_data = closed_img.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    closed_frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    ear_closed, success = get_ear_from_image(closed_frame)
    if not success:
        st.error("No face detected.")
        return False

    # If EAR dropped significantly, we have a blink
    if ear_open - ear_closed > 0.15:  # threshold
        st.success("✅ Blink detected – you're live!")
    else:
        st.error("❌ Blink not detected. Please try again.")
        return False

    # ---- Face verification ----
    st.write("Now take a final photo for identity verification.")
    final_img = st.camera_input("Final photo", key="final_face")
    if final_img is None:
        return False

    bytes_data = final_img.getvalue()
    np_arr = np.frombuffer(bytes_data, np.uint8)
    final_frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    new_embedding = get_face_embedding(final_frame)
    if new_embedding is None:
        st.error("No face detected.")
        return False

    # Retrieve stored embedding
    doc = db.collection('faces').document(email).get()
    if not doc.exists:
        st.error("No registered face.")
        return False
    stored_emb = np.array(doc.to_dict()['embedding'])

    # Cosine similarity
    similarity = np.dot(new_embedding, stored_emb) / (np.linalg.norm(new_embedding) * np.linalg.norm(stored_emb))
    st.write(f"Similarity: **{similarity:.2f}**")

    if similarity > 0.5:  # threshold for ArcFace is usually around 0.5-0.6
        st.success("✅ Face verified!")
        return True
    else:
        st.error("❌ Face does not match.")
        return False

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
#
#     st.info("📸 Please capture your face for registration")
#
#     # Persist camera input across reruns
#     if "reg_face" not in st.session_state:
#         st.session_state.reg_face = None
#
#     img_file = st.camera_input("Take a photo", key="register_camera")
#
#     if img_file is not None:
#         st.session_state.reg_face = img_file
#
#     if st.session_state.reg_face is None:
#         return False  # No photo captured yet
#
#     # Convert to OpenCV format
#     bytes_data = st.session_state.reg_face.getvalue()
#     np_arr = np.frombuffer(bytes_data, np.uint8)
#     frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
#
#     if frame is None:
#         st.error("Could not process image")
#         return False
#
#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#     )
#
#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)
#
#     if len(faces) == 0:
#         st.error("No face detected. Make sure you are in good lighting and try again.")
#         return False
#
#     # Take the first detected face
#     x, y, w, h = faces[0]
#     face = gray[y:y+h, x:x+w]
#     face = cv2.resize(face, (200, 200))
#
#     # Encode face as JPEG bytes
#     ret, buffer = cv2.imencode('.jpg', face)
#     if not ret:
#         st.error("Failed to encode face image")
#         return False
#
#     # Convert to Base64 string
#     face_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
#
#     # Store in Firestore (faces collection, document ID = email)
#     db.collection('faces').document(email).set({
#         'image': face_base64,
#         'uploaded_at': firestore.SERVER_TIMESTAMP
#     })
#
#     st.success("✅ Face captured and saved successfully!")
#     st.session_state.reg_face = None
#     return True
#
# def verify_face(email):
#     """
#     Capture a new face and compare with stored face from Firestore.
#     Returns True if matched.
#     """
#     import streamlit as st
#
#     # Retrieve stored face from Firestore
#     face_doc = db.collection('faces').document(email).get()
#     if not face_doc.exists:
#         st.error("No registered face found. Please register first.")
#         return False
#
#     stored_base64 = face_doc.to_dict().get('image')
#     if not stored_base64:
#         st.error("Stored face data is missing.")
#         return False
#
#     # Decode Base64 to image
#     stored_bytes = base64.b64decode(stored_base64)
#     np_arr_stored = np.frombuffer(stored_bytes, np.uint8)
#     stored_face = cv2.imdecode(np_arr_stored, cv2.IMREAD_GRAYSCALE)
#
#     if stored_face is None:
#         st.error("Stored face image is corrupted.")
#         return False
#
#     # Persist camera input across reruns
#     if "verify_face_img" not in st.session_state:
#         st.session_state.verify_face_img = None
#
#     img_file = st.camera_input("Take a photo", key="verify_camera")
#
#     if img_file is not None:
#         st.session_state.verify_face_img = img_file
#
#     if st.session_state.verify_face_img is None:
#         st.info("📸 Please take a photo to continue.")
#         return False
#
#     # Convert to OpenCV format
#     bytes_data = st.session_state.verify_face_img.getvalue()
#     np_arr = np.frombuffer(bytes_data, np.uint8)
#     frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
#
#     if frame is None:
#         st.error("Could not process image")
#         return False
#
#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#     )
#
#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)
#
#     if len(faces) == 0:
#         st.error("Face not detected. Make sure you are in good lighting.")
#         return False
#
#     # Take the first detected face
#     x, y, w, h = faces[0]
#     face = gray[y:y+h, x:x+w]
#     face = cv2.resize(face, (200, 200))
#
#     # Compare with stored face
#     diff = cv2.absdiff(stored_face, face)
#     score = np.mean(diff)
#     st.write(f"Face difference score: {score:.2f}")
#
#     if score < 50:  # threshold can be tuned
#         st.success("✅ Face verified successfully!")
#         st.session_state.verify_face_img = None
#         return True
#     else:
#         st.error("❌ Face does not match the registered one.")
#         st.session_state.verify_face_img = None
#         return False
#
# def has_face_registered(email):
#     face_ref = db.collection('faces').document(email)
#     face_doc = face_ref.get()
#     return face_doc.exists
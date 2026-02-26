import os
import zipfile
import gdown
import streamlit as st

MODEL_DIR = os.path.join(os.getcwd(), "models", "buffalo_l")
ZIP_PATH = os.path.join(os.getcwd(), "buffalo_l.zip")

def download_model():
    if os.path.exists(MODEL_DIR):
        print("✅ Model already exists.")
        return True

    os.makedirs(os.path.dirname(MODEL_DIR), exist_ok=True)

    # Google Drive file ID (replace with your own)
    file_id = st.secrets["BUFFALO_L_FILE_ID"]
    url = f"https://drive.google.com/uc?id={file_id}"

    try:
        print("📥 Downloading buffalo_l model (326 MB)...")
        gdown.download(url, ZIP_PATH, quiet=False)

        print("📦 Extracting...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(MODEL_DIR)

        print("✅ Model ready.")
        return True

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

    finally:
        if os.path.exists(ZIP_PATH):
            os.remove(ZIP_PATH)
import base64
import io
import json
import os
from PIL import Image
import pdf2image
import google.generativeai as genai
import streamlit as st
import PyPDF2

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def sanitize_text(text):
    """Remove any characters that cannot be encoded in UTF‑8 (e.g., emoji surrogates)."""
    if text is None:
        return ""
    return text.encode('utf-8', errors='ignore').decode('utf-8')

def extract_text_from_pdf(uploaded_file):
    """Extract text from all pages of a PDF and sanitize it."""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.warning(f"Text extraction failed: {e}. Falling back to image only.")
    return sanitize_text(text)

def input_pdf_setup(uploaded_file, max_pages=3):
    """
    Convert first few pages of PDF to images.
    Returns list of image parts for Gemini.
    """
    images = pdf2image.convert_from_bytes(uploaded_file.read())
    pdf_parts = []
    for i, img in enumerate(images[:max_pages]):
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        pdf_parts.append({
            "mime_type": "image/jpeg",
            "data": base64.b64encode(img_byte_arr).decode('utf-8')
        })
    return pdf_parts

def evaluate_candidate(resume_file, job_description, job_skills):
    """
    Evaluate a resume against a job description and required skills using Gemini.
    Returns a dict with 'score' (int) and 'explanation' (str), or None.
    """
    # Sanitize job details
    job_description = sanitize_text(job_description)
    job_skills = sanitize_text(job_skills)

    prompt = f"""
You are an experienced Technical HR Manager. Evaluate the provided resume against the job description and required skills below.

**Job Description:**
{job_description}

**Required Skills:**
{job_skills}

**Instructions:**
- Score the match from 0 to 100 (100 = perfect fit).
- Base your evaluation **only** on the content of the resume and the job description/skills.
- Do not use any external knowledge or make assumptions.
- Respond **only** with a valid JSON object containing two keys: "score" (integer) and "explanation" (string). The explanation should briefly summarise the fit and, if the score is low, point out the key missing skills or mismatches.

**Resume:"""
    
    # Prepare content
    content_parts = []
    
    # Try text extraction first (resume_file may have been read, so reset pointer)
    resume_file.seek(0)
    resume_text = extract_text_from_pdf(resume_file)
    if resume_text:
        # resume_text is already sanitized
        content_parts.append(resume_text)
    else:
        # Fallback to images
        resume_file.seek(0)
        image_parts = input_pdf_setup(resume_file)
        content_parts.extend(image_parts)
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([prompt] + content_parts)
        
        # Sanitize the response text before parsing
        result_text = sanitize_text(response.text)
        # Remove possible markdown code fences
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        if "score" in result and "explanation" in result:
            # Sanitize explanation before returning (for display)
            result["explanation"] = sanitize_text(result["explanation"])
            return result
        else:
            st.error("Gemini response missing required fields.")
            return None
    except json.JSONDecodeError:
        st.error("Could not parse Gemini response as JSON.")
        return None
    except Exception as e:
        st.error(f"Evaluation failed: {e}")
        return None
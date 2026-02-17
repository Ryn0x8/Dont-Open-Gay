import base64
import io
import json
import os
from PIL import Image
import pdf2image
import google.generativeai as genai
import streamlit as st
import PyPDF2  # or pdfplumber

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def extract_text_from_pdf(uploaded_file):
    """Extract text from all pages of a PDF."""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.warning(f"Text extraction failed: {e}. Falling back to image only.")
    return text.strip()

def input_pdf_setup(uploaded_file, max_pages=3):
    """
    Convert first few pages of PDF to images.
    Returns list of image parts for Gemini.
    """
    images = pdf2image.convert_from_bytes(uploaded_file.read())
    pdf_parts = []
    for i, img in enumerate(images[:max_pages]):  # limit pages to avoid token overflow
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        pdf_parts.append({
            "mime_type": "image/jpeg",
            "data": base64.b64encode(img_byte_arr).decode('utf-8')
        })
    return pdf_parts

def evaluate_candidate(resume_file, job_description):
    """
    Evaluate a resume against a job description using Gemini.
    Returns a dict with 'score' (int) and 'explanation' (str), or None.
    """
    prompt = """
You are an experienced Technical HR Manager. Evaluate the provided resume against the job description.

**Instructions:**
- Score the match from 0 to 100 (100 = perfect fit).
- Base your evaluation **only** on the content of the resume and job description.
- Do not use any external knowledge or make assumptions.
- Respond **only** with a valid JSON object containing two keys: "score" (integer) and "explanation" (string).

**Job Description:**
{job_description}

**Resume:"""
    
    # Prepare content
    content_parts = []
    
    # Try to extract text first (more reliable)
    resume_text = extract_text_from_pdf(resume_file)
    if resume_text:
        content_parts.append(resume_text)
    else:
        # Fallback to images
        resume_file.seek(0)  # reset file pointer
        image_parts = input_pdf_setup(resume_file)
        content_parts.extend(image_parts)
    
    # Build the full prompt with job description embedded
    full_prompt = prompt.format(job_description=job_description)
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([full_prompt] + content_parts)
        
        # Parse JSON from response
        result_text = response.text.strip()
        # Sometimes the model wraps JSON in ```json ... ```
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        # Validate structure
        if "score" in result and "explanation" in result:
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
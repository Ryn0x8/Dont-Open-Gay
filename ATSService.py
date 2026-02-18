import io
import json
import fitz  # PyMuPDF
import google.generativeai as genai
import streamlit as st

def sanitize_text(text):
    """Clean text and replace common problematic symbols."""
    if text is None:
        return ""
    clean_text = text.encode("utf-8", errors="ignore").decode("utf-8")
    replacements = {
        "•": "-",
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
    }
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)
    return clean_text

def extract_text_from_pdf(file):
    """Extract text from all pages of a PDF using PyMuPDF."""
    text = ""
    try:
        file.seek(0)
        doc = fitz.open(stream=file.read(), filetype="pdf")
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                text += page_text + "\n"
        doc.close()
    except Exception:
        return None
    return sanitize_text(text)

def evaluate_candidate(resume_file, job_description, job_skills):
    """
    Evaluate a resume using Gemini.
    Returns:
        dict: {"score": int, "explanation": str}
    Shows st.error in Streamlit if any failure occurs.
    """
    # Get API keys from Streamlit secrets
    GEMINI_API_KEYS = [
        st.secrets.get("GEMINI_API_KEY_1", ""),
        st.secrets.get("GEMINI_API_KEY_2", "")
    ]

    job_description = sanitize_text(job_description)
    job_skills = sanitize_text(job_skills)

    resume_text = extract_text_from_pdf(resume_file)
    if not resume_text:
        st.error("Failed to extract text from PDF.")
        return None

    prompt = f"""
You are an experienced Technical HR Manager. Evaluate the provided resume against the job description and required skills below.

**Job Description:**
{job_description}

**Required Skills:**
{job_skills}

**Instructions:**
- Score the match from 0 to 100 (100 = perfect fit).
- Base your evaluation only on the content of the resume and the job description/skills.
- Respond only with a valid JSON object containing two keys: "score" (integer) and "explanation" (string).

**Resume:**
{resume_text}
"""

    last_exception = None
    for api_key in GEMINI_API_KEYS:
        if not api_key:
            continue
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([prompt])
            result_text = sanitize_text(response.text)

            # Remove possible code fences
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            if "score" in result and "explanation" in result:
                result["explanation"] = sanitize_text(result["explanation"])
                return result
            else:
                st.error("Gemini response missing required fields.")
                return None

        except json.JSONDecodeError:
            st.error("Could not parse Gemini response as JSON.")
            return None
        except Exception as e:
            last_exception = e
            if "429" in str(e) or "rate limit" in str(e).lower():
                # try next key
                continue
            else:
                st.error("Failed to connect with Gemini API.")
                return None

    if last_exception:
        if "429" in str(last_exception) or "rate limit" in str(last_exception).lower():
            st.error("Rate limit reached for all API keys.")
        else:
            st.error(f"Failed to connect with Gemini API: {last_exception}")
    return None

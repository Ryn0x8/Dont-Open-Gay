from openai import OpenAI
import os
import json
import streamlit as st
import fitz  

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

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

def extract_text_from_pdf(pdf_bytes):
    """Extract text from uploaded PDF file bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        st.error(f"Failed to extract PDF text: {e}")
        return ""
    return sanitize_text(text)

def parse_resume_with_groq(resume_text):
    """Call Groq API to extract structured fields from resume text."""
    prompt = f"""
You are a strict resume parser.

Extract the following fields and return ONLY valid JSON.

Fields:
- location
- experience_level (Must be one of: Entry, Junior, Mid, Senior, Lead)
- phone_number
- skills (array of strings)
- bio (2-3 line professional summary)
- github_link
- linkedin_link
- portfolio_link

Rules:
- If a field cannot be found, return "".
- Do NOT guess missing information.
- Return ONLY valid JSON.
- No explanations.

Resume Text:
\"\"\"
{resume_text}
\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You extract structured data from resumes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)
    except Exception as e:
        st.error(f"AI parsing failed: {e}")
        return {
            "location": "",
            "experience_level": "",
            "phone_number": "",
            "skills": [],
            "bio": "",
            "github_link": "",
            "linkedin_link": "",
            "portfolio_link": ""
        }

def get_resume_goodness_score(resume_text):
    """Get a short, constructive feedback on the resume."""
    prompt = f"""
You are a career coach. Give a very short, constructive feedback (max 2‑3 lines) on this resume. 
Focus on strengths and one area for improvement. Be concise and encouraging.

Resume:
\"\"\"
{resume_text[:5000]}  # limit to avoid token issues
\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You give brief, helpful resume feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Could not generate score at this time."
    
    # --- Helper functions (place after existing helpers) ---
import requests
import json

def fetch_github_repos(github_username):
    if not github_username:
        return []
    url = f"https://api.github.com/users/{github_username}/repos"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            repos = resp.json()
            return [{"name": r["name"], "description": r.get("description", ""), "url": r["html_url"]} for r in repos]
        else:
            st.error(f"GitHub API error: {resp.status_code}")
            return []
    except Exception as e:
        st.error(f"Failed to fetch GitHub repos: {e}")
        return []
def get_ai_career_suggestions(skills, experience_level, resume_text=""):
    prompt = f"""
You are a career advisor. Based on the user's skills, experience level, and resume, suggest 3-4 potential career paths or job titles that would be a good fit. Be specific and concise. Return as a bullet list with short explanations.

Skills: {skills}
Experience Level: {experience_level}
Resume excerpt: {resume_text[:2000] if resume_text else "Not provided"}

Suggestions:
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You provide concise career suggestions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate suggestions: {e}"

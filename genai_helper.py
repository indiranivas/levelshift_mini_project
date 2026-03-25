"""
genai_helper.py
---------------
Shared helper for Gemini API calls using the new google-genai SDK.
Handles rate limiting, model fallback, and missing API key gracefully.
"""

import os
import time

GOOGLE_API_KEY = "" #api

# Models to try in order (most capable → most available)
_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def _get_client():
    from google import genai
    return genai.Client(api_key=GOOGLE_API_KEY)


def call_gemini(prompt: str, retries: int = 2) -> str:
    """
    Call the Gemini API with automatic model fallback and rate-limit retry.
    Returns the response text, or a fallback string on failure.
    """
    if not GOOGLE_API_KEY:
        return (
            "_Set `GOOGLE_API_KEY` environment variable to enable AI features._\n\n"
            "**Demo output:** This candidate has strong domain knowledge with relevant skills "
            "and structured work history."
        )

    try:
        client = _get_client()
    except ImportError:
        return "_google-genai package not installed. Run: pip install google-genai_"

    last_error = None
    for model in _MODELS:
        for attempt in range(retries + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Rate limited — wait and retry once, then try next model
                    if attempt < retries:
                        wait = 3  # wait shorter time before retry, or fail over gracefully
                        time.sleep(wait)
                    else:
                        last_error = e
                        break  # try next model
                elif "404" in err_str or "not found" in err_str.lower():
                    last_error = e
                    break  # model doesn't exist, try next
                else:
                    last_error = e
                    break

    return f"_AI temporarily unavailable ({type(last_error).__name__}). Please try again in a moment._"


# ─── Convenience wrappers ─────────────────────────────────────

def summarize_resume(resume_text: str, job_description: str = "") -> str:
    jd_part = f"\nJob Description:\n{job_description[:500]}" if job_description else ""
    prompt = f"""You are an expert recruiter. Summarize the following resume in 5-6 bullet points.
Highlight: key skills, total experience, education, and standout achievements.{jd_part}

Resume:
{resume_text[:3000]}"""
    return call_gemini(prompt)


def generate_interview_questions(resume_text: str, job_description: str = "") -> str:
    jd_part = f"\nJob Description:\n{job_description[:500]}" if job_description else ""
    prompt = f"""You are an expert technical interviewer.
Generate 8 targeted interview questions (mix of technical and behavioural) based on this resume.{jd_part}

Resume:
{resume_text[:2500]}"""
    return call_gemini(prompt)


def generate_feedback(resume_text: str, job_description: str = "") -> str:
    jd_part = f"\nJob Description:\n{job_description[:500]}" if job_description else ""
    prompt = f"""You are a senior recruiter. Provide structured candidate feedback:
1. Strengths (3 points)
2. Weaknesses / Gaps (3 points)
3. Overall Recommendation (Shortlist / Hold / Reject with justification){jd_part}

Resume:
{resume_text[:2500]}"""
    return call_gemini(prompt)


def answer_hiring_question(question: str, context: str = "") -> str:
    ctx_part = f"\nContext from company hiring policy and database:\n{context}" if context else ""
    prompt = f"""You are a helpful HR assistant for TalentAI Solutions.
Answer the following recruiter question clearly and concisely. You have access to the company's hiring policy and current candidate database details.{ctx_part}

Question: {question}"""
    return call_gemini(prompt)

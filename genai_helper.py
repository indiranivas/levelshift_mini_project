"""
genai_helper.py
---------------
Shared helper for Gemini API calls using the new google-genai SDK.
Handles rate limiting, model fallback, and missing API key gracefully.
"""

import os
import time

<<<<<<< HEAD
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
=======
GOOGLE_API_KEY = "" #api
>>>>>>> b3e3381b161d14e48dfa23a52c0ab1a9b53d316d

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
                elif "403" in err_str or "PERMISSION_DENIED" in err_str:
                    return f"**Demo Output (API Key Error):** The configured API key is invalid or leaked. Please configure a valid `GOOGLE_API_KEY`.\n\n_System fallback active. The candidate shows strong potential and aligns well with the required skills._"
                else:
                    last_error = e
                    break

    # If it completely fails, string fallback for testing instead of throwing UI errors.
    return f"**Demo Output (AI Unavailable):** Please check your API key and connection.\n\n_System fallback active. ({type(last_error).__name__} encountered)._"


def _local_text_embedding(text: str) -> list[float]:
    """Fast local fallback embedding when remote service is not available."""
    if not text:
        return [0.0] * 768
    try:
        vectorizer = TfidfVectorizer(max_features=768, stop_words='english')
        arr = vectorizer.fit_transform([text]).toarray()[0]
        if len(arr) < 768:
            padded = np.zeros(768, dtype=float)
            padded[:len(arr)] = arr
            return padded.tolist()
        return arr.tolist()
    except Exception:
        return [0.0] * 768


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

    # Keep the app responsive when API is unavailable by using a lightweight fallback.
    if not GOOGLE_API_KEY or os.getenv('DISABLE_GENAI', '0').lower() in ('1', 'true', 'yes'):
        return (
            "[Fallback response] AI service is currently unavailable. "
            "Here are recommendations based on local startup data: \n"
            "- Review top candidates by match score\n"
            "- Check skill overlap and experience alignment\n"
            "- Manually finalize shortlist where high confidence exists"
        )

    return call_gemini(prompt)

def interpret_candidate_query(question: str, db_schema: str = "") -> str:
    """Uses GenAI to understand what candidate information the user is asking for."""
    schema_context = f"\n\n{db_schema}" if db_schema else ""
    
    prompt = f"""You are a recruiter assistant. The user has asked a question about candidates.
Analyze their question and identify what specific information they're looking for at the DATABASE LEVEL.
Respond with a JSON object with these fields (ONLY these fields, no SQL!):
- search_keywords: comma-separated skills/titles they're asking about (empty string if none)
- experience_min: minimum years of experience (integer, 0 if not specified)
- experience_max: maximum years of experience (integer, 999 if not specified)
- status_filter: filter by prediction status ('Shortlisted', 'Rejected', 'Pending', or 'All')
- match_score_min: minimum match score (0-100, integer)
- limit: number of candidates to return (integer, default 10, max 100)

IMPORTANT:
- Do NOT generate SQL queries
- Do NOT include any field other than the 6 specified above
- Only return valid JSON
- Interpret naturally from the question (e.g., 'Python developers' -> search_keywords: 'Python,Developer'){schema_context}

User Question: {question}

Respond ONLY with valid JSON, no other text."""
    
    if not GOOGLE_API_KEY or os.getenv('DISABLE_GENAI', '0').lower() in ('1', 'true', 'yes'):
        # Fallback: return default filters
        return '{"search_keywords": "", "experience_min": 0, "experience_max": 999, "status_filter": "All", "match_score_min": 0, "limit": 10}'
    
    return call_gemini(prompt)

def format_candidate_data_response(question: str, candidates_data: str, db_schema: str = "") -> str:
    """Uses GenAI to format raw candidate data into a comprehensive answer."""
    schema_context = f"\n\nDATABASE SCHEMA (for reference):\n{db_schema}" if db_schema else ""
    
    prompt = f"""You are a helpful recruiter assistant. The user asked a question about candidates.
You have retrieved candidate data from the database via READ-ONLY queries.
Analyze the data and provide a comprehensive, well-formatted answer to their question.
Include insights, patterns, and recommendations based on the data.

User's Original Question: {question}

Candidate Data Retrieved from Database:
{candidates_data}{schema_context}

Provide a clear, professional response that directly answers their question.
Organize the information in a readable format with clear sections.
Be specific about numbers, percentages, and comparisons when analyzing the data."""
    
    if not GOOGLE_API_KEY or os.getenv('DISABLE_GENAI', '0').lower() in ('1', 'true', 'yes'):
        return f"Retrieved candidates based on your query: {question}\n\n{candidates_data}"
    
    return call_gemini(prompt)

def get_embedding(text: str) -> list[float]:
    """Generate a dense vector embedding using Google Gemini with fast local fallback."""
    if not text:
        return [0.0] * 768

    if not GOOGLE_API_KEY or os.getenv('DISABLE_GENAI', '0').lower() in ('1', 'true', 'yes'):
        return _local_text_embedding(text)

    try:
        client = _get_client()
    except Exception as e:
        print(f"GenAI client init error: {e}. Using local fallback embedding.")
        return _local_text_embedding(text)

    last_error = None
    start_ts = time.time()

    # Try multiple embedding models with a timeout
    for model in ["text-embedding-004", "gemini-embedding-001", "gemini-embedding-2-preview", "models/embedding-001"]:
        try:
            response = client.models.embed_content(
                model=model,
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str:
                continue
            if "403" in err_str or "permission_denied" in err_str or "429" in err_str:
                break

        if time.time() - start_ts > 5.0:
            print("GenAI embedding deadline reached, using local fallback.")
            break

    print(f"Error generating embedding: {last_error}. Returning local style embedding.")
    return _local_text_embedding(text)

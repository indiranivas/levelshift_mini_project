"""
rag_engine.py
-------------
Simple, fast RAG engine for candidate retrieval using local TF-IDF embeddings.
No external API dependencies for embeddings; uses sklearn TfidfVectorizer.
"""

import os
import sys
import json
import sqlite3
import numpy as np
import joblib
from sklearn.metrics.pairwise import cosine_similarity

# Adjust path so we can import app DB
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# IMPORTANT: RAG must use the same DB as Flask (config.py -> DATABASE_PATH env var).
DB_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hiring.db"),
)

# Global vectorizer and cache
_VECTORIZER = None
_EMBEDDINGS_CACHE = {}  # {candidate_id: (candidate_data, tfidf_vector_dense)}
_LAST_INDEXED_TIMESTAMP = 0.0

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def _get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _generate_candidate_summary(row) -> str:
    """Creates a plain-text summary for TF-IDF embedding."""
    try:
        skills = json.loads(row['skills']) if row['skills'] else []
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    except Exception:
        skills_str = "None"

    prediction = row['prediction'] or "Unknown"
    shortlisted_status = "explicitly shortlisted" if row['is_shortlisted'] else "not shortlisted"

    return (
        f"Name: {row['name']}. "
        f"Title: {row['title']}. "
        f"Experience: {row['experience']} years. "
        f"Skills: {skills_str}. "
        f"Match Score: {row['match_score']}%. "
        f"Status: {prediction}. "
        f"Shortlisting: {shortlisted_status}. "
        f"Resume: {(row['resume_text'] or '')[:400]}"
    )


def _get_or_create_vectorizer():
    """Lazy-load the persisted TF-IDF vectorizer (no refitting)."""
    global _VECTORIZER
    if _VECTORIZER is None:
        try:
            _VECTORIZER = joblib.load(os.path.join(MODEL_PATH, "tfidf_vectorizer.pkl"))
        except Exception as e:
            print(f"WARNING: Could not load TF-IDF vectorizer for RAG: {e}")
            _VECTORIZER = None
    return _VECTORIZER


def build_or_update_index():
    """
    Incrementally sync the in-memory RAG cache with the SQLite database.

    Key requirement: do NOT refit TF-IDF vectorizers. We only call
    `vectorizer.transform(...)` using the persisted vectorizer.
    """
    global _EMBEDDINGS_CACHE, _LAST_INDEXED_TIMESTAMP, _VECTORIZER

    try:
        vectorizer = _get_or_create_vectorizer()
        if vectorizer is None:
            return

        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, title, experience, skills, match_score, resume_text, is_shortlisted, prediction, timestamp "
                "FROM candidates WHERE timestamp > ? ORDER BY timestamp ASC",
                (_LAST_INDEXED_TIMESTAMP,),
            ).fetchall()

        if not rows:
            return

        max_ts = _LAST_INDEXED_TIMESTAMP
        for r in rows:
            cid = r["id"]
            max_ts = max(max_ts, float(r["timestamp"] or 0.0))

            # Skip if already cached (safety if timestamps collide).
            if cid in _EMBEDDINGS_CACHE:
                continue

            cand_data = dict(r)
            summary = _generate_candidate_summary(cand_data)
            vec = vectorizer.transform([summary]).toarray()[0]
            _EMBEDDINGS_CACHE[cid] = (cand_data, vec)

        _LAST_INDEXED_TIMESTAMP = max_ts
    except Exception as e:
        print(f"RAG Index Error: {e}")


def search_relevant_candidates(query: str, top_k: int = 3) -> list:
    """
    Embeds the query using TF-IDF and returns top K relevant candidates.
    Always returns results, even if no strong matches.
    """
    global _EMBEDDINGS_CACHE

    build_or_update_index()

    if not _EMBEDDINGS_CACHE:
        # Fallback to DB top match_score
        with _get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM candidates ORDER BY match_score DESC LIMIT ?", (top_k,)).fetchall()
            return [dict(r, **{'rag_similarity': round((r['match_score'] or 0) / 100.0, 4)}) for r in rows]

    vectorizer = _get_or_create_vectorizer()
    query_vector = vectorizer.transform([query]).toarray()[0]

    candidates = []
    vectors = []
    for _, (cand_data, vec) in _EMBEDDINGS_CACHE.items():
        candidates.append(cand_data)
        vectors.append(vec)

    vectors_matrix = np.array(vectors)
    similarities = cosine_similarity([query_vector], vectors_matrix)[0]

    candidate_items = [(cand, float(sim)) for cand, sim in zip(candidates, similarities)]
    candidate_items.sort(key=lambda x: x[1], reverse=True)

    results = []
    for cand, sim in candidate_items[:top_k]:
        candidate_copy = dict(cand)
        candidate_copy['rag_similarity'] = round(sim, 4)
        results.append(candidate_copy)

    return results


def get_database_schema() -> str:
    """
    Returns the database schema/structure as a string for GenAI context.
    """
    schema = """DATABASE SCHEMA:

Table: candidates
Columns:
  - id (TEXT): Unique candidate identifier
  - name (TEXT): Candidate full name
  - email (TEXT): Candidate email address
  - experience (REAL): Total years of experience
  - title (TEXT): Current job title/role
  - match_score (INTEGER): AI match score (0-100)
  - prediction (TEXT): Prediction status ('Shortlisted', 'Rejected', 'Pending')
  - resume_text (TEXT): Full resume content
  - skills (TEXT): JSON array of candidate skills
  - timestamp (REAL): When candidate was added
  - is_shortlisted (INTEGER): Manual shortlist flag (0 or 1)
"""
    return schema


def search_candidates_with_filters(keywords: str = "", experience_min: int = 0, experience_max: int = 999, 
                                   status_filter: str = "All", match_score_min: int = 0, limit: int = 10) -> list:
    """
    Advanced candidate search with multiple filters.
    Returns candidates matching the specified criteria from the database.
    """
    try:
        with _get_db_connection() as conn:
            query = "SELECT * FROM candidates WHERE 1=1"
            params = []
            
            # Experience filter
            if experience_min > 0:
                query += " AND experience >= ?"
                params.append(experience_min)
            if experience_max < 999:
                query += " AND experience <= ?"
                params.append(experience_max)
            
            # Match score filter
            if match_score_min > 0:
                query += " AND match_score >= ?"
                params.append(match_score_min)
            
            # Status filter
            if status_filter != "All":
                query += " AND prediction = ?"
                params.append(status_filter)
            
            # Keyword search in skills, name, title
            if keywords:
                keyword_list = [kw.strip().lower() for kw in keywords.split(',') if kw.strip()]
                if keyword_list:
                    # Search in skills (JSON), name, and title
                    condition_parts = []
                    for kw in keyword_list:
                        # Parameterized LIKE patterns (prevents SQL injection).
                        condition_parts.append("(LOWER(name) LIKE ? OR LOWER(title) LIKE ? OR LOWER(skills) LIKE ?)")
                        pattern = f"%{kw}%"
                        params.extend([pattern, pattern, pattern])
                    query += " AND (" + " OR ".join(condition_parts) + ")"
            
            query += " ORDER BY match_score DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            results = []
            for row in rows:
                candidate = dict(row)
                # Parse skills JSON
                try:
                    candidate['skills'] = json.loads(candidate['skills']) if candidate['skills'] else []
                except ValueError:
                    candidate['skills'] = []
                results.append(candidate)
            
            return results
    except Exception as e:
        print(f"Error in advanced candidate search: {e}")
        return []


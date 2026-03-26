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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Adjust path so we can import app DB
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hiring.db")

# Global vectorizer and cache
_VECTORIZER = None
_EMBEDDINGS_CACHE = {}  # {candidate_id: (candidate_data, tfidf_vector)}
_LAST_INDEXED_COUNT = 0


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
        f"Resume: {row['resume_text'][:400]}"
    )


def _get_or_create_vectorizer():
    """Lazy init TF-IDF vectorizer."""
    global _VECTORIZER
    if _VECTORIZER is None:
        _VECTORIZER = TfidfVectorizer(stop_words='english', max_features=1000)
    return _VECTORIZER


def build_or_update_index():
    """
    Syncs the local TF-IDF cache with the SQLite database.
    Only processes new candidates; uses a count check to avoid re-processing.
    """
    global _EMBEDDINGS_CACHE, _LAST_INDEXED_COUNT, _VECTORIZER

    try:
        with _get_db_connection() as conn:
            row_count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            if row_count == _LAST_INDEXED_COUNT and _EMBEDDINGS_CACHE:
                return  # No new candidates

            rows = conn.execute("SELECT id, name, title, experience, skills, match_score, resume_text, is_shortlisted, prediction FROM candidates").fetchall()

        new_summaries = []
        new_candidates = []
        for r in rows:
            cid = r['id']
            if cid not in _EMBEDDINGS_CACHE:
                summary = _generate_candidate_summary(r)
                new_summaries.append(summary)
                new_candidates.append((cid, dict(r)))

        if new_summaries:
            vectorizer = _get_or_create_vectorizer()
            if len(_EMBEDDINGS_CACHE) == 0:
                # First time, fit on all
                all_summaries = new_summaries
                all_candidates = new_candidates
            else:
                # Incremental: refit on all (simple approach)
                all_summaries = []
                all_candidates = []
                for cid, cand_data in _EMBEDDINGS_CACHE.values():
                    all_summaries.append(_generate_candidate_summary(cand_data))
                    all_candidates.append((cid, cand_data))
                all_summaries.extend(new_summaries)
                all_candidates.extend(new_candidates)

            vectors = vectorizer.fit_transform(all_summaries).toarray()
            for i, (cid, cand_data) in enumerate(all_candidates):
                _EMBEDDINGS_CACHE[cid] = (cand_data, vectors[i])

        _LAST_INDEXED_COUNT = row_count
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
                        condition_parts.append(f"(LOWER(name) LIKE '%{kw}%' OR LOWER(title) LIKE '%{kw}%' OR LOWER(skills) LIKE '%{kw}%')")
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


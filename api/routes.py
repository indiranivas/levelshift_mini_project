import json
from datetime import datetime
from typing import Callable, Optional

from flask import jsonify, request, session


def handle_ai_summarize(get_candidate_texts: Callable, genai_helper) -> object:
    data = request.json or {}
    candidate_id = data.get("candidate_id", "")
    job_description = data.get("job_description", "")

    resume_text, _ = get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    result = genai_helper.summarize_resume(resume_text, job_description)
    return jsonify({"success": True, "result": result})


def handle_ai_interview_questions(get_candidate_texts: Callable, genai_helper) -> object:
    data = request.json or {}
    candidate_id = data.get("candidate_id", "")
    job_description = data.get("job_description", "")

    resume_text, _ = get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    result = genai_helper.generate_interview_questions(resume_text, job_description)
    return jsonify({"success": True, "result": result})


def handle_ai_feedback(get_candidate_texts: Callable, genai_helper) -> object:
    data = request.json or {}
    candidate_id = data.get("candidate_id", "")
    job_description = data.get("job_description", "")

    resume_text, _ = get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    result = genai_helper.generate_feedback(resume_text, job_description)
    return jsonify({"success": True, "result": result})


def handle_ai_chat(rag_engine, genai_helper) -> object:
    """Answer an HR policy question via the Gemini chatbot with enhanced RAG support."""
    data = request.json or {}
    question = data.get("question", "")
    context = data.get("context", "")

    if not question:
        return jsonify({"success": False, "error": "Question required"}), 400

    candidate_keywords = [
        "candidate",
        "candidates",
        "who",
        "which",
        "show me",
        "list",
        "find",
        "search",
        "filter",
        "skill",
        "experience",
    ]
    is_candidate_query = any(keyword in question.lower() for keyword in candidate_keywords)

    if is_candidate_query:
        try:
            db_schema = rag_engine.get_database_schema()
            interpretation_json = genai_helper.interpret_candidate_query(question, db_schema)

            try:
                import ast

                if isinstance(interpretation_json, str) and interpretation_json.startswith("{"):
                    query_params = ast.literal_eval(interpretation_json)
                else:
                    query_params = json.loads(interpretation_json)
            except Exception:
                query_params = {
                    "search_keywords": "",
                    "experience_min": 0,
                    "experience_max": 999,
                    "status_filter": "All",
                    "match_score_min": 0,
                    "limit": 10,
                }

            candidates = rag_engine.search_candidates_with_filters(
                keywords=query_params.get("search_keywords", ""),
                experience_min=int(query_params.get("experience_min", 0)),
                experience_max=int(query_params.get("experience_max", 999)),
                status_filter=query_params.get("status_filter", "All"),
                match_score_min=int(query_params.get("match_score_min", 0)),
                limit=int(query_params.get("limit", 10)),
            )

            if candidates:
                candidates_text = "CANDIDATES FOUND:\n\n"
                for idx, c in enumerate(candidates, 1):
                    shortlisted = "Yes" if c.get("is_shortlisted") else "No"
                    skills_str = ", ".join(c["skills"]) if isinstance(c.get("skills"), list) else str(c.get("skills"))
                    candidates_text += f"{idx}. {c.get('name')}\n"
                    candidates_text += f"   - Role: {c.get('title')}\n"
                    candidates_text += f"   - Experience: {c.get('experience')} years\n"
                    candidates_text += f"   - Match Score: {c.get('match_score')}%\n"
                    candidates_text += f"   - Status: {c.get('prediction')}\n"
                    candidates_text += f"   - Skills: {skills_str}\n"
                    candidates_text += f"   - Shortlisted: {shortlisted}\n\n"
            else:
                candidates_text = "No candidates found matching your criteria."

            result = genai_helper.format_candidate_data_response(question, candidates_text, db_schema)
            return jsonify({"success": True, "answer": result, "candidates_count": len(candidates)})
        except Exception as e:
            # Fallback to basic RAG if enhanced process fails
            print(f"Error in enhanced candidate query: {e}")

    try:
        relevant_candidates = rag_engine.search_relevant_candidates(question, top_k=3)
        db_context = "\n\n--- RELEVANT CANDIDATES FROM DATABASE ---\n"
        if not relevant_candidates:
            db_context += "No highly relevant candidates found for this query.\n"
        else:
            for r in relevant_candidates:
                shortlisted = "Yes" if r.get("is_shortlisted") else "No"
                skills_str = "None"
                if r.get("skills"):
                    try:
                        skills = json.loads(r["skills"]) if isinstance(r["skills"], str) else r["skills"]
                        skills_str = ", ".join(skills[:5]) if isinstance(skills, list) else str(skills)
                    except Exception:
                        pass

                db_context += (
                    f"- Name: {r.get('name')}, Role: {r.get('title')}, Exp: {r.get('experience')} yrs, "
                    f"Match Score: {r.get('match_score')}%, Status: {r.get('prediction')}, "
                    f"Shortlisted: {shortlisted}, Skills: {skills_str}\n"
                )

        context = str(context or "") + db_context
    except Exception as e:
        print(f"Error fetching RAG candidates for chat context: {e}")

    result = genai_helper.answer_hiring_question(question, context)
    return jsonify({"success": True, "answer": result})


def handle_get_all_candidates(get_db) -> object:
    db = get_db()
    search = request.args.get("search", "").strip()
    filter_pred = request.args.get("filter", "").strip()

    query = "SELECT * FROM candidates"
    params = []
    conditions = []

    if search:
        conditions.append("(name LIKE ? OR email LIKE ? OR title LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if filter_pred:
        conditions.append("prediction = ?")
        params.append(filter_pred)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY match_score DESC"

    rows = db.execute(query, params).fetchall()
    result = []
    for row in rows:
        c = dict(row)
        c["skills"] = json.loads(c["skills"]) if c["skills"] else []
        result.append(c)

    return jsonify({"success": True, "candidates": result, "total": len(result)})


def handle_dashboard_stats(get_db) -> object:
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    shortlisted = db.execute("SELECT COUNT(*) FROM candidates WHERE is_shortlisted = 1").fetchone()[0]
    pending = total - shortlisted

    recent_rows = db.execute("SELECT * FROM candidates ORDER BY timestamp DESC LIMIT 5").fetchall()
    formatted_candidates = []
    for row in recent_rows:
        formatted_candidates.append(
            {
                "id": row["id"],
                "name": row["name"],
                "title": row["title"],
                "experience": row["experience"],
                "score": row["match_score"],
                "prediction": row["prediction"],
            }
        )

    return jsonify(
        {
            "total": total,
            "shortlisted": shortlisted,
            "pending": pending,
            "candidates": formatted_candidates,
        }
    )


def handle_analyze(
    get_db,
    allowed_file: Callable,
    extract_text_from_file: Callable,
    extract_candidate_info: Callable,
    matching_engine,
    rf_model,
    standard_scaler,
    tfidf_vectorizer,
) -> object:
    db = get_db()

    try:
        job_description = request.form.get("job_description", "")
        if not job_description:
            return jsonify({"success": False, "error": "Job description required"}), 400

        if "files" not in request.files:
            return jsonify({"success": False, "error": "No files provided"}), 400

        files = request.files.getlist("files")
        resume_texts = []

        for file in files:
            if not allowed_file(file.filename):
                continue

            if (file.filename or "").lower().endswith(".csv"):
                try:
                    import pandas as pd

                    df = pd.read_csv(file)
                    for _, row in df.iterrows():
                        name_val = "Unknown"
                        email_val = "email@example.com"
                        text_parts = []

                        for col, val in row.items():
                            if pd.isna(val):
                                continue
                            col_lower = str(col).lower()
                            if "name" in col_lower and name_val == "Unknown":
                                name_val = str(val)
                            elif "email" in col_lower and email_val == "email@example.com":
                                email_val = str(val)
                            elif col_lower in ["resume_str", "resume", "text", "resume_html"]:
                                text_parts.append(str(val))
                            else:
                                text_parts.append(f"{col}: {val}")

                        constructed_text = f"{name_val}\n{email_val}\n\n" + "\n".join(text_parts)
                        if len(constructed_text.strip()) >= 50:
                            resume_texts.append(constructed_text)
                except Exception as e:
                    print(f"Error parsing CSV: {e}")
            else:
                text = extract_text_from_file(file)
                if text and len(text.strip()) >= 50:
                    resume_texts.append(text)

        analyzed_candidates = []

        for resume_text in resume_texts:
            candidate_info = extract_candidate_info(resume_text)

            match_score = matching_engine.score_candidate_percent(resume_text, job_description)

            prediction = "Unknown"
            if rf_model and standard_scaler and tfidf_vectorizer:
                try:
                    import scipy.sparse as sp
                    import pandas as pd

                    resume_length = len(resume_text)
                    word_count = len(resume_text.split())
                    skill_count = len(candidate_info.get("skills", []))
                    experience_years = candidate_info.get("experience", 0.0)

                    X_num = pd.DataFrame(
                        [[resume_length, word_count, skill_count, experience_years]],
                        columns=["resume_length", "word_count", "skill_count", "experience_years"],
                    )
                    X_scaled = standard_scaler.transform(X_num)
                    X_tfidf = tfidf_vectorizer.transform([resume_text])
                    X_comb = sp.hstack((X_scaled, X_tfidf))

                    pred = rf_model.predict(X_comb)[0]
                    prediction = "Shortlisted" if pred == 1 else "Rejected"
                except Exception as e:
                    print(f"Model prediction error: {e}")

            candidate_id = str(__import__("uuid").uuid4())

            db.execute(
                """
                INSERT INTO candidates (
                    id, name, email, experience, title, match_score,
                    prediction, resume_text, skills, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    candidate_info["name"],
                    candidate_info["email"],
                    candidate_info["experience"],
                    candidate_info["title"],
                    match_score,
                    prediction,
                    resume_text,
                    json.dumps(candidate_info["skills"]),
                    datetime.now().timestamp(),
                ),
            )

            analyzed_candidates.append(
                {
                    "id": candidate_id,
                    "name": candidate_info["name"],
                    "match_score": match_score,
                    "prediction": prediction,
                }
            )

        if not analyzed_candidates:
            return jsonify({"success": False, "error": "No valid resumes processed"}), 400

        db.commit()

        # Store latest analyzed candidate in session
        session["latest_candidate_id"] = analyzed_candidates[0]["id"]

        return jsonify(
            {
                "success": True,
                "candidates": analyzed_candidates,
                "message": f"Analyzed {len(analyzed_candidates)} candidate(s)",
            }
        )

    except Exception as e:
        print(f"Error in analyze_resumes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def handle_get_latest_candidate(get_db) -> object:
    db = get_db()
    row = db.execute("SELECT * FROM candidates ORDER BY timestamp DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"success": False, "error": "No candidates available"})

    latest = dict(row)
    latest["skills"] = json.loads(latest["skills"]) if latest["skills"] else []
    return jsonify({"success": True, "candidate": latest})


def handle_get_candidate(get_db, candidate_id: str) -> object:
    db = get_db()
    row = db.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    candidate = dict(row)
    candidate["skills"] = json.loads(candidate["skills"]) if candidate["skills"] else []
    return jsonify({"success": True, "candidate": candidate})


def handle_shortlist_candidate(get_db) -> object:
    db = get_db()
    try:
        data = request.json or {}
        candidate_id = data.get("candidate_id")
        if not candidate_id:
            return jsonify({"success": False, "error": "candidate_id required"}), 400

        row = db.execute("SELECT id FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if row:
            db.execute("UPDATE candidates SET is_shortlisted = 1 WHERE id = ?", (candidate_id,))
            db.commit()
            return jsonify({"success": True, "message": "Candidate shortlisted"})

        return jsonify({"success": False, "error": "Candidate not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def handle_health_check(get_db, rf_model) -> object:
    total_candidates = 0
    try:
        total_candidates = get_db().execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    except Exception:
        pass

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "models_loaded": rf_model is not None,
            "total_candidates": total_candidates,
        }
    )


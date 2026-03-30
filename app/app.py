import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import joblib
import pandas as pd
import numpy as np
import sqlite3
import uuid
from flask import g
import regex as re
# Add parent directory and app module path to path for imports
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
APP_PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_PATH)
sys.path.insert(0, APP_PATH)


# Import configuration
# Add parent directory and app module path to path for imports
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
APP_PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_PATH)
sys.path.insert(0, APP_PATH)

# Import configuration
from config import get_config

from data.data_processing import preprocess_data
from nlp.nlp_pipeline import NLPPipeline, extract_skills, extract_experience
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import genai_helper
import rag_engine

# Initialize Flask app with config
app = Flask(__name__, template_folder='templates')
app.config.from_object(get_config())

# Security: Add security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains' if app.config['SESSION_COOKIE_SECURE'] else ''
    return response

print(f"INFO: Flask app initialized with config: {app.config.get('ENV', 'production')}")
print(f"INFO: Debug mode: {app.debug}")

# Configuration
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']
app.config['MAX_CONTENT_LENGTH'] = app.config['MAX_CONTENT_LENGTH']

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"INFO: Upload folder configured: {UPLOAD_FOLDER}")

# Database Setup
DATABASE = app.config['DATABASE']
print(f"INFO: Database configured: {DATABASE}")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                experience REAL,
                title TEXT,
                match_score INTEGER,
                prediction TEXT,
                resume_text TEXT,
                skills TEXT,
                timestamp REAL,
                is_shortlisted INTEGER DEFAULT 0
            )
        ''')
        db.commit()

init_db()
    
# Load pre-trained models
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models')
ensemble_model = None
primary_model = None

try:
    ensemble_model = joblib.load(os.path.join(MODEL_PATH, 'ensemble_model.pkl'))
    primary_model = ensemble_model
    print("INFO: Ensemble model loaded successfully")
except Exception as e:
    print(f"WARNING: Could not load ensemble model: {e}")

if primary_model is None:
    try:
        primary_model = joblib.load(os.path.join(MODEL_PATH, 'logistic_regression_model.pkl'))
        print("INFO: Fallback: Logistic Regression model loaded successfully")
    except Exception as e:
        print(f"WARNING: Could not load logistic regression model: {e}")

try:
    tfidf_vectorizer = joblib.load(os.path.join(MODEL_PATH, 'tfidf_vectorizer.pkl'))
    print("INFO: TF-IDF vectorizer loaded successfully")
except Exception as e:
    print(f"WARNING: Could not load TF-IDF vectorizer: {e}")
    tfidf_vectorizer = None

try:
    standard_scaler = joblib.load(os.path.join(MODEL_PATH, 'standard_scaler.pkl'))
    print("INFO: Standard Scaler loaded successfully")
except Exception as e:
    print(f"WARNING: Could not load Standard Scaler: {e}")
    standard_scaler = None

rf_model = primary_model  # legacy variable name used in prediction path

# NLP Pipeline
nlp_pipeline = NLPPipeline()

def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    """Extract text content from uploaded file."""
    if file.filename.endswith('.txt'):
        return file.read().decode('utf-8', errors='ignore')
    elif file.filename.endswith('.csv'):
        return file.read().decode('utf-8', errors='ignore')
    elif file.filename.endswith('.pdf'):
        # Simple PDF text extraction (basic)
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except:
            return file.read().decode('utf-8', errors='ignore')
    return ""

def calculate_skill_overlap(resume_text, job_description):
    """Calculate simple keyword overlap between resume and job description."""
    try:
        resume_tokens = set(re.findall(r"\b\w+\b", resume_text.lower()))
        job_tokens = set(re.findall(r"\b\w+\b", job_description.lower()))
        if not resume_tokens or not job_tokens:
            return 0.0

        intersect = resume_tokens.intersection(job_tokens)
        score = len(intersect) / max(len(job_tokens), 1)
        return min(score, 1.0)
    except Exception:
        return 0.0


def calculate_match_score(resume_text, job_description, candidate_skills=None, candidate_experience=None):
    """Calculate weighted match score from TF-IDF cosine similarity, skill overlap, and model probability."""
    try:
        # TF-IDF similarity
        similarity = 0.0
        if tfidf_vectorizer is not None:
            vectors = tfidf_vectorizer.transform([resume_text, job_description])
            similarity = float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
        else:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            vectors = vectorizer.fit_transform([resume_text, job_description])
            similarity = float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])

        # Skill overlap
        overlap = calculate_skill_overlap(resume_text, job_description)

        # ML prediction probability
        model_prob = 0.0
        if rf_model is not None and standard_scaler is not None and tfidf_vectorizer is not None:
            try:
                import scipy.sparse as sp
                resume_length = len(resume_text)
                word_count = len(resume_text.split())
                skill_count = len(candidate_skills) if candidate_skills is not None else 0
                experience_years = candidate_experience if candidate_experience is not None else 0

                X_num = pd.DataFrame(
                    [[resume_length, word_count, skill_count, experience_years]],
                    columns=['resume_length', 'word_count', 'skill_count', 'experience_years']
                )
                X_scaled = standard_scaler.transform(X_num)
                X_tfidf = tfidf_vectorizer.transform([resume_text])
                X_comb = sp.hstack((X_scaled, X_tfidf))

                if hasattr(rf_model, 'predict_proba'):
                    model_prob = float(rf_model.predict_proba(X_comb)[0, 1])
                elif hasattr(rf_model, 'decision_function'):
                    decision_score = float(rf_model.decision_function(X_comb)[0])
                    model_prob = 1 / (1 + np.exp(-decision_score))
            except Exception as e:
                print(f"Model scoring error in calculate_match_score: {e}")

        # Experience multiplier (caps at 1.0 for 10+ years)
        experience_score = min(candidate_experience / 10.0, 1.0) if candidate_experience else 0.0

        # Weighted blend (tune weights as needed)
        combined = (0.45 * similarity) + (0.25 * overlap) + (0.25 * model_prob) + (0.05 * experience_score)
        combined_clamped = max(0.0, min(1.0, combined))
        return int(combined_clamped * 100)
    except Exception as e:
        print(f"Error calculating match score: {e}")
        return 50  # default fallback

def extract_candidate_info(resume_text):
    """Extract basic candidate information from resume text."""
    lines = resume_text.split('\n')
    
    # Extract name (usually first line)
    name = lines[0].strip() if lines else "Unknown"
    
    # Try to extract email
    email = "email@example.com"
    for line in lines:
        if '@' in line and '.' in line:
            email = line.strip()
            break
    
    # Extract experience using NLP
    experience = extract_experience(resume_text)
    
    # Extract skills
    skills = extract_skills(resume_text)
    
    # Try to extract title from first few lines
    title = "Professional"
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 3 and not '@' in line and not any(char.isdigit() for char in line):
            title = line
            break
    
    return {
        'name': name,
        'email': email,
        'experience': experience,
        'title': title,
        'skills': skills
    }

# Routes

@app.route('/')
def dashboard():
    """Dashboard page."""
    return render_template('dashboard.html')

@app.route('/upload')
def upload():
    """Resume upload page."""
    return render_template('upload.html')

@app.route('/analytics')
def analytics():
    """Analytics/Analysis results page."""
    return render_template('analytics.html')

@app.route('/candidates')
def candidates_list():
    """All candidates list view."""
    return render_template('candidates.html')

@app.route('/chatbot')
def chatbot():
    """HR Chatbot page."""
    return render_template('chatbot.html')

# API Endpoints

# ── GenAI Endpoints ──────────────────────────────────────────

def _get_candidate_texts(candidate_id):
    """Helper: return (resume_text, job_description) for a candidate."""
    row = get_db().execute('SELECT resume_text FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
    if not row:
        return None, ''
    return row['resume_text'] or '', ''

@app.route('/api/ai/summarize', methods=['POST'])
def ai_summarize():
    """Generate an AI summary for a candidate."""
    data = request.json or {}
    candidate_id = data.get('candidate_id', '')
    job_description = data.get('job_description', '')
    resume_text, _ = _get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    result = genai_helper.summarize_resume(resume_text, job_description)
    return jsonify({'success': True, 'result': result})

@app.route('/api/ai/interview-questions', methods=['POST'])
def ai_interview_questions():
    """Generate interview questions for a candidate."""
    data = request.json or {}
    candidate_id = data.get('candidate_id', '')
    job_description = data.get('job_description', '')
    resume_text, _ = _get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    result = genai_helper.generate_interview_questions(resume_text, job_description)
    return jsonify({'success': True, 'result': result})

@app.route('/api/ai/feedback', methods=['POST'])
def ai_feedback():
    """Generate structured recruiter feedback for a candidate."""
    data = request.json or {}
    candidate_id = data.get('candidate_id', '')
    job_description = data.get('job_description', '')
    resume_text, _ = _get_candidate_texts(candidate_id)
    if resume_text is None:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    result = genai_helper.generate_feedback(resume_text, job_description)
    return jsonify({'success': True, 'result': result})

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Answer an HR policy question via the Gemini chatbot with enhanced RAG support."""
    data = request.json or {}
    question = data.get('question', '')
    context = data.get('context', '')
    
    if not question:
        print("WARNING: Chat request received without question")
        return jsonify({'success': False, 'error': 'Question required'}), 400
    
    print(f"INFO: Processing chat question: {question[:100]}...")
    
    # Detect if user is asking about candidates
    candidate_keywords = ['candidate', 'candidates', 'who', 'which', 'show me', 'list', 'find', 'search', 'filter', 'skill', 'experience']
    is_candidate_query = any(keyword in question.lower() for keyword in candidate_keywords)
    
    if is_candidate_query:
        # Two-step process for candidate queries
        try:
            # Get database schema
            db_schema = rag_engine.get_database_schema()
            
            # Step 1: Use GenAI to interpret what candidate data is needed
            interpretation_json = genai_helper.interpret_candidate_query(question, db_schema)
            
            # Parse the JSON response
            try:
                import ast
                query_params = ast.literal_eval(interpretation_json) if interpretation_json.startswith('{') else json.loads(interpretation_json)
            except Exception as parse_error:
                print(f"Failed to parse GenAI interpretation: {parse_error}. Using defaults.")
                # Fallback to default params if parsing fails
                query_params = {
                    'search_keywords': '',
                    'experience_min': 0,
                    'experience_max': 999,
                    'status_filter': 'All',
                    'match_score_min': 0,
                    'limit': 10
                }
            
            # Step 2: Execute the query with interpreted filters
            candidates = rag_engine.search_candidates_with_filters(
                keywords=query_params.get('search_keywords', ''),
                experience_min=int(query_params.get('experience_min', 0)),
                experience_max=int(query_params.get('experience_max', 999)),
                status_filter=query_params.get('status_filter', 'All'),
                match_score_min=int(query_params.get('match_score_min', 0)),
                limit=int(query_params.get('limit', 10))
            )
            print(f"RAG search returned {len(candidates)} candidates")
            
            # Format candidate data for display
            if candidates:
                candidates_text = "CANDIDATES FOUND:\n\n"
                for idx, c in enumerate(candidates, 1):
                    shortlisted = "Yes" if c['is_shortlisted'] else "No"
                    skills_str = ", ".join(c['skills']) if isinstance(c['skills'], list) else str(c['skills'])
                    candidates_text += f"{idx}. {c['name']}\n"
                    candidates_text += f"   - Role: {c['title']}\n"
                    candidates_text += f"   - Experience: {c['experience']} years\n"
                    candidates_text += f"   - Match Score: {c['match_score']}%\n"
                    candidates_text += f"   - Status: {c['prediction']}\n"
                    candidates_text += f"   - Skills: {skills_str}\n"
                    candidates_text += f"   - Shortlisted: {shortlisted}\n\n"
            else:
                candidates_text = "No candidates found matching your criteria."
            
            # Step 3: Use GenAI to format a comprehensive response
            result = genai_helper.format_candidate_data_response(question, candidates_text, db_schema)
            print(f"Successfully processed candidate query")
            return jsonify({'success': True, 'answer': result, 'candidates_count': len(candidates)})
            
        except Exception as e:
            print(f"Error in enhanced candidate query: {e}", exc_info=True)
            # Fallback to basic RAG if enhanced process fails
            pass
    
    # Default flow: Basic RAG + GenAI for non-candidate queries or fallback
    try:
        relevant_candidates = rag_engine.search_relevant_candidates(question, top_k=3)
        
        db_context = "\n\n--- RELEVANT CANDIDATES FROM DATABASE ---\n"
        if not relevant_candidates:
            db_context += "No highly relevant candidates found for this query.\n"
        else:
            for r in relevant_candidates:
                shortlisted = "Yes" if r['is_shortlisted'] else "No"
                skills_str = "None"
                if r['skills']:
                    try:
                        skills = json.loads(r['skills'])
                        skills_str = ", ".join(skills[:5]) if isinstance(skills, list) else str(skills)
                    except json.JSONDecodeError:
                        pass
                
                db_context += f"- Name: {r['name']}, Role: {r['title']}, Exp: {r['experience']} yrs, Match Score: {r['match_score']}%, Status: {r['prediction']}, Shortlisted: {shortlisted}, Skills: {skills_str}\n"
        
        context = context + db_context
    except Exception as e:
        print(f"Error fetching RAG candidates for chat context: {e}")
        # Continue without DB context if it fails so the chat still works

    result = genai_helper.answer_hiring_question(question, context)
    return jsonify({'success': True, 'answer': result})

@app.route('/api/candidates', methods=['GET'])
def get_all_candidates():
    """Get all candidates, sorted by match score."""
    db = get_db()
    search = request.args.get('search', '').strip()
    filter_pred = request.args.get('filter', '').strip()  # 'Shortlisted' or 'Rejected'
    
    query = 'SELECT * FROM candidates'
    params = []
    conditions = []
    
    if search:
        conditions.append('(name LIKE ? OR email LIKE ? OR title LIKE ?)')
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if filter_pred:
        conditions.append('prediction = ?')
        params.append(filter_pred)
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY match_score DESC'
    
    rows = db.execute(query, params).fetchall()
    result = []
    for row in rows:
        c = dict(row)
        c['skills'] = json.loads(c['skills']) if c['skills'] else []
        result.append(c)
    
    return jsonify({'success': True, 'candidates': result, 'total': len(result)})

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics."""
    db = get_db()
    
    total = db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    shortlisted = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Shortlisted"').fetchone()[0]
    pending = total - shortlisted
    
    # Get recent candidates
    recent_rows = db.execute('SELECT * FROM candidates ORDER BY timestamp DESC LIMIT 5').fetchall()
    
    formatted_candidates = []
    for row in recent_rows:
        formatted_candidates.append({
            'id': row['id'],
            'name': row['name'],
            'title': row['title'],
            'experience': row['experience'],
            'score': row['match_score'],
            'prediction': row['prediction']
        })
    
    return jsonify({
        'total': total,
        'shortlisted': shortlisted,
        'pending': pending,
        'candidates': formatted_candidates
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_resumes():
    """Analyze uploaded resumes."""
    db = get_db()
    
    try:
        # Get job description
        job_description = request.form.get('job_description', '')
        
        if not job_description:
            return jsonify({'success': False, 'error': 'Job description required'}), 400
        
        # Process uploaded files
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        # Collect all texts to process
        resume_texts = []
        
        for file in files:
            if not allowed_file(file.filename):
                continue
                
            if file.filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file)
                    for _, row in df.iterrows():
                        name_val = "Unknown"
                        email_val = "email@example.com"
                        text_parts = []
                        
                        for col, val in row.items():
                            if pd.isna(val): continue
                            col_lower = str(col).lower()
                            if 'name' in col_lower and name_val == "Unknown":
                                name_val = str(val)
                            elif 'email' in col_lower and email_val == "email@example.com":
                                email_val = str(val)
                            elif col_lower in ['resume_str', 'resume', 'text', 'resume_html']:
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
            # Extract candidate info
            candidate_info = extract_candidate_info(resume_text)
            
            # Calculate match score (weighted ensemble + TF-IDF + overlap + experience)
            match_score = calculate_match_score(
                resume_text,
                job_description,
                candidate_skills=candidate_info.get('skills', []),
                candidate_experience=candidate_info.get('experience', 0)
            )
            
            # Apply NLP processing
            nlp_features = nlp_pipeline.process_resume_text(resume_text)
            
            # Predict Shortlist/Reject if model is loaded
            prediction = "Unknown"
            if rf_model and standard_scaler and tfidf_vectorizer:
                try:
                    import scipy.sparse as sp
                    resume_length = len(resume_text)
                    word_count = len(resume_text.split())
                    skill_count = len(candidate_info['skills'])
                    experience_years = candidate_info['experience']
                    
                    X_num = pd.DataFrame(
                        [[resume_length, word_count, skill_count, experience_years]], 
                        columns=['resume_length', 'word_count', 'skill_count', 'experience_years']
                    )
                    X_scaled = standard_scaler.transform(X_num)
                    X_tfidf = tfidf_vectorizer.transform([resume_text])
                    X_comb = sp.hstack((X_scaled, X_tfidf))
                    
                    pred = rf_model.predict(X_comb)[0]
                    prediction = "Shortlisted" if pred == 1 else "Rejected"
                except Exception as e:
                    print(f"Model prediction error: {e}")
                    
            # Store candidate
            candidate_id = str(uuid.uuid4())
            
            db.execute('''
                INSERT INTO candidates (
                    id, name, email, experience, title, match_score, 
                    prediction, resume_text, skills, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_id, candidate_info['name'], candidate_info['email'],
                candidate_info['experience'], candidate_info['title'],
                match_score, prediction, resume_text,
                json.dumps(candidate_info['skills']), datetime.now().timestamp()
            ))
            db.commit()
            
            analyzed_candidates.append({
                'id': candidate_id,
                'name': candidate_info['name'],
                'match_score': match_score,
                'prediction': prediction
            })
        
        if not analyzed_candidates:
            return jsonify({'success': False, 'error': 'No valid resumes processed'}), 400
        
        # Store latest analyzed candidate in session
        session['latest_candidate_id'] = analyzed_candidates[0]['id']
        
        return jsonify({
            'success': True,
            'candidates': analyzed_candidates,
            'message': f'Analyzed {len(analyzed_candidates)} candidate(s)'
        })
    
    except Exception as e:
        print(f"Error in analyze_resumes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/candidate/<candidate_id>')
def candidate_analytics(candidate_id):
    """Individual candidate analytics page."""
    db = get_db()
    
    row = db.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
    
    if not row:
        return "Candidate not found", 404
    
    candidate = dict(row)
    candidate['skills'] = json.loads(candidate['skills']) if candidate['skills'] else []
    
    return render_template('analytics.html', candidate=candidate)

@app.route('/api/latest-candidate', methods=['GET'])
def get_latest_candidate():
    """Get the latest analyzed candidate."""
    db = get_db()
    row = db.execute('SELECT * FROM candidates ORDER BY timestamp DESC LIMIT 1').fetchone()
    
    if not row:
        return jsonify({'success': False, 'error': 'No candidates available'})
    
    latest = dict(row)
    latest['skills'] = json.loads(latest['skills']) if latest['skills'] else []
    
    return jsonify({
        'success': True,
        'candidate': latest
    })

@app.route('/api/candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get a specific candidate by ID."""
    db = get_db()
    row = db.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()

    if not row:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    candidate = dict(row)
    candidate['skills'] = json.loads(candidate['skills']) if candidate['skills'] else []

    return jsonify({
        'success': True,
        'candidate': candidate
    })

@app.route('/api/shortlist', methods=['POST'])
def shortlist_candidate():
    """Shortlist a candidate."""
    db = get_db()
    
    try:
        data = request.json
        candidate_id = data.get('candidate_id')
        
        row = db.execute('SELECT id FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
        
        if row:
            db.execute('UPDATE candidates SET is_shortlisted = 1 WHERE id = ?', (candidate_id,))
            db.commit()
            return jsonify({'success': True, 'message': 'Candidate shortlisted'})
        
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    total_candidates = 0
    try:
        total_candidates = get_db().execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    except:
        pass
        
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'models_loaded': rf_model is not None,
        'total_candidates': total_candidates
    })

# ── Analytics Endpoints ──────────────────────────────────────────

@app.route('/api/analytics/match-score-distribution', methods=['GET'])
def analytics_match_score_distribution():
    """Get match score distribution for visualization."""
    db = get_db()
    rows = db.execute('SELECT match_score FROM candidates WHERE match_score IS NOT NULL').fetchall()
    
    # Bin into ranges: 0-20, 20-40, 40-60, 60-80, 80-100
    bins = {'0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0}
    for row in rows:
        score = row['match_score']
        if score < 20: bins['0-20'] += 1
        elif score < 40: bins['20-40'] += 1
        elif score < 60: bins['40-60'] += 1
        elif score < 80: bins['60-80'] += 1
        else: bins['80-100'] += 1
    
    return jsonify({
        'labels': list(bins.keys()),
        'data': list(bins.values()),
        'total': sum(bins.values())
    })

@app.route('/api/analytics/prediction-breakdown', methods=['GET'])
def analytics_prediction_breakdown():
    """Get prediction breakdown (Shortlisted vs Rejected vs Pending)."""
    db = get_db()
    shortlisted = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Shortlisted"').fetchone()[0]
    rejected = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Rejected"').fetchone()[0]
    pending = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction IS NULL OR prediction = ""').fetchone()[0]
    
    return jsonify({
        'labels': ['Shortlisted', 'Rejected', 'Pending Review'],
        'data': [shortlisted, rejected, pending],
        'backgroundColor': ['#10b981', '#ef4444', '#f59e0b'],
        'total': shortlisted + rejected + pending
    })

@app.route('/api/analytics/experience-distribution', methods=['GET'])
def analytics_experience_distribution():
    """Get experience level distribution."""
    db = get_db()
    rows = db.execute('SELECT experience FROM candidates WHERE experience IS NOT NULL').fetchall()
    
    # Bin by experience: 0-2, 2-5, 5-10, 10+
    bins = {'0-2 yrs': 0, '2-5 yrs': 0, '5-10 yrs': 0, '10+ yrs': 0}
    for row in rows:
        exp = row['experience']
        if exp < 2: bins['0-2 yrs'] += 1
        elif exp < 5: bins['2-5 yrs'] += 1
        elif exp < 10: bins['5-10 yrs'] += 1
        else: bins['10+ yrs'] += 1
    
    return jsonify({
        'labels': list(bins.keys()),
        'data': list(bins.values()),
        'total': sum(bins.values())
    })

@app.route('/api/analytics/top-skills', methods=['GET'])
def analytics_top_skills():
    """Get top 10 most common skills in applicant pool."""
    db = get_db()
    rows = db.execute('SELECT skills FROM candidates WHERE skills IS NOT NULL').fetchall()
    
    skill_count = {}
    for row in rows:
        try:
            skills = json.loads(row['skills']) if row['skills'] else []
            for skill in skills:
                skill_count[skill] = skill_count.get(skill, 0) + 1
        except:
            pass
    
    # Sort and get top 10
    sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [s[0] for s in sorted_skills]
    data = [s[1] for s in sorted_skills]
    
    return jsonify({
        'labels': labels,
        'data': data,
        'total': sum(data) if data else 0
    })

@app.route('/api/analytics/application-timeline', methods=['GET'])
def analytics_application_timeline():
    """Get application submissions over time (last 7 days)."""
    db = get_db()
    import time
    from datetime import datetime, timedelta
    
    # Get data from last 7 days
    seven_days_ago = time.time() - (7 * 24 * 60 * 60)
    rows = db.execute(
        'SELECT timestamp FROM candidates WHERE timestamp > ? ORDER BY timestamp ASC',
        (seven_days_ago,)
    ).fetchall()
    
    # Group by date
    date_counts = {}
    for row in rows:
        dt = datetime.fromtimestamp(row['timestamp'])
        date_str = dt.strftime('%Y-%m-%d')
        date_counts[date_str] = date_counts.get(date_str, 0) + 1
    
    # Ensure all dates in range are present
    labels = []
    data = []
    current = datetime.now() - timedelta(days=6)
    for _ in range(7):
        date_str = current.strftime('%Y-%m-%d')
        labels.append(date_str)
        data.append(date_counts.get(date_str, 0))
        current += timedelta(days=1)
    
    return jsonify({
        'labels': labels,
        'data': data,
        'total': sum(data)
    })

@app.route('/api/analytics/quality-metrics', methods=['GET'])
def analytics_quality_metrics():
    """Get quality metrics: avg score by prediction, conversion rates, etc."""
    db = get_db()
    
    total = db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    shortlisted = db.execute('SELECT COUNT(*) FROM candidates WHERE is_shortlisted = 1').fetchone()[0]
    rejected = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Rejected"').fetchone()[0]
    
    avg_match_all = db.execute('SELECT AVG(match_score) FROM candidates').fetchone()[0] or 0
    avg_match_shortlisted = db.execute('SELECT AVG(match_score) FROM candidates WHERE is_shortlisted = 1').fetchone()[0] or 0
    avg_exp = db.execute('SELECT AVG(experience) FROM candidates').fetchone()[0] or 0
    
    conversion_rate = (shortlisted / total * 100) if total > 0 else 0
    rejection_rate = (rejected / total * 100) if total > 0 else 0
    
    return jsonify({
        'total_candidates': total,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'avg_match_score': round(avg_match_all, 2),
        'avg_match_shortlisted': round(avg_match_shortlisted, 2),
        'avg_experience_years': round(avg_exp, 2),
        'conversion_rate': round(conversion_rate, 2),
        'rejection_rate': round(rejection_rate, 2),
        'pending': total - shortlisted - rejected
    })

@app.route('/api/analytics/hiring-funnel', methods=['GET'])
def analytics_hiring_funnel():
    """Get hiring funnel: Applications → Shortlisted → Selected."""
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    shortlisted = db.execute('SELECT COUNT(*) FROM candidates WHERE is_shortlisted = 1').fetchone()[0]
    selected = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Shortlisted"').fetchone()[0]
    
    return jsonify({
        'stages': ['Applications', 'Shortlisted', 'Selected'],
        'values': [total, shortlisted, selected],
        'percentages': [
            100,
            round((shortlisted / total * 100), 1) if total > 0 else 0,
            round((selected / total * 100), 1) if total > 0 else 0
        ]
    })

@app.route('/api/analytics/score-by-title', methods=['GET'])
def analytics_score_by_title():
    """Get average match score grouped by job title."""
    db = get_db()
    rows = db.execute('''
        SELECT title, AVG(match_score) as avg_score, COUNT(*) as count 
        FROM candidates 
        WHERE title IS NOT NULL 
        GROUP BY title 
        ORDER BY avg_score DESC 
        LIMIT 10
    ''').fetchall()
    
    return jsonify({
        'labels': [row['title'] for row in rows],
        'scores': [round(row['avg_score'], 1) for row in rows],
        'counts': [row['count'] for row in rows]
    })

@app.route('/api/analytics/score-range-breakdown', methods=['GET'])
def analytics_score_range_breakdown():
    """Get candidate count in different score ranges with percentages."""
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    
    ranges = [
        ('90-100', 90, 100),
        ('80-89', 80, 89),
        ('70-79', 70, 79),
        ('60-69', 60, 69),
        ('Below 60', 0, 59)
    ]
    
    data = []
    for label, min_score, max_score in ranges:
        count = db.execute(
            f'SELECT COUNT(*) FROM candidates WHERE match_score >= {min_score} AND match_score <= {max_score}'
        ).fetchone()[0]
        percentage = (count / total * 100) if total > 0 else 0
        data.append({'label': label, 'count': count, 'percentage': round(percentage, 1)})
    
    return jsonify({'data': data, 'total': total})

@app.route('/api/analytics/experience-salary-correlation', methods=['GET'])
def analytics_experience_salary_correlation():
    """Get experience level vs match score correlation."""
    db = get_db()
    rows = db.execute('SELECT experience, match_score FROM candidates WHERE experience IS NOT NULL AND match_score IS NOT NULL').fetchall()
    
    # Group by experience level
    experience_groups = {'0-2': [], '2-5': [], '5-10': [], '10+': []}
    for row in rows:
        exp = row['experience']
        score = row['match_score']
        if exp < 2: experience_groups['0-2'].append(score)
        elif exp < 5: experience_groups['2-5'].append(score)
        elif exp < 10: experience_groups['5-10'].append(score)
        else: experience_groups['10+'].append(score)
    
    return jsonify({
        'labels': list(experience_groups.keys()),
        'avg_scores': [
            round(sum(scores) / len(scores), 1) if scores else 0 
            for scores in experience_groups.values()
        ],
        'candidate_counts': [len(scores) for scores in experience_groups.values()]
    })

@app.route('/api/analytics/rejection-reasons', methods=['GET'])
def analytics_rejection_reasons():
    """Get most common rejection patterns based on score ranges."""
    db = get_db()
    rejected = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Rejected"').fetchone()[0]
    
    low_score_rejected = db.execute('SELECT COUNT(*) FROM candidates WHERE prediction = "Rejected" AND match_score < 50').fetchone()[0]
    exp_mismatch = db.execute('SELECT COUNT(*) FROM candidates WHERE is_shortlisted = 0 AND experience < 1').fetchone()[0]
    
    return jsonify({
        'total_rejected': rejected,
        'low_score': low_score_rejected,
        'experience_gap': exp_mismatch,
        'other': max(0, rejected - low_score_rejected - exp_mismatch)
    })

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Starting AI Smart Hiring Platform...")
    print(f"Environment: {app.config.get('ENV', 'production')}")
    print(f"Debug mode: {app.debug}")
    print(f"Database: {DATABASE}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Models loaded: Ensemble={ensemble_model is not None}, TF-IDF={tfidf_vectorizer is not None}, Scaler={standard_scaler is not None}")
    print("=" * 60)
    
    # Use debug from config, not hardcoded
    app.run(debug=app.debug, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

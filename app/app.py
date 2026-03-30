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

from nlp.skill_extractor import SkillExtractor
from nlp.experience_extractor import extract_experience_years
from model.matching_engine import MatchingEngine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import genai_helper
import rag_engine
from api import routes as api_routes

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

# Skill extraction + hybrid matching engine (deterministic)
skills_extractor = SkillExtractor()
matching_engine = MatchingEngine(tfidf_vectorizer=tfidf_vectorizer, skill_extractor=skills_extractor)

def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    """Extract text content from uploaded file."""
    filename = (file.filename or "").lower()
    if filename.endswith('.txt'):
        return file.read().decode('utf-8', errors='ignore')
    elif filename.endswith('.csv'):
        return file.read().decode('utf-8', errors='ignore')
    elif filename.endswith('.pdf'):
        # Simple PDF text extraction (basic)
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
            return text
        except Exception:
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
    
    # Extract experience + skills using the production extractors
    experience_years, _conf = extract_experience_years(resume_text)
    experience = float(experience_years) if experience_years is not None else 0.0

    skills = skills_extractor.extract_skills(resume_text)
    
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
    return api_routes.handle_ai_summarize(_get_candidate_texts, genai_helper)

@app.route('/api/ai/interview-questions', methods=['POST'])
def ai_interview_questions():
    """Generate interview questions for a candidate."""
    return api_routes.handle_ai_interview_questions(_get_candidate_texts, genai_helper)

@app.route('/api/ai/feedback', methods=['POST'])
def ai_feedback():
    """Generate structured recruiter feedback for a candidate."""
    return api_routes.handle_ai_feedback(_get_candidate_texts, genai_helper)

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Answer an HR policy question via the Gemini chatbot with enhanced RAG support."""
    return api_routes.handle_ai_chat(rag_engine, genai_helper)

@app.route('/api/candidates', methods=['GET'])
def get_all_candidates():
    """Get all candidates, sorted by match score."""
    return api_routes.handle_get_all_candidates(get_db)

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics."""
    return api_routes.handle_dashboard_stats(get_db)

@app.route('/api/analyze', methods=['POST'])
def analyze_resumes():
    """Analyze uploaded resumes."""
    return api_routes.handle_analyze(
        get_db=get_db,
        allowed_file=allowed_file,
        extract_text_from_file=extract_text_from_file,
        extract_candidate_info=extract_candidate_info,
        matching_engine=matching_engine,
        rf_model=rf_model,
        standard_scaler=standard_scaler,
        tfidf_vectorizer=tfidf_vectorizer,
    )

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
    return api_routes.handle_get_latest_candidate(get_db)

@app.route('/api/candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get a specific candidate by ID."""
    return api_routes.handle_get_candidate(get_db, candidate_id)

@app.route('/api/shortlist', methods=['POST'])
def shortlist_candidate():
    """Shortlist a candidate."""
    return api_routes.handle_shortlist_candidate(get_db)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return api_routes.handle_health_check(get_db, rf_model)

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

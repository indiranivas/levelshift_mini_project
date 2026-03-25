# 🏗️ Architecture & Development Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB INTERFACE (Flask)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Dashboard   │  │ Upload Page  │  │ Analytics    │       │
│  │   (/api)     │  │  (/upload)   │  │  (/analytics)│       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND SERVICES                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ app/app.py - Flask Application & API Endpoints      │    │
│  │  - Route handling (dashboard, upload, analytics)    │    │
│  │  - File upload processing                           │    │
│  │  - API endpoint management                          │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING PIPELINE                          │
│                                                               │
│  Resume File                                                  │
│     ↓                                                         │
│  ┌─────────────────────────┐                                 │
│  │ Text Extraction         │  (Extract raw text from PDF/TXT)│
│  └─────────────────────────┘                                 │
│     ↓                                                         │
│  ┌─────────────────────────┐                                 │
│  │ NLP Pipeline            │  (nlp/nlp_pipeline.py)         │
│  │  - Tokenization         │                                 │
│  │  - Stopword removal     │                                 │
│  │  - Lemmatization        │                                 │
│  │  - TF-IDF vectorization │                                 │
│  │  - N-gram extraction    │                                 │
│  └─────────────────────────┘                                 │
│     ↓                                                         │
│  ┌─────────────────────────┐                                 │
│  │ Feature Engineering     │  (data/data_processing.py)     │
│  │  - Skill extraction     │                                 │
│  │  - Experience detection │                                 │
│  │  - Candidate info parse │                                 │
│  └─────────────────────────┘                                 │
│     ↓                                                         │
│  ┌─────────────────────────┐                                 │
│  │ Match Scoring           │  (Similarity calculation)       │
│  │  - TF-IDF similarity    │                                 │
│  │  - Cosine distance      │                                 │
│  │  - Score normalization  │                                 │
│  └─────────────────────────┘                                 │
│     ↓                                                         │
│  ┌─────────────────────────┐                                 │
│  │ Results Storage         │  (In-memory or database)       │
│  │  - Candidate profile    │                                 │
│  │  - Match scores         │                                 │
│  │  - Extracted data       │                                 │
│  └─────────────────────────┘                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  ML INFERENCE (Optional)                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Pre-trained Models (models/*.pkl)                   │    │
│  │  - Random Forest (BEST: 98% accuracy)              │    │
│  │  - Decision Tree (100% on validation)              │    │
│  │  - Logistic Regression (ROC-AUC: 0.76)            │    │
│  │  - SVM                                              │    │
│  │                                                    │    │
│  │ Predictions:                                       │    │
│  │  - Shortlist probability                           │    │
│  │  - Confidence score                                │    │
│  │  - Risk assessment                                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Upload & Analysis Flow

```
User Uploads Resume + Job Description
         ↓
Flask receives multipart/form-data
         ↓
Extract text from file (PDF/TXT)
         ↓
Parse candidate info (name, email, experience)
         ↓
Apply NLP pipeline:
  - Tokenize & clean text
  - Remove stopwords
  - Lemmatize
  - Generate TF-IDF vectors
         ↓
Calculate match score:
  - Vectorize resume & job description
  - Compute cosine similarity
  - Convert to percentage (0-100%)
         ↓
Extract skills from tokens
         ↓
Create candidate profile:
  {
    "id": "unique_id",
    "name": "Extracted Name",
    "email": "Extracted Email",
    "experience": "Years detected",
    "match_score": "0-100 score",
    "skills": ["List", "of", "skills"],
    "resume_text": "First 500 chars...",
    "timestamp": "Analysis time"
  }
         ↓
Store in candidates_db
         ↓
Return results as JSON
         ↓
Frontend displays on Analytics page
```

## Module Dependencies

```
app.py
  ├── data.data_processing
  │   ├── pandas
  │   ├── numpy
  │   ├── scikit-learn
  │   └── sklearn.preprocessing
  │
  ├── nlp.nlp_pipeline
  │   ├── spacy
  │   ├── nltk
  │   ├── scikit-learn
  │   └── sklearn.feature_extraction.text
  │
  ├── joblib (model loading)
  │
  └── Flask
      ├── render_template
      ├── request
      ├── jsonify
      └── session
```

## How Each Component Works

### 1. Flask App (app/app.py)

**Purpose**: Web server and API endpoints

```python
@app.route('/')
def dashboard():
    """Homepage with candidate stats"""
    return render_template('dashboard.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_resumes():
    """Main analysis endpoint"""
    # 1. Receive files + job description
    # 2. Extract text from files
    # 3. Process with NLP pipeline
    # 4. Calculate match score
    # 5. Store candidate
    # 6. Return JSON response
```

**Key Functions**:
- `allowed_file()` - File validation
- `extract_text_from_file()` - PDF/TXT/CSV parsing
- `calculate_match_score()` - TF-IDF similarity
- `extract_candidate_info()` - Info extraction

### 2. NLP Pipeline (nlp/nlp_pipeline.py)

**Purpose**: Text preprocessing and vectorization

```
Raw Text
  ↓
Preprocessing (lowercase, special char removal)
  ↓
Tokenization (spaCy NLP)
  ↓
Stopword Removal (NLTK)
  ↓
Lemmatization (spaCy)
  ↓
TF-IDF Vectorization (scikit-learn)
  ↓
N-gram Extraction
  ↓
Structured Features
```

**Key Methods**:
- `preprocess_text()` - Clean text
- `tokenize_and_clean()` - Token extraction
- `extract_ngrams()` - Bigrams/trigrams
- `fit_tfidf()` - Vectorizer training
- `get_tfidf_features()` - Feature generation

### 3. Data Processing (data/data_processing.py)

**Purpose**: Dataset loading and feature extraction

```
CSV File (Resume.csv)
  ↓
Load with Pandas
  ↓
Handle missing values
  ↓
Remove duplicates
  ↓
Extract features:
  - Resume length
  - Word count
  ↓
Encode categories
  ↓
Scale numerical features
  ↓
Return cleaned data
```

**Key Functions**:
- `load_resume_data()` - CSV loading
- `handle_missing_values()` - Data cleaning
- `remove_duplicates()` - Deduplication
- `extract_basic_features()` - Feature extraction
- `encode_categorical_features()` - Category encoding

### 4. ML Models (models/train_model.py)

**Purpose**: Train classification models

```
Processed Data
  ↓
Create binary target (Shortlist/Reject)
  ↓
Split train/test (80/20)
  ↓
For each model:
  ├── Perform 5-fold cross-validation
  ├── Hyperparameter tuning (GridSearchCV)
  ├── Train on full training set
  ├── Evaluate on test set
  ├── Calculate metrics (Accuracy, F1, ROC-AUC)
  └── Save model to .pkl file
  ↓
Results & Model Files
```

**Models Trained**:
- Logistic Regression
- Decision Tree
- Random Forest (BEST)
- SVM

## API Reference

### Endpoints

#### GET /
**Dashboard homepage**
- Response: HTML page
- Status: 200 OK

#### GET /upload
**Resume upload page**
- Response: HTML page
- Status: 200 OK

#### GET /analytics
**Candidate analysis results page**
- Response: HTML page
- Status: 200 OK

#### POST /api/analyze
**Analyze resumes**
- Request:
  ```
  multipart/form-data:
    - files: File[] (multiple resume files)
    - job_description: string
  ```
- Response:
  ```json
  {
    "success": true,
    "candidates": [
      {
        "id": "0",
        "name": "John Doe",
        "match_score": 85
      }
    ],
    "message": "Analyzed 1 candidate(s)"
  }
  ```
- Status: 200 OK or 400/500 error

#### GET /api/dashboard-stats
**Get dashboard statistics**
- Response:
  ```json
  {
    "total": 5,
    "shortlisted": 3,
    "pending": 2,
    "candidates": [...]
  }
  ```
- Status: 200 OK

#### GET /api/candidate/<id>
**Get specific candidate**
- Parameter: id (candidate ID)
- Response:
  ```json
  {
    "success": true,
    "candidate": {...}
  }
  ```
- Status: 200 OK or 404 Not Found

#### GET /api/latest-candidate
**Get latest analyzed candidate**
- Response:
  ```json
  {
    "success": true,
    "candidate": {...}
  }
  ```
- Status: 200 OK

#### POST /api/shortlist
**Shortlist a candidate**
- Request: `{candidate_id: "id"}`
- Response: `{success: true, message: "..."}`
- Status: 200 OK or 404 error

#### GET /api/health
**Health check**
- Response:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-03-25T...",
    "models_loaded": true,
    "total_candidates": 5
  }
  ```
- Status: 200 OK

## Configuration

### app/app.py

```python
# Secret key for sessions (change in production)
app.secret_key = 'your-secret-key-here'

# Upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'csv'}

# Max file size: 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
```

### NLP Settings (nlp/nlp_pipeline.py)

```python
# TF-IDF Configuration
TfidfVectorizer(
    max_features=1000,      # Max features to extract
    ngram_range=(1, 2),     # Unigrams and bigrams
    stop_words='english'    # Remove English stopwords
)
```

### ML Model Settings (models/train_model.py)

```python
# Train-test split
test_size=0.2, random_state=42, stratify=y

# Cross-validation
cv=5  # 5-fold cross-validation

# GridSearchCV parameters
param_grids = {
    'Random Forest': {
        'n_estimators': [50, 100, 200],
        'max_depth': [5, 10, None]
    }
}
```

## Extensions & Improvements

### Possible Enhancements

1. **Database Integration**
   ```python
   # Replace in-memory candidates_db with:
   from flask_sqlalchemy import SQLAlchemy
   db.session.add(Candidate(...))
   db.session.commit()
   ```

2. **Authentication**
   ```python
   from flask_login import login_required
   @app.route('/api/shortlist', methods=['POST'])
   @login_required
   def shortlist_candidate():
       ...
   ```

3. **Advanced Matching**
   - Use embedding models (BERT, Word2Vec)
   - Implement fuzzy matching for typos
   - Add semantic similarity

4. **LLM Integration**
   - Interview question generation
   - Resume summarization
   - Skill inference

5. **Analytics**
   - Candidate distribution charts
   - Hiring funnel visualization
   - Time-to-hire metrics

## Testing

Run the test suite:
```bash
python test_api.py
```

Tests verify:
- Web pages load correctly
- API endpoints respond
- File upload works
- Match scoring functions
- Error handling

## Deployment

### Production Checklist

- [ ] Change `app.secret_key`
- [ ] Set `debug=False`
- [ ] Use production WSGI server (Gunicorn, uWSGI)
- [ ] Add database (PostgreSQL/MongoDB)
- [ ] Implement authentication
- [ ] Add HTTPS/SSL
- [ ] Set up logging
- [ ] Configure environment variables
- [ ] Add rate limiting
- [ ] Implement backup strategy

### Production Run (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app.app:app
```

## Troubleshooting Guide

| Error | Solution |
|-------|----------|
| Port 5000 in use | Use different port: `app.run(port=5001)` |
| spaCy model not found | `python -m spacy download en_core_web_sm` |
| Module not found | `pip install -r requirements.txt` |
| File upload fails | Check `UPLOAD_FOLDER` permissions |
| Slow analysis | Consider caching TF-IDF vectorizer |
| Database errors | Ensure database is running and accessible |

---

**For more information, see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)**
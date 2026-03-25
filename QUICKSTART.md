# 🚀 Quick Start Guide - AI Smart Hiring Platform

## What's Inside?

You now have a **complete, fully functional AI-powered hiring platform** with:

✅ **Machine Learning Models** - Trained on 2,482 resumes  
✅ **NLP Pipeline** - Advanced text processing with TF-IDF, tokenization, lemmatization  
✅ **Flask Web Application** - Beautiful, modern UI with Tailwind CSS  
✅ **REST API** - Endpoints for resume analysis, matching, and scoring  
✅ **Candidate Matching** - Intelligent similarity matching with job descriptions  

## File Structure

```
mini_project/
├── app/app.py                    ← Main Flask application (START HERE)
├── data/data_processing.py      ← Data preprocessing module
├── nlp/nlp_pipeline.py          ← NLP & text processing
├── models/train_model.py        ← ML model training
├── requirements.txt             ← Python dependencies
└── README.md                    ← Full documentation
```

## ⚡ Running the Application

### 1. Start the Flask Server

```bash
cd mini_project
.\.venv\Scripts\activate  # Windows
python app/app.py
```

You'll see:
```
Starting AI Smart Hiring Platform...
Flask app running on http://localhost:5000
Running on http://127.0.0.1:5000
```

### 2. Open in Your Browser

Go to: **http://localhost:5000**

### 3. Upload & Analyze Resumes

1. Click **"Upload Resume"** tab
2. Drag & drop resume files (PDF, TXT, CSV)
3. Paste job description on the right
4. Click **"Analyze Candidate"**
5. View results with match scores and extracted skills!

## 📊 Web Pages

| Page | URL | Purpose |
|------|-----|---------|
| **Dashboard** | `/` | View candidates and statistics |
| **Upload** | `/upload` | Upload resumes and job description |
| **Analytics** | `/analytics` | View detailed analysis results |

## 🔌 API Endpoints

```bash
# Get dashboard stats
curl http://localhost:5000/api/dashboard-stats

# Get latest analyzed candidate
curl http://localhost:5000/api/latest-candidate

# Health check
curl http://localhost:5000/api/health
```

## 📚 What Each Module Does

### Data Processing (`data/data_processing.py`)
- Loads 2,482 resumes from CSV
- Cleans and deduplicates data
- Extracts features (word count, length)
- Encodes job categories

### NLP Pipeline (`nlp/nlp_pipeline.py`)
- Tokenization using spaCy
- Removes stopwords with NLTK
- Lemmatization to base forms
- TF-IDF vectorization
- Extracts bigrams and trigrams

### ML Models (`models/train_model.py`)
- **4 algorithms trained**: Logistic Regression, Decision Tree, Random Forest, SVM
- **Hyperparameter tuning** with GridSearchCV
- **5-fold cross-validation**
- **Evaluation metrics**: Accuracy, Precision, Recall, F1, ROC-AUC
- **Models saved** as .pkl files for inference

### Flask App (`app/app.py`)
- Routes for dashboard, upload, analytics
- API endpoints for analysis
- Resume file handling
- Match score calculation
- Candidate data storage

## 🧪 Testing the API

Run the automated test suite:

```bash
python test_api.py
```

This will test:
- ✓ Health check
- ✓ Dashboard page
- ✓ Upload page
- ✓ Analytics page
- ✓ Dashboard stats API
- ✓ Latest candidate API
- ✓ File upload and analysis

## 📝 Example Workflow

1. **Start Flask app**
   ```bash
   python app/app.py
   ```

2. **Visit dashboard** at `http://localhost:5000`

3. **Navigate to upload page**

4. **Upload sample resume**
   ```
   John Doe
   john@email.com
   
   Senior Python Developer
   5+ years experience
   Skills: Python, FastAPI, AWS, Docker
   ```

5. **Enter job description**
   ```
   Senior Python Backend Engineer
   Requirements: 5+ years Python, AWS experience
   Skills: Python, FastAPI, PostgreSQL, Docker
   ```

6. **Click "Analyze Candidate"**

7. **View results on analytics page**
   - Match score: ~85-95%
   - Extracted skills
   - Interview questions
   - Experience summary

## 🎯 Key Features Implemented

### ✅ Resume Uploading
- Drag & drop interface
- Batch upload support
- Multiple file formats (PDF, TXT, CSV)

### ✅ intelligent Matching
- TF-IDF cosine similarity
- Job description comparison
- 0-100% match score

### ✅ Skill Extraction
- Automatic NLP-based extraction
- Token-level analysis
- Skill ranking

### ✅ Candidate Profiles
- Name & email extraction
- Experience detection
- Performance scoring

### ✅ Modern UI
- Responsive design (Mobile/Desktop)
- Tailwind CSS styling
- Material Design icons
- Smooth animations

## 🔧 Customization

### Change Match Score Calculation
Edit `app/app.py` in the `calculate_match_score()` function:
```python
def calculate_match_score(resume_text, job_description):
    # Modify this function to change scoring logic
    ...
```

### Add More ML Models
Edit `models/train_model.py` to add new algorithms and hyperparameters.

### Customize NLP Processing
Edit `nlp/nlp_pipeline.py` to modify tokenization, lemmatization, or TF-IDF settings.

## 🚨 Troubleshooting

### Port 5000 already in use
```bash
# Find what's using port 5000
netstat -an | findstr 5000

# Or use a different port
python -c "
from app.app import app
app.run(port=5001)
"
```

### spaCy model not found
```bash
python -m spacy download en_core_web_sm
```

### Module import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Flask not reloading on code changes
The app runs in debug mode (auto-reload enabled) by default. Changes to `app.py`, templates, or other files will automatically reload the server.

## 📈 Performance

| Task | Time |
|------|------|
| Data preprocessing (2,482 resumes) | ~2 sec |
| NLP pipeline processing | ~30 sec |
| Model training | ~5 min |
| Single resume analysis | <2 sec |
| Match scoring | Real-time |

## 🎓 Dataset

- **Source**: `dataset/Resume/Resume.csv` and PDFs
- **Size**: 2,482 clean resumes
- **Categories**: 25 job roles (IT, Finance, HR, Sales, etc.)
- **Distribution**: Balanced (~100-120 per category)

## 📦 Technology Stack

```
Backend:     Flask, Python, NumPy, Pandas
ML/NLP:      Scikit-learn, NLTK, spaCy, TF-IDF
Frontend:    HTML, Tailwind CSS, JavaScript
Data:        Pandas, Joblib
Models:      Logistic Regression, Decision Tree, Random Forest, SVM
```

## 🎉 You're All Set!

Your AI Smart Hiring Platform is ready to use. Start the Flask app and begin analyzing candidates!

```bash
python app/app.py
# Then open http://localhost:5000 in your browser
```

## 📞 Need Help?

Refer to [README.md](README.md) for comprehensive documentation.

Happy recruiting! 🚀
"""
WSGI entry point for production deployment.

This file is used by production WSGI servers (gunicorn, uWSGI, etc.)
to load the Flask application.

Usage:
  gunicorn wsgi:app
  gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Download NLTK data before importing the app
try:
    import nltk
    required_packages = ['punkt', 'punkt_tab', 'stopwords', 'wordnet', 'omw-1.4']
    for package in required_packages:
        try:
            nltk.download(package, quiet=True)
        except Exception:
            pass  # Continue if download fails
except ImportError:
    pass  # NLTK not available

from app.app import app

if __name__ == "__main__":
    app.run()

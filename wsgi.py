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

from app.app import app

if __name__ == "__main__":
    app.run()

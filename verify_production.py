#!/usr/bin/env python3
"""
Production readiness verification script.

This script checks if the application is properly configured for production deployment.
Run this before deploying to ensure all critical components are in place.

Usage:
  python verify_production.py
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Verify required environment configuration."""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        'FLASK_ENV': 'Environment mode (production/development/testing)',
        'SECRET_KEY': 'Flask session encryption key',
        'GOOGLE_API_KEY': 'Google Gemini API key',
    }
    
    optional_vars = {
        'DATABASE_PATH': 'SQLite database path',
        'UPLOAD_FOLDER': 'Resume upload directory',
        'PORT': 'Server port (default: 5000)',
        'LOG_LEVEL': 'Logging level (default: INFO)',
    }
    
    issues = []
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            issues.append(f"❌ {var}: MISSING - {description}")
        else:
            if var == 'SECRET_KEY':
                if len(value) < 16:
                    issues.append(f"⚠️  {var}: TOO SHORT (should be 16+ chars)")
                else:
                    print(f"✅ {var}: Configured")
            elif var == 'GOOGLE_API_KEY':
                if value.startswith('AIza'):
                    print(f"✅ {var}: Looks valid")
                else:
                    issues.append(f"⚠️  {var}: Format looks invalid (should start with 'AIza')")
            else:
                print(f"✅ {var}: Configured")
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Configured")
        else:
            print(f"ℹ️  {var}: Using default - {description}")
    
    return issues

def check_files():
    """Verify required files exist."""
    print("\n📁 Checking required files...")
    
    required_files = {
        'config.py': 'Configuration management module',
        'wsgi.py': 'WSGI entry point for production servers',
        'Procfile': 'Heroku deployment configuration',
        'requirements.txt': 'Python dependencies',
        '.env.example': 'Environment variable template',
        'app/app.py': 'Flask application',
        'app/rag_engine.py': 'RAG/search engine module',
        'genai_helper.py': 'GenAI integration module',
    }
    
    issues = []
    
    for filepath, description in required_files.items():
        if os.path.exists(filepath):
            print(f"✅ {filepath}: Found")
        else:
            issues.append(f"❌ {filepath}: MISSING - {description}")
    
    return issues

def check_imports():
    """Verify critical module imports work."""
    print("\n📦 Checking module imports...")
    
    modules_to_check = [
        ('flask', 'Flask web framework'),
        ('config', 'Configuration module'),
        ('genai_helper', 'GenAI helper module'),
    ]
    
    issues = []
    
    for module_name, description in modules_to_check:
        try:
            if module_name == 'config':
                import config as mod
            elif module_name == 'genai_helper':
                import genai_helper as mod
            else:
                mod = __import__(module_name)
            print(f"✅ {module_name}: Import successful")
        except ImportError as e:
            issues.append(f"❌ {module_name}: Import failed - {e}")
    
    return issues

def check_database():
    """Verify database file exists or can be created."""
    print("\n💾 Checking database...")
    
    db_path = os.getenv('DATABASE_PATH', 'hiring.db')
    
    issues = []
    
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"✅ Database exists: {db_path} ({size} bytes)")
    else:
        if os.access(os.path.dirname(db_path) or '.', os.W_OK):
            print(f"✅ Database path writable: {db_path} (will be created on first run)")
        else:
            issues.append(f"❌ Database path not writable: {db_path}")
    
    return issues

def check_uploads():
    """Verify uploads directory exists or can be created."""
    print("\n📤 Checking uploads directory...")
    
    upload_dir = os.getenv('UPLOAD_FOLDER', 'uploads')
    
    issues = []
    
    if os.path.exists(upload_dir):
        print(f"✅ Upload directory exists: {upload_dir}")
    else:
        if os.access(os.path.dirname(upload_dir) or '.', os.W_OK):
            print(f"✅ Upload directory path writable: {upload_dir} (will be created on first run)")
        else:
            issues.append(f"❌ Upload directory path not writable: {upload_dir}")
    
    return issues

def main():
    """Run all production readiness checks."""
    print("=" * 60)
    print("Production Readiness Verification")
    print("=" * 60)
    
    all_issues = []
    
    all_issues.extend(check_environment())
    all_issues.extend(check_files())
    all_issues.extend(check_imports())
    all_issues.extend(check_database())
    all_issues.extend(check_uploads())
    
    print("\n" + "=" * 60)
    
    if not all_issues:
        print("✅ All checks passed! Application is ready for production.")
        print("\nNext steps:")
        print("1. Review DEPLOYMENT.md for platform-specific instructions")
        print("2. Deploy using: gunicorn wsgi:app")
        print("3. Monitor logs for any issues")
        return 0
    else:
        print(f"⚠️  {len(all_issues)} issue(s) found:\n")
        for issue in all_issues:
            print(f"  {issue}")
        print("\nPlease resolve the above issues before deploying to production.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

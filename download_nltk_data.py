#!/usr/bin/env python3
"""
Script to download all required NLTK data for the application.
This ensures NLTK resources are available in production environments.
"""

import nltk
import sys

def download_nltk_data():
    """Download all required NLTK data packages."""
    required_packages = [
        'punkt',
        'punkt_tab',
        'stopwords',
        'wordnet',
        'omw-1.4'
    ]

    print("Downloading NLTK data packages...")
    for package in required_packages:
        try:
            print(f"Downloading {package}...")
            nltk.download(package, quiet=True)
            print(f"✓ {package} downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download {package}: {e}")
            # Continue with other packages

    print("NLTK data download complete.")

if __name__ == "__main__":
    download_nltk_data()
#!/usr/bin/env python
"""
Test script for the AI Smart Hiring Platform Flask application.
Tests all API endpoints and functionality.
"""

import sys
import os
import json
import requests
from time import sleep

# Configuration
BASE_URL = 'http://localhost:5000'
TIMEOUT = 10

def test_health_check():
    """Test health check endpoint."""
    print("\n✓ Testing Health Check...")
    try:
        response = requests.get(f'{BASE_URL}/api/health', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_dashboard_page():
    """Test dashboard page load."""
    print("\n✓ Testing Dashboard Page...")
    try:
        response = requests.get(f'{BASE_URL}/', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        print(f"  Page size: {len(response.content)} bytes")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_upload_page():
    """Test upload page load."""
    print("\n✓ Testing Upload Page...")
    try:
        response = requests.get(f'{BASE_URL}/upload', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        print(f"  Page size: {len(response.content)} bytes")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_analytics_page():
    """Test analytics page load."""
    print("\n✓ Testing Analytics Page...")
    try:
        response = requests.get(f'{BASE_URL}/analytics', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        print(f"  Page size: {len(response.content)} bytes")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_dashboard_stats():
    """Test dashboard stats API."""
    print("\n✓ Testing Dashboard Stats API...")
    try:
        response = requests.get(f'{BASE_URL}/api/dashboard-stats', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Total candidates: {data.get('total', 0)}")
        print(f"  Shortlisted: {data.get('shortlisted', 0)}")
        print(f"  Pending: {data.get('pending', 0)}")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_latest_candidate():
    """Test latest candidate API."""
    print("\n✓ Testing Latest Candidate API...")
    try:
        response = requests.get(f'{BASE_URL}/api/latest-candidate', timeout=TIMEOUT)
        print(f"  Status: {response.status_code}")
        data = response.json()
        if data.get('success'):
            candidate = data.get('candidate', {})
            print(f"  Candidate: {candidate.get('name', 'N/A')}")
            print(f"  Match Score: {candidate.get('match_score', 'N/A')}%")
        else:
            print(f"  Message: {data.get('error', 'No candidates available')}")
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_file_upload():
    """Test resume upload API."""
    print("\n✓ Testing Resume Upload API...")
    
    # Create a test resume file
    test_resume = """
    John Doe
    john@example.com
    
    Software Engineer with 5+ years of experience in Python, Java, and web development.
    
    Skills: Python, Java, JavaScript, React, AWS, Docker, Machine Learning
    
    Experience:
    - Senior Developer at Tech Corp (2020-2024)
    - Developer at StartUp Inc (2019-2020)
    - Junior Developer at WebCo (2018-2019)
    
    Education:
    - BS Computer Science, Tech University (2018)
    """
    
    job_description = """
    Senior Python Developer
    Requirements: 5+ years Python experience, ML/AI knowledge preferred
    Skills: Python, FastAPI, PostgreSQL, AWS, Docker
    """
    
    try:
        files = {'files': ('test_resume.txt', test_resume.encode())}
        data = {'job_description': job_description}
        
        response = requests.post(
            f'{BASE_URL}/api/analyze',
            files=files,
            data=data,
            timeout=TIMEOUT
        )
        
        print(f"  Status: {response.status_code}")
        result = response.json()
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message', result.get('error'))}")
        
        if result.get('candidates'):
            for candidate in result.get('candidates', []):
                print(f"    - {candidate.get('name')}: {candidate.get('match_score')}% match")
        
        return response.status_code == 200 and result.get('success')
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("AI Smart Hiring Platform - API Test Suite")
    print("=" * 60)
    
    print(f"\nBase URL: {BASE_URL}")
    print("Waiting for Flask server to be ready...")
    
    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f'{BASE_URL}/api/health', timeout=5)
            if response.status_code == 200:
                print("✓ Flask server is ready!\n")
                break
        except:
            if i < max_retries - 1:
                sleep(1)
            else:
                print("✗ Flask server not responding. Make sure it's running on port 5000")
                return False
    
    tests = [
        ("Health Check", test_health_check),
        ("Dashboard Page", test_dashboard_page),
        ("Upload Page", test_upload_page),
        ("Analytics Page", test_analytics_page),
        ("Dashboard Stats API", test_dashboard_stats),
        ("Latest Candidate API", test_latest_candidate),
        ("File Upload API", test_file_upload),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✓ All tests passed! The application is ready to use.")
        return True
    else:
        print(f"\n✗ {total_count - passed_count} test(s) failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
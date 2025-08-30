#!/usr/bin/env python3
"""
Test script to verify database connection and latest-update-time endpoint
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and table existence"""
    from app import create_app, db
    from sqlalchemy import inspect

    print("Testing database connection...")

    app = create_app()
    with app.app_context():
        try:
            # Test basic connection
            db.session.execute(db.text("SELECT 1"))
            print("Database connection successful")

            # Check tables
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            expected_tables = ['users', 'updates', 'read_logs', 'activity_logs',
                             'archived_updates', 'archived_sop_summaries',
                             'archived_lessons_learned', 'sop_summaries', 'lessons_learned']

            print(f"Existing tables: {existing_tables}")
            missing_tables = [table for table in expected_tables if table not in existing_tables]

            if missing_tables:
                print(f"Missing tables: {missing_tables}")
                return False
            else:
                print("All expected tables exist")

            # Test the updates table specifically
            if 'updates' in existing_tables:
                from models import Update
                count = Update.query.count()
                print(f"Updates table accessible, contains {count} records")

            return True

        except Exception as e:
            print(f"Database test failed: {e}")
            return False

def test_api_endpoint():
    """Test the latest-update-time API endpoint"""
    print("\nTesting API endpoint...")

    # Get the app URL from environment or use localhost
    app_url = os.getenv("APP_URL", "http://localhost:8000")

    try:
        response = requests.get(f"{app_url}/api/latest-update-time", timeout=10)
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"API Response: {data}")
            if data.get("success"):
                print("API endpoint working correctly")
                return True
            else:
                print(f"API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to API: {e}")
        return False

if __name__ == "__main__":
    print("Testing database and API functionality...\n")

    db_success = test_database_connection()
    api_success = test_api_endpoint()

    print("\nTest Results:")
    print(f"Database: {'PASS' if db_success else 'FAIL'}")
    print(f"API: {'PASS' if api_success else 'FAIL'}")

    if db_success and api_success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
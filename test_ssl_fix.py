#!/usr/bin/env python3
"""
Test script to verify SSL configuration fixes for Render deployment.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import health_check, test_ssl_connection

def test_ssl_configuration():
    """Test the SSL configuration fixes."""
    print("Testing SSL configuration fixes...")

    app = create_app()

    with app.app_context():
        print("\n1. Testing database health check...")
        health_ok = health_check()
        if health_ok:
            print("Health check passed")
        else:
            print("Health check failed")
            return False

        print("\n2. Testing SSL connection...")
        ssl_ok = test_ssl_connection()
        if ssl_ok:
            print("SSL connection test passed")
        else:
            print("SSL connection test failed")
            return False

        print("\n3. Testing basic database operations...")
        try:
            from models import User
            user_count = User.query.count()
            print(f"Database operations working - {user_count} users found")
        except Exception as e:
            print(f"Database operations failed: {e}")
            return False

        print("\nAll SSL configuration tests passed!")
        return True

if __name__ == "__main__":
    success = test_ssl_configuration()
    sys.exit(0 if success else 1)
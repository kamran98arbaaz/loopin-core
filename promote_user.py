#!/usr/bin/env python3
"""
Script to promote a user to admin role
Usage: python promote_user.py
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Flask app and models
from app import create_app
from models import User, db

def promote_user_to_admin(username):
    """Promote a user to admin role"""
    try:
        app = create_app()

        with app.app_context():
            # Find the user
            user = User.query.filter_by(username=username).first()

            if not user:
                print(f"ERROR: User '{username}' not found")
                return False

            # Check current role
            if user.role == 'admin':
                print(f"INFO: User '{username}' is already an admin")
                return True

            # Promote to admin
            old_role = user.role
            user.role = 'admin'
            db.session.commit()

            print(f"SUCCESS: Promoted '{username}' from {old_role} to admin")
            print(f"   User ID: {user.id}")
            print(f"   Display Name: {user.display_name}")
            print(f"   New Role: {user.role}")

            return True

    except Exception as e:
        print(f"ERROR: Failed to promote user: {e}")
        return False

if __name__ == "__main__":
    # Promote kamran_arbaz to admin
    username = "kamran_arbaz"
    print(f"Promoting user '{username}' to admin role...")

    success = promote_user_to_admin(username)

    if success:
        print("\nUser promotion completed successfully!")
    else:
        print("\nUser promotion failed!")
        sys.exit(1)
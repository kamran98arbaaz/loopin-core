#!/usr/bin/env python3
"""
Script to promote a user to admin role.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User

def promote_user_to_admin(username):
    """Promote a user to admin role."""
    app = create_app()

    with app.app_context():
        try:
            # Find the user
            user = User.query.filter_by(username=username).first()

            if not user:
                print(f"ERROR: User '{username}' not found")
                return False

            print(f"Found user: {user.username} (ID: {user.id})")
            print(f"Current role: {user.role}")

            # Update role to admin
            user.role = 'admin'
            db.session.commit()

            print(f"SUCCESS: User '{username}' promoted to admin role")

            # Verify the change
            updated_user = User.query.filter_by(username=username).first()
            print(f"Verified role: {updated_user.role}")

            return True

        except Exception as e:
            print(f"ERROR: Failed to promote user: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python promote_user.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    success = promote_user_to_admin(username)
    sys.exit(0 if success else 1)
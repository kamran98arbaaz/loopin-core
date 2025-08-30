#!/usr/bin/env python3
"""
Script to create an admin user in the database.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import User

def create_admin_user():
    """Create admin user with specified details."""
    app = create_app()

    with app.app_context():
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(username='kamran_arbaz').first()
            if existing_user:
                print("WARNING: User 'kamran_arbaz' already exists!")
                return False

            # Create new admin user
            admin_user = User(
                username='kamran_arbaz',
                display_name='Kamran Arbaz',
                role='admin'
            )
            admin_user.set_password('9785arbaz')

            # Save to database
            from extensions import db
            db.session.add(admin_user)
            db.session.commit()

            print("SUCCESS: Admin user created successfully!")
            print(f"   Username: {admin_user.username}")
            print(f"   Display Name: {admin_user.display_name}")
            print(f"   Role: {admin_user.role}")
            print(f"   User ID: {admin_user.id}")

            return True

        except Exception as e:
            print(f"ERROR: Error creating admin user: {e}")
            from extensions import db
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
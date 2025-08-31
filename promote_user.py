#!/usr/bin/env python3
"""Script to promote a user to admin role"""

from app import create_app, db
from models import User

def promote_user_to_admin(username):
    """Promote a user to admin role"""
    app = create_app()
    with app.app_context():
        # Find the user
        user = User.query.filter_by(username=username).first()

        if not user:
            print(f"User '{username}' not found in database")
            return False

        print(f"User found: {user.username}")
        print(f"Current role: {user.role}")
        print(f"Display name: {user.display_name}")

        # Update role to admin
        old_role = user.role
        user.role = 'admin'
        db.session.commit()

        print(f"User '{username}' promoted from '{old_role}' to 'admin' role")
        return True

if __name__ == "__main__":
    username = "kamran_arbaz"
    success = promote_user_to_admin(username)
    if success:
        print("User promotion completed successfully!")
    else:
        print("User promotion failed!")
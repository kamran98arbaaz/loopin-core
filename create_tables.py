#!/usr/bin/env python3
"""
Script to create all database tables from models, bypassing migrations.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def create_all_tables():
    """Create all tables from models."""
    app = create_app()

    with app.app_context():
        try:
            print("Creating all tables from models...")
            db.create_all()
            print("SUCCESS: All tables created successfully!")

            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f"Created tables: {existing_tables}")

        except Exception as e:
            print(f"ERROR: Error creating tables: {e}")
            return False

    return True

if __name__ == "__main__":
    success = create_all_tables()
    sys.exit(0 if success else 1)
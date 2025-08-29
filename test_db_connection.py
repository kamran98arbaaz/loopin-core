#!/usr/bin/env python3
"""
Test script to verify database connection and table reflection for Render PostgreSQL migration.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Update, ReadLog, ActivityLog, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned, SOPSummary, LessonLearned
from sqlalchemy import inspect, text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection and verify tables."""
    app = create_app()

    with app.app_context():
        try:
            # Test basic connection
            result = db.session.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")

            # Check if tables exist
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            expected_tables = [
                'users', 'updates', 'read_logs', 'activity_logs',
                'archived_updates', 'archived_sop_summaries', 'archived_lessons_learned',
                'sop_summaries', 'lessons_learned', 'alembic_version'
            ]

            logger.info(f"📋 Existing tables: {existing_tables}")
            logger.info(f"🎯 Expected tables: {expected_tables}")

            missing_tables = [table for table in expected_tables if table not in existing_tables]
            if missing_tables:
                logger.warning(f"⚠️ Missing tables: {missing_tables}")
            else:
                logger.info("✅ All expected tables are present")

            # Test queries on each table (only if table exists)
            if 'users' in existing_tables:
                try:
                    user_count = User.query.count()
                    logger.info(f"👥 Users table: {user_count} records")
                except Exception as e:
                    logger.error(f"❌ Users table query failed: {e}")

            if 'updates' in existing_tables:
                try:
                    update_count = Update.query.count()
                    logger.info(f"📢 Updates table: {update_count} records")
                except Exception as e:
                    logger.error(f"❌ Updates table query failed: {e}")

            if 'read_logs' in existing_tables:
                try:
                    readlog_count = ReadLog.query.count()
                    logger.info(f"👁️ ReadLogs table: {readlog_count} records")
                except Exception as e:
                    logger.error(f"❌ ReadLogs table query failed: {e}")

            if 'sop_summaries' in existing_tables:
                try:
                    sop_count = SOPSummary.query.count()
                    logger.info(f"📄 SOP Summaries table: {sop_count} records")
                except Exception as e:
                    logger.error(f"❌ SOP Summaries table query failed: {e}")

            if 'lessons_learned' in existing_tables:
                try:
                    lesson_count = LessonLearned.query.count()
                    logger.info(f"📚 Lessons Learned table: {lesson_count} records")
                except Exception as e:
                    logger.error(f"❌ Lessons Learned table query failed: {e}")

            logger.info("🎉 Database verification completed successfully!")

        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            return False

    return True

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
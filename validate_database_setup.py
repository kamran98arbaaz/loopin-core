#!/usr/bin/env python3
"""
Comprehensive database validation script for LoopIn
Checks database configuration, connection, and prevents SQLite usage in production
"""

import os
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def check_environment_variables():
    """Check critical environment variables"""
    print("Checking environment variables...")

    required_vars = ['DATABASE_URL', 'FLASK_ENV']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"ERROR {var}: Not set")
        else:
            if var == 'DATABASE_URL':
                # Mask the password in the URL for security
                parsed = urlparse(value)
                masked_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
                print(f"OK {var}: {masked_url}")
            else:
                print(f"OK {var}: {value}")

    if missing_vars:
        print(f"ERROR Missing required environment variables: {missing_vars}")
        return False

    return True

def validate_database_url():
    """Validate DATABASE_URL configuration"""
    print("\nValidating DATABASE_URL...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR DATABASE_URL not set")
        return False

    parsed = urlparse(database_url)

    # Check scheme
    if parsed.scheme not in ('postgresql', 'postgres'):
        if parsed.scheme in ('sqlite', 'sqlite3'):
            print("CRITICAL: SQLite database detected!")
            print("   This will cause 'cannot notify on un-acquired lock' errors in production")
            print("   Please configure PostgreSQL database for production use")
            return False
        else:
            print(f"ERROR Unsupported database scheme: {parsed.scheme}")
            print("   Only PostgreSQL is supported for production")
            return False

    # Check required components
    if not parsed.hostname:
        print("ERROR Database hostname not specified in URL")
        return False

    if not parsed.username or not parsed.password:
        print("ERROR Database credentials not specified in URL")
        return False

    print("OK DATABASE_URL validation passed")
    print(f"   Host: {parsed.hostname}")
    print(f"   Database: {parsed.path.lstrip('/')}")
    print(f"   SSL: {'Enabled' if 'sslmode=require' in database_url else 'Not specified'}")

    return True

def check_config_files():
    """Check configuration files for SQLite fallbacks"""
    print("\nChecking configuration files...")

    issues_found = []

    # Check config.py for SQLite fallbacks
    try:
        with open('config.py', 'r') as f:
            content = f.read()

        if 'sqlite://' in content:
            issues_found.append("config.py contains SQLite fallbacks")
            print("WARNING: config.py contains SQLite database URLs")
            print("   This may cause issues if configuration loading doesn't work properly")

    except FileNotFoundError:
        print("INFO: config.py not found - using direct DATABASE_URL configuration")

    # Check app.py for proper database configuration
    try:
        with open('app.py', 'r') as f:
            content = f.read()

        if 'sqlite:///:memory:' in content:
            issues_found.append("app.py has SQLite memory fallback")
            print("WARNING: app.py contains SQLite memory fallback")
            print("   Ensure DATABASE_URL is always set to override this")

    except FileNotFoundError:
        print("ERROR app.py not found")
        return False

    if not issues_found:
        print("OK Configuration files look good")
        return True
    else:
        print(f"WARNING Found {len(issues_found)} potential configuration issues")
        return True  # Don't fail, just warn

def test_database_connection():
    """Test actual database connection"""
    print("\nTesting database connection...")

    try:
        from app import create_app
        app = create_app()

        with app.app_context():
            from extensions import db

            # Test basic connection
            db.session.execute(db.text("SELECT 1"))
            print("OK Database connection successful")

            # Check database type
            if db.engine.url.drivername.startswith('sqlite'):
                print("CRITICAL: Connected to SQLite database!")
                print("   This will cause lock errors in production")
                return False
            elif db.engine.url.drivername == 'postgresql':
                print("OK Connected to PostgreSQL database")
            else:
                print(f"WARNING Connected to {db.engine.url.drivername} database")
                print("   Ensure this is the intended database type")

            # Check tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            expected_tables = ['users', 'updates', 'read_logs', 'activity_logs',
                             'archived_updates', 'archived_sop_summaries',
                             'archived_lessons_learned', 'sop_summaries', 'lessons_learned']

            missing_tables = [table for table in expected_tables if table not in existing_tables]

            if missing_tables:
                print(f"WARNING Missing tables: {missing_tables}")
                print("   Tables will be created automatically by SQLAlchemy")
            else:
                print("OK All expected tables exist")

            return True

    except Exception as e:
        print(f"ERROR Database connection test failed: {e}")
        return False

def check_deployment_environment():
    """Check deployment environment configuration"""
    print("\nChecking deployment environment...")

    is_production = os.getenv("FLASK_ENV") == "production"
    if is_production:
        print("OK Running in production environment")

        # Check production-specific variables
        prod_vars = ['DATABASE_URL']
        for var in prod_vars:
            value = os.getenv(var)
            if value:
                print(f"OK {var}: Set")
            else:
                print(f"WARNING {var}: Not set")

        # Ensure we're not using SQLite in production
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith('sqlite'):
            print("CRITICAL: SQLite database configured in production!")
            print("   This will definitely cause lock errors")
            return False

    else:
        print("INFO: Running in development/local environment")

    return True

def main():
    """Run all validation checks"""
    print("LoopIn Database Configuration Validator")
    print("=" * 50)

    checks = [
        ("Environment Variables", check_environment_variables),
        ("DATABASE_URL Validation", validate_database_url),
        ("Configuration Files", check_config_files),
        ("Database Connection", test_database_connection),
        ("Deployment Environment", check_deployment_environment),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed with error: {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")

    passed = 0
    failed = 0

    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {len(results)} checks")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\nAll checks passed! Database configuration looks good.")
        return 0
    else:
        print(f"\n{failed} check(s) failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Ensure DATABASE_URL points to PostgreSQL (not SQLite)")
        print("- Check that all required environment variables are set")
        print("- Verify database service is properly configured")
        return 1

if __name__ == "__main__":
    sys.exit(main())
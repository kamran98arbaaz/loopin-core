#!/usr/bin/env python3
"""
Environment variable checker for deployment
"""
import os
import sys
from urllib.parse import urlparse

def check_database_url():
    """Verify DATABASE_URL configuration"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL is not set")
        return False
    
    try:
        parsed = urlparse(db_url)
        if not all([parsed.scheme, parsed.hostname, parsed.path]):
            print("❌ DATABASE_URL is not properly formatted")
            return False
        print("✅ DATABASE_URL is properly configured")
        return True
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URL: {e}")
        return False

def check_flask_config():
    """Verify Flask configuration"""
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        print("❌ FLASK_SECRET_KEY is not set")
        return False
    
    if len(secret_key) < 32:
        print("⚠️ FLASK_SECRET_KEY should be at least 32 characters long")
        return False
    
    print("✅ Flask configuration is valid")
    return True

def check_redis_config():
    """Verify Redis configuration if used"""
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        print("ℹ️ REDIS_URL is not set (optional)")
        return True
    
    try:
        parsed = urlparse(redis_url)
        if not all([parsed.scheme, parsed.hostname]):
            print("❌ REDIS_URL is not properly formatted")
            return False
        print("✅ REDIS_URL is properly configured")
        return True
    except Exception as e:
        print(f"❌ Error parsing REDIS_URL: {e}")
        return False

def check_render_config():
    """Verify Render-specific configuration"""
    is_render = os.getenv('RENDER') == 'true'
    if not is_render:
        print("ℹ️ Not running on Render platform")
        return True
    
    required_vars = [
        'RENDER_EXTERNAL_URL',
        'RENDER_SERVICE_ID',
        'RENDER_GIT_BRANCH'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing Render environment variables: {', '.join(missing)}")
        return False
    
    print("✅ Render configuration is valid")
    return True

def main():
    """Main function to check all configurations"""
    print("\n🔍 Checking environment configuration...")
    print("=" * 50)
    
    checks = [
        ("Database Configuration", check_database_url()),
        ("Flask Configuration", check_flask_config()),
        ("Redis Configuration", check_redis_config()),
        ("Render Configuration", check_render_config())
    ]
    
    print("\n📊 Summary:")
    print("=" * 50)
    
    success = all(result for _, result in checks)
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    if success:
        print("\n✨ All checks passed! Ready for deployment.")
        return 0
    else:
        print("\n⚠️ Some checks failed. Please fix the issues before deploying.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

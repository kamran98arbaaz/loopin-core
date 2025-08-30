"""Application factory configuration"""

import os
from typing import Optional, Dict, Any

class Config:
    """Base configuration."""
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
    }
    APP_NAME = "LoopIn"
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # Enable connection health checks
        "pool_recycle": 300,        # Recycle connections after 5 minutes
        "pool_timeout": 30,         # Connection timeout after 30 seconds
        "max_overflow": 15,         # Maximum number of connections to overflow
        "pool_size": 30,           # Base number of connections in the pool
        "echo": False,             # Don't log all SQL statements in production
        "echo_pool": False         # Don't log connection pool operations
    }
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    REMEMBER_COOKIE_SECURE = True      # Secure flag for remember cookie
    REMEMBER_COOKIE_HTTPONLY = True    # HTTP-only flag for remember cookie
    REMEMBER_COOKIE_SAMESITE = "Lax"   # CSRF protection for remember cookie
    REMEMBER_COOKIE_DURATION = 2592000 # 30 days in seconds
    JSON_SORT_KEYS = False            # Better performance in production
    JSONIFY_PRETTYPRINT_REGULAR = False  # Don't prettify JSON in production
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = "uploads"

class ProductionConfig(Config):
    """Production configuration."""
    ENV = "production"
    DEBUG = False
    TESTING = False

    # Ensure PostgreSQL is used in production - no SQLite fallback
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required for production")
    if database_url.startswith('sqlite'):
        raise RuntimeError("SQLite database detected in production - PostgreSQL required")
    SQLALCHEMY_DATABASE_URI = database_url

    # Render-optimized SQLAlchemy engine options
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # Enable connection health checks
        "pool_recycle": 300,        # Recycle connections after 5 minutes
        "pool_timeout": 30,         # Increased timeout for Render
        "max_overflow": 5,          # Reduced overflow for Render limits
        "pool_size": 5,            # Base pool size for Render
        "echo": False,             # Don't log SQL statements in production
        "echo_pool": False,        # Don't log pool operations
        "pool_use_lifo": True,     # Use LIFO to reduce number of connections
        "pool_reset_on_return": "rollback"  # Reset connection state on return
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    ENV = "development"
    DEBUG = True
    TESTING = False

    # Use DATABASE_URL if available, otherwise allow SQLite for local development
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith('sqlite'):
            print("WARNING: Using SQLite database in development - this may cause lock issues")
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Only use SQLite as fallback when no DATABASE_URL is set
        SQLALCHEMY_DATABASE_URI = "sqlite:///loopin_dev.db"
        print("WARNING: No DATABASE_URL set, using SQLite for development")

class TestingConfig(Config):
    """Testing configuration."""
    ENV = "testing"
    DEBUG = True
    TESTING = True

    # Use PostgreSQL for testing if DATABASE_URL is available, otherwise use SQLite
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith('sqlite'):
            print("WARNING: Using SQLite database in testing - this may cause lock issues")
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Only use SQLite memory database as last resort for testing
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        print("WARNING: No DATABASE_URL set for testing, using SQLite memory database")

    WTF_CSRF_ENABLED = False

config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig
}

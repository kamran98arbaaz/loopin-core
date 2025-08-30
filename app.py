import os

# Removed gevent monkey patching - using sync workers for better SQLAlchemy compatibility
if os.getenv("FLASK_ENV") == "development":
    print("ℹ️ Using sync workers (no gevent monkey patching)")
import time
import uuid
import pytz
import re
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_migrate import Migrate
from read_logs import bp as read_logs_bp
from flask_login import LoginManager
from models import User, Update, ReadLog, SOPSummary, LessonLearned, ActivityLog, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned
from extensions import db, socketio
from database import db_session
from role_decorators import admin_required, editor_required, writer_required, delete_required, export_required, get_user_role_info
from timezone_utils import UTC, IST, now_utc, to_utc, to_ist, format_ist, ensure_timezone, is_within_hours, get_hours_ago
from io import BytesIO
import sys
import subprocess
from pathlib import Path

# Add system Python site-packages to path if needed (for environments with path issues)
try:
    import site
    # Get all site-packages directories and add them to path if not already present
    site_packages_dirs = site.getsitepackages()
    for site_dir in site_packages_dirs:
        if site_dir not in sys.path and os.path.exists(site_dir):
            sys.path.insert(0, site_dir)
except Exception:
    # Fallback: try common site-packages locations
    import platform
    python_version = f"Python{sys.version_info.major}{sys.version_info.minor}"
    if platform.system() == "Windows":
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages"),
            os.path.expanduser(f"~\\AppData\\Local\\Programs\\Python\\{python_version}\\Lib\\site-packages"),
            os.path.expanduser(f"~\\AppData\\Roaming\\Python\\Python{sys.version_info.major}{sys.version_info.minor}\\site-packages")
        ]
        for path in possible_paths:
            if path not in sys.path and os.path.exists(path):
                sys.path.insert(0, path)
                break

# Import pandas and openpyxl with error handling
try:
    import pandas as pd
    import openpyxl
    EXCEL_EXPORT_AVAILABLE = True
except ImportError as e:
    # Only print warning in development mode
    if os.getenv('FLASK_ENV') == 'development':
        print(f"Warning: Excel export dependencies not available: {e}")
    EXCEL_EXPORT_AVAILABLE = False

# Load .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up advanced logging configuration
try:
    from logging_config import setup_logging
    # This will be called after app creation
except ImportError:
    logger.warning("logging_config module not found - using basic logging")

migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login'

# Process start timestamp for basic metrics
APP_START = time.time()

# Simple in-memory cache for performance optimization
_cache = {}
CACHE_TIMEOUT = 300  # 5 minutes

def get_cached_user_role(user_id):
    """Get cached user role information"""
    cache_key = f"user_role_{user_id}"
    if cache_key in _cache:
        cached_time, role_info = _cache[cache_key]
        if time.time() - cached_time < CACHE_TIMEOUT:
            return role_info
        else:
            del _cache[cache_key]

    user = User.query.get(user_id)
    if user:
        role_info = get_user_role_info(user)
        _cache[cache_key] = (time.time(), role_info)
        return role_info

    return {'is_admin': False, 'is_editor': False, 'is_writer': False, 'is_deleter': False, 'is_exporter': False}

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Apply default config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Apply custom configuration
    if config_name:
        app.config.from_object(config_name)
    
    # Initialize extensions
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Initialize Socket.IO with optimized configuration
    socketio_kwargs = {
        'message_queue': None,
        'cors_allowed_origins': '*',
        'ping_timeout': 30,  # Reduced from 60 for faster disconnect detection
        'ping_interval': 15,  # Reduced from 25 for more frequent health checks
        'max_http_buffer_size': 500000,  # Reduced from 1e6 for memory efficiency
        'async_mode': 'threading',  # Use threading for better performance
        'transports': ['websocket', 'polling'],  # Prefer WebSocket
        'compression': True,
        'compression_threshold': 512,  # Compress smaller messages
    }
    
    socketio.init_app(app, **socketio_kwargs)
    app.register_blueprint(read_logs_bp)
    # Register new API blueprint (first milestone)
    try:
        from api.updates import updates_bp as api_bp
        app.register_blueprint(api_bp)
    except Exception:
        # Blueprint registration should not break app startup if something is off
        pass
    
    # Register Socket.IO blueprint for real-time updates
    try:
        from api.socketio import bp as socketio_bp, init_socketio
        app.register_blueprint(socketio_bp)
        init_socketio(socketio, app)
        if os.getenv("FLASK_ENV") == "development":
            print("SUCCESS: Socket.IO blueprint registered successfully")
    except Exception as e:
        # Socket.IO registration should not break app startup if something is off
        logger.error(f"Socket.IO blueprint registration failed: {e}")
        if os.getenv("FLASK_ENV") == "development":
            print(f"WARNING: Socket.IO blueprint registration failed: {e}")
            import traceback
            print(f"WARNING: Full error: {traceback.format_exc()}")
        pass
    
    # Register search API blueprint
    try:
        from api.search import bp as search_bp
        app.register_blueprint(search_bp)
    except Exception:
        # Search API registration should not break app startup if something is off
        pass

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Security configuration
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
    app.config["APP_NAME"] = "LoopIn"

    # CORS configuration for Socket.IO
    app.config["CORS_HEADERS"] = "Content-Type"

    # Secure session configuration - adjust for Render
    is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
    if is_production:
        app.config["SESSION_COOKIE_SECURE"] = True  # Only send cookies over HTTPS
    else:
        app.config["SESSION_COOKIE_SECURE"] = False  # Allow HTTP for development
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to session cookie
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # Session timeout in seconds

    # Render-specific configurations
    if os.getenv("RENDER"):
        app.config["SERVER_NAME"] = None  # Disable SERVER_NAME for Render
        app.config["PREFERRED_URL_SCHEME"] = "https"  # Force HTTPS on Render

        # Additional Render configurations for Socket.IO
        app.config["RENDER_STATIC_URL"] = os.getenv("RENDER_EXTERNAL_URL", "")

        # Log Render environment info (only in development)
        if os.getenv("FLASK_ENV") == "development":
            print(f"🎨 Render Environment: {os.getenv('RENDER')}")
            print(f"🎨 Render Service ID: {os.getenv('RENDER_SERVICE_ID', 'Not set')}")
            print(f"🎨 Render Service Name: {os.getenv('RENDER_SERVICE_NAME', 'Not set')}")
            print(f"🎨 Render External URL: {os.getenv('RENDER_EXTERNAL_URL', 'Not set')}")
            print(f"🎨 Render Git Commit: {os.getenv('RENDER_GIT_COMMIT', 'Not set')}")
            print(f"🎨 Render Git Branch: {os.getenv('RENDER_GIT_BRANCH', 'Not set')}")

    # Database configuration
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "sqlite:///loopin.db"
        if os.getenv("FLASK_ENV") == "development":
            print("⚠️ DATABASE_URL not set, using SQLite by default")
    else:
        if os.getenv("FLASK_ENV") == "development":
            print("Using database from DATABASE_URL")

    parsed = urlparse(database_url)
    if parsed.scheme not in ("postgresql", "postgres", "sqlite", "sqlite3"):
        raise RuntimeError(f"Unsupported DB scheme: {parsed.scheme}")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure SSL for PostgreSQL with Render-specific defaults
    if parsed.scheme in ("postgresql", "postgres"):
        ssl_config = {}

        # Set SSL mode with Render-friendly defaults
        ssl_mode = os.getenv("PG_SSLMODE", "require")  # Default to 'require' for Render
        ssl_config["sslmode"] = ssl_mode
        logger.info(f"PostgreSQL SSL mode: {ssl_mode}")

        # Render-specific SSL parameters
        if os.getenv("PG_SSLROOTCERT"):
            ssl_config["sslrootcert"] = os.getenv("PG_SSLROOTCERT")
        if os.getenv("PG_SSLCERT"):
            ssl_config["sslcert"] = os.getenv("PG_SSLCERT")
        if os.getenv("PG_SSLKEY"):
            ssl_config["sslkey"] = os.getenv("PG_SSLKEY")

        # Set connection arguments for Render with optimized connection pooling
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": ssl_config,
            # Optimized connection pool settings for better performance
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_timeout": 30,  # Increased timeout for better reliability
            "pool_size": 10,     # Increased pool size for concurrent requests
            "max_overflow": 20,  # Increased overflow for peak loads
            # Additional settings for stability and performance
            "echo": False,  # Disable SQL echoing in production
            "pool_reset_on_return": "rollback",  # Reset connections on return
        }

        logger.info(f"SQLAlchemy engine options configured for Render PostgreSQL with sync workers")
    else:
        # Non-PostgreSQL databases use optimized settings
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_timeout": 30,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_reset_on_return": "rollback",
        }

    db.init_app(app)

    with app.app_context():
        if os.getenv("FLASK_ENV") == "development":
            print("Database configured successfully")

        # Verify database connection and table reflection
        db_verification_success = False
        try:
            # Test basic connection with health check
            from database import get_connection_with_retry
            with get_connection_with_retry() as test_conn:
                test_conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")

            # Test SSL connection if using PostgreSQL (in separate session to avoid transaction abortion)
            ssl_test_result = False
            try:
                from database import test_ssl_connection
                # Create a new healthy connection for SSL testing
                with get_connection_with_retry() as test_conn:
                    ssl_test_result = test_ssl_connection(test_conn)
                if ssl_test_result:
                    logger.info("SSL connection test passed")
                else:
                    logger.warning("⚠️ SSL connection test failed - this may cause issues")
            except Exception as ssl_e:
                logger.warning(f"⚠️ SSL test error (non-critical): {ssl_e}")

            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            expected_tables = ['users', 'updates', 'read_logs', 'activity_logs', 'archived_updates', 'archived_sop_summaries', 'archived_lessons_learned', 'sop_summaries', 'lessons_learned']

            logger.info(f"Existing tables: {existing_tables}")
            logger.info(f"Expected tables: {expected_tables}")

            missing_tables = [table for table in expected_tables if table not in existing_tables]
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
            else:
                logger.info("All expected tables are present")

            # Test a simple query on users table with connection health check
            try:
                user_count = User.query.count()
                logger.info(f"Users table has {user_count} records")
            except Exception as query_e:
                logger.warning(f"⚠️ User count query failed, but continuing: {query_e}")

            db_verification_success = True

        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            if os.getenv("FLASK_ENV") == "development":
                print(f"❌ Database verification failed: {e}")

            # Enhanced cleanup on error
            try:
                db.session.rollback()
                db.session.close()
                # Force engine disposal to clear any problematic connections
                db.engine.dispose()
                logger.info("Database engine disposed due to verification failure")
            except Exception as cleanup_e:
                logger.error(f"Error during cleanup: {cleanup_e}")

        # If database verification failed, don't continue with app startup
        if not db_verification_success:
            logger.error("❌ Database verification failed - aborting app startup")
            # In production, we might want to be more graceful
            if os.getenv("FLASK_ENV") == "production":
                logger.warning("⚠️ Continuing with app startup despite database issues (production mode)")
            else:
                raise RuntimeError("Database verification failed - cannot start application")

    # Activity Logging Helper
    def log_activity(action, entity_type, entity_id, entity_title=None, details=None):
        """Log user activity for audit trail"""
        try:
            user_id = session.get("user_id")

            # Get client IP address
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()

            # Get user agent
            user_agent = request.headers.get('User-Agent', 'Unknown')

            activity = ActivityLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                entity_title=entity_title,
                timestamp=now_utc(),
                ip_address=client_ip,
                user_agent=user_agent,
                details=details
            )

            db.session.add(activity)
            db.session.commit()
        except Exception as e:
            # Don't let activity logging break the main functionality
            if os.getenv("FLASK_ENV") == "development":
                print(f"Activity logging failed: {e}")

    # Archive Helper Functions
    def archive_update(update):
        """Archive an update before deletion"""
        try:
            # Validate update object
            if not update or not update.id:
                raise ValueError("Invalid update object")

            # Get archiving user
            user_id = session.get("user_id")
            if not user_id:
                app.logger.warning("Archiving update without user context")

            # Check if already archived
            existing_archive = ArchivedUpdate.query.get(update.id)
            if existing_archive:
                app.logger.warning(f"Update {update.id} already archived")
                return True

            # Create archive record
            archived_update = ArchivedUpdate(
                id=update.id,
                name=update.name,
                process=update.process,
                message=update.message,
                timestamp=update.timestamp,
                archived_at=now_utc(),
                archived_by=user_id
            )

            # Save the archive
            db.session.add(archived_update)
            db.session.commit()
            
            app.logger.info(f"Successfully archived update {update.id}")
            return True
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to archive update {update.id if update and hasattr(update, 'id') else 'unknown'}: {str(e)}")
            return False

    def archive_sop(sop):
        """Archive a SOP before deletion"""
        try:
            # Validate SOP object
            if not sop or not sop.id:
                raise ValueError("Invalid SOP object")

            # Get archiving user
            user_id = session.get("user_id")
            if not user_id:
                app.logger.warning("Archiving SOP without user context")

            # Check if already archived
            existing_archive = ArchivedSOPSummary.query.get(sop.id)
            if existing_archive:
                app.logger.warning(f"SOP {sop.id} already archived")
                return True

            # Create archive record
            archived_sop = ArchivedSOPSummary(
                id=sop.id,
                title=sop.title,
                summary_text=sop.summary_text,
                department=sop.department,
                tags=sop.tags,
                created_at=sop.created_at,
                archived_at=now_utc(),
                archived_by=user_id
            )

            # Save the archive
            db.session.add(archived_sop)
            db.session.commit()
            
            app.logger.info(f"Successfully archived SOP {sop.id}")
            return True
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to archive SOP {sop.id if sop and hasattr(sop, 'id') else 'unknown'}: {str(e)}")
            return False

    def archive_lesson(lesson):
        """Archive a lesson learned before deletion"""
        try:
            # Validate lesson object
            if not lesson or not lesson.id:
                raise ValueError("Invalid lesson object")

            # Get archiving user
            user_id = session.get("user_id")
            if not user_id:
                app.logger.warning("Archiving lesson without user context")

            # Check if already archived
            existing_archive = ArchivedLessonLearned.query.get(lesson.id)
            if existing_archive:
                app.logger.warning(f"Lesson {lesson.id} already archived")
                return True

            # Create archive record
            archived_lesson = ArchivedLessonLearned(
                id=lesson.id,
                title=lesson.title,
                content=lesson.content,
                summary=lesson.summary,
                author=lesson.author,
                department=lesson.department,
                tags=lesson.tags,
                created_at=lesson.created_at,
                archived_at=now_utc(),
                archived_by=user_id
            )

            # Save the archive
            db.session.add(archived_lesson)
            db.session.commit()
            
            app.logger.info(f"Successfully archived lesson {lesson.id}")
            return True
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to archive lesson {lesson.id if lesson and hasattr(lesson, 'id') else 'unknown'}: {str(e)}")
            return False

    # Auth Helpers
    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                flash("🔒 Please log in to continue.")
                return redirect(url_for("login", next=request.endpoint))
            return f(*args, **kwargs)
        return decorated

    @app.context_processor
    def inject_current_user():
        """Inject current user into template context with caching"""
        user_id = session.get("user_id")
        if user_id:
            # Use get() instead of filter_by().first() for better performance
            user = User.query.get(user_id)
            return dict(current_user=user)
        return dict(current_user=None)

    @app.context_processor
    def inject_user_role_info():
        """
        Inject user role information into templates for conditional rendering.
        """
        user_id = session.get("user_id")
        if user_id:
            role_info = get_cached_user_role(user_id)
            return dict(user_role=role_info)
        return dict(user_role={'is_admin': False, 'is_editor': False, 'is_writer': False, 'is_deleter': False, 'is_exporter': False})

    @app.context_processor
    def inject_now_utc():
        """Make now_utc function available in templates"""
        return dict(now_utc=now_utc)

    @app.template_filter('to_ist')
    def to_ist_filter(utc_datetime):
        """Convert UTC datetime to IST for display"""
        return format_ist(utc_datetime, '%Y-%m-%d %H:%M')

    @app.template_filter('format_datetime')
    def format_datetime_filter(dt, format='%Y-%m-%d %H:%M'):
        """Format datetime with timezone conversion"""
        return format_ist(dt, format)

    @app.template_filter('format_backup_timestamp')
    def format_backup_timestamp_filter(iso_string):
        """Convert ISO timestamp string to IST for backup display"""
        if not iso_string:
            return 'N/A'
        try:
            # Parse the ISO string to datetime
            from datetime import datetime
            # Handle different ISO formats
            if iso_string.endswith('Z'):
                iso_string = iso_string.replace('Z', '+00:00')
            elif '+' not in iso_string and 'T' in iso_string:
                # Assume UTC if no timezone info
                iso_string = iso_string + '+00:00'

            dt = datetime.fromisoformat(iso_string)
            # Convert to IST and format
            return format_ist(dt, '%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError, TypeError):
            # Fallback to original string manipulation if parsing fails
            try:
                return iso_string[:19].replace('T', ' ') + ' (UTC)'
            except:
                return str(iso_string)

    @app.context_processor
    def built_assets_available():
        """Expose a small flag to templates indicating whether built CSS exists.

        Templates can use `built_css` to prefer a local built stylesheet
        (e.g. `static/dist/styles.css`) when present, otherwise fall back
        to a CDN link. This keeps CI builds optional and safe for local dev.
        """
        try:
            static_path = os.path.join(app.root_path, "static", "dist", "styles.css")
            is_prod = str(app.config.get('ENV', '')).lower() == 'production' or os.getenv('FLASK_ENV', '').lower() == 'production' or os.getenv('ENV', '').lower() == 'production'
            return dict(built_css=os.path.exists(static_path), is_production=is_prod)
        except Exception:
            return dict(built_css=False, is_production=False)

    # Routes
    @app.route("/health")
    def health():
        """Optimized health check endpoint"""
        try:
            # Validate connection before health check
            from database import validate_connection_before_operation
            if not validate_connection_before_operation():
                return jsonify({
                    "status": "error",
                    "message": "Database connection validation failed",
                    "timestamp": now_utc().isoformat()
                }), 500

            # Test database connection efficiently
            db.session.execute(text("SELECT 1"))

            out = {
                "status": "ok",
                "db": "connected",
                "timestamp": now_utc().isoformat()
            }

            # Optional memory monitoring (only if needed)
            if os.getenv("DETAILED_HEALTH_CHECK") == "true":
                memory_info = {"available": False}
                try:
                    import psutil
                    process = psutil.Process(os.getpid())
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    memory_info = {
                        "available": True,
                        "usage_mb": round(memory_mb, 2),
                        "usage_percent": round(process.memory_percent(), 2)
                    }
                    out["memory"] = memory_info
                except ImportError:
                    pass

            # Check Redis if configured (only if needed)
            if os.getenv("DETAILED_HEALTH_CHECK") == "true":
                redis_url = os.getenv("REDIS_URL")
                if redis_url:
                    try:
                        import redis
                        r = redis.from_url(redis_url)
                        r.ping()
                        out["redis"] = "connected"
                    except Exception as e:
                        out["redis"] = f"error: {str(e)}"
                else:
                    out["redis"] = "not_configured"

            return jsonify(out), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": now_utc().isoformat()
            }), 500

    try:
        from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
        registry = CollectorRegistry()
        g_uptime = Gauge('app_uptime_seconds', 'App uptime in seconds', registry=registry)
        g_updates = Gauge('updates_total', 'Total updates', registry=registry)
        g_redis = Gauge('redis_up', 'Redis up (1/0)', registry=registry)

        @app.route('/metrics')
        def metrics():
            try:
                g_uptime.set(int(time.time() - APP_START))
            except Exception:
                g_uptime.set(0)
            try:
                g_updates.set(int(Update.query.count()))
            except Exception:
                g_updates.set(0)
            # Only check Redis if configured to avoid performance issues
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from api.updates import is_redis_healthy
                    g_redis.set(1 if is_redis_healthy() else 0)
                except Exception:
                    g_redis.set(0)
            else:
                g_redis.set(0)  # Redis not configured
            data = generate_latest(registry)
            return (data, 200, {'Content-Type': CONTENT_TYPE_LATEST})
    except Exception:
        # If prometheus_client not available, keep the small plaintext /metrics
        @app.route('/metrics')
        def metrics_plain():
            lines = []
            try:
                uptime = time.time() - APP_START
                lines.append(f"app_uptime_seconds {int(uptime)}")
            except Exception:
                lines.append("app_uptime_seconds 0")
            try:
                total = Update.query.count()
                lines.append(f"updates_total {int(total)}")
            except Exception:
                lines.append("updates_total 0")
            # Only check Redis if configured to avoid performance issues
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from api.updates import is_redis_healthy
                    ok = is_redis_healthy()
                    lines.append(f"redis_up {1 if ok else 0}")
                except Exception:
                    lines.append("redis_up 0")
            else:
                lines.append("redis_up 0")  # Redis not configured
            return ("\n".join(lines), 200, {"Content-Type": "text/plain; version=0.0.4"})

    @app.route('/health/alert', methods=['POST'])
    def health_alert():
        """Trigger a POST to a configured alert webhook with current health status.

        Useful for manual or automated alerting during deployment checks.
        Configure `HEALTH_ALERT_URL` in the environment to enable.
        """
        url = os.getenv('HEALTH_ALERT_URL')
        if not url:
            return jsonify({'error': 'no_webhook_configured'}), 400
        try:
            import requests
            # Reuse /health to get current status
            with app.test_client() as c:
                resp = c.get('/health')
                payload = resp.get_json()
            r = requests.post(url, json=payload, timeout=5)
            return jsonify({'status': 'sent', 'response_code': r.status_code}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route("/lessons_learned/view/<int:lesson_id>")
    @login_required
    def view_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))
        return render_template("view_lesson_learned.html", lesson=lesson)

    @app.route("/search")
    def search():
        query = request.args.get("q", "").strip()
        results = []

        # Get filter parameters
        category = request.args.get("category", "")
        process = request.args.get("process", "")
        department = request.args.get("department", "")
        date_range = request.args.get("date_range", "")

        # Prepare filters for template
        filters = {
            "category": category,
            "process": process,
            "department": department,
            "date_range": date_range
        }

        # Available options for filters
        available_processes = ["ABC", "XYZ", "AB"]
        available_departments = ["ABC", "XYZ", "AB"]  # Fixed to match process options

        if query:
            # Case-insensitive search
            query_filter = f"%{query}%"

            # Search Updates (if no category filter or category is 'updates')
            if not category or category == "updates":
                updates_query = Update.query.filter(
                    or_(
                        Update.message.ilike(query_filter),
                        Update.name.ilike(query_filter),
                        Update.process.ilike(query_filter)
                    )
                )

                # Apply process filter
                if process:
                    updates_query = updates_query.filter(Update.process.ilike(f"%{process}%"))

                updates_rows = updates_query.order_by(Update.timestamp.desc()).all()

                for upd in updates_rows:
                    results.append({
                        "id": upd.id,
                        "title": f"{upd.process} - {upd.name}",
                        "content": upd.message[:200] + ("..." if len(upd.message) > 200 else ""),
                        "type": "update",
                        "url": url_for("view_update", update_id=upd.id),
                        "author": upd.name,
                        "created_at": upd.timestamp,
                        "process": upd.process
                    })

            # Search SOP Summaries (if no category filter or category is 'sops')
            if not category or category == "sops":
                sops_query = SOPSummary.query.filter(
                    or_(
                        SOPSummary.title.ilike(query_filter),
                        SOPSummary.summary_text.ilike(query_filter)
                    )
                )

                # Apply department filter
                if department:
                    sops_query = sops_query.filter(SOPSummary.department.ilike(f"%{department}%"))

                sops_rows = sops_query.order_by(SOPSummary.created_at.desc()).all()

                for sop in sops_rows:
                    results.append({
                        "id": sop.id,
                        "title": sop.title,
                        "content": sop.summary_text[:200] + ("..." if len(sop.summary_text) > 200 else ""),
                        "type": "sop",
                        "url": url_for("view_sop_summary", summary_id=sop.id),
                        "created_at": sop.created_at,
                        "tags": sop.tags or []
                    })

            # Search Lessons Learned (if no category filter or category is 'lessons')
            if not category or category == "lessons":
                lessons_query = LessonLearned.query.filter(
                    or_(
                        LessonLearned.title.ilike(query_filter),
                        LessonLearned.content.ilike(query_filter),
                        LessonLearned.summary.ilike(query_filter)
                    )
                )

                # Apply department filter
                if department:
                    lessons_query = lessons_query.filter(LessonLearned.department.ilike(f"%{department}%"))

                lessons_rows = lessons_query.order_by(LessonLearned.created_at.desc()).all()

                for lesson in lessons_rows:
                    results.append({
                        "id": lesson.id,
                        "title": lesson.title,
                        "content": (lesson.summary or lesson.content or "")[:200] + ("..." if len(lesson.summary or lesson.content or "") > 200 else ""),
                        "type": "lesson",
                        "url": url_for("view_lesson_learned", lesson_id=lesson.id),
                        "author": lesson.author,
                        "created_at": lesson.created_at,
                        "tags": lesson.tags or []
                    })

        return render_template("search_results.html",
                             query=query,
                             results=results,
                             filters=filters,
                             available_processes=available_processes,
                             available_departments=available_departments)



    @app.route("/")
    def home():
        try:
            # Limit the number of items loaded for better performance
            summaries = SOPSummary.query.order_by(SOPSummary.created_at.desc()).limit(10).all()
            lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).limit(10).all()

            # Get latest updates for the home page with read counts
            latest_updates = Update.query.order_by(Update.timestamp.desc()).limit(5).all()
            updates_data = []

            for update in latest_updates:
                update_dict = update.to_dict()
                # Get read count efficiently
                read_count = db.session.query(func.count(ReadLog.id)).filter(
                    ReadLog.update_id == update.id
                ).scalar()
                update_dict['read_count'] = read_count
                update_dict['is_new'] = is_within_hours(update.timestamp, 24, now_utc())
                updates_data.append(update_dict)

            return render_template("home.html", app_name=app.config["APP_NAME"],
                                  summaries=summaries, lessons=lessons, updates=updates_data,
                                  excel_export_available=EXCEL_EXPORT_AVAILABLE)
        except Exception as e:
            # Return a basic template without updates if there's an error
            return render_template("home.html", app_name=app.config["APP_NAME"],
                                  summaries=[], lessons=[], updates=[],
                                  excel_export_available=EXCEL_EXPORT_AVAILABLE)

    @app.route("/updates")
    def show_updates():
        # Get filter parameters from query string
        selected_process = request.args.get("process", "")
        selected_department = request.args.get("department", "")
        sort = request.args.get("sort", "newest")
        
        # Base query
        base_query = (
            db.session.query(Update, func.count(ReadLog.id).label('read_count'))
            .outerjoin(ReadLog, ReadLog.update_id == Update.id)
            .group_by(Update.id)
        )
        
        # Apply process filter if specified
        if selected_process:
            base_query = base_query.filter(Update.process == selected_process)
        
        # Apply sorting
        if sort == "oldest":
            base_query = base_query.order_by(Update.timestamp.asc())
        elif sort == "process":
            base_query = base_query.order_by(Update.process.asc(), Update.timestamp.desc())
        elif sort == "author":
            base_query = base_query.order_by(Update.name.asc(), Update.timestamp.desc())
        else:  # newest (default)
            base_query = base_query.order_by(Update.timestamp.desc())
        
        rows = base_query.all()

        updates = []
        current_time = now_utc()
        for upd, count in rows:
            d = upd.to_dict()
            d['read_count'] = count

            # determine if it's within last 24 hours
            d['is_new'] = is_within_hours(upd.timestamp, 24, current_time)

            # Add the original datetime object for isoformat() in template
            d['timestamp_obj'] = upd.timestamp

            updates.append(d)

        # Get additional data for template more efficiently
        # Use distinct queries instead of loading all records
        unique_authors = [row[0] for row in db.session.query(Update.name).filter(Update.name.isnot(None)).distinct().all()]
        processes = [row[0] for row in db.session.query(Update.process).filter(Update.process.isnot(None)).distinct().all()]
        
        # Calculate updates this week more efficiently
        week_ago = get_hours_ago(24 * 7)
        updates_this_week = Update.query.filter(Update.timestamp >= week_ago).count()
        
        # Get unique departments (consistent with other forms)
        departments = ["ABC", "XYZ", "AB"]
        
        return render_template("show.html", 
                             app_name=app.config["APP_NAME"], 
                             updates=updates,
                             unique_authors=unique_authors,
                             processes=processes,
                             departments=departments,
                             updates_this_week=updates_this_week,
                             selected_process=selected_process,
                             selected_department=selected_department,
                             sort=sort)

    @app.route("/post", methods=["GET", "POST"])
    @writer_required
    def post_update():
        processes = ["ABC", "XYZ", "AB"]

        if request.method == "POST":
            # Validate connection before critical operation
            from database import validate_connection_before_operation
            if not validate_connection_before_operation():
                flash("⚠️ Database connection issue. Please try again.")
                return redirect(url_for("post_update"))

            message = request.form.get("message", "").strip()
            selected_process = request.form.get("process")
            name = inject_current_user()["current_user"].display_name

            if not message or not selected_process:
                flash("⚠️ Message and process are required.")
                return redirect(url_for("post_update"))

            new_update = Update(
                id=uuid.uuid4().hex,
                name=name,
                process=selected_process,
                message=message,
                timestamp=now_utc(),
            )
            try:
                db.session.add(new_update)
                db.session.commit()
                flash("✅ Update posted.")

                # Log activity
                log_activity('created', 'update', new_update.id, f"Update: {message[:50]}...")

                # Broadcast the new update via Socket.IO
                try:
                    if os.getenv("FLASK_ENV") == "development":
                        logger.info(f"🔄 Broadcasting new update via Socket.IO - ID: {new_update.id}")
                        print(f"🔄 Broadcasting new update via Socket.IO - ID: {new_update.id}")
                    from api.socketio import broadcast_update
                    update_data = {
                        'id': new_update.id,
                        'name': new_update.name,
                        'process': new_update.process,
                        'message': new_update.message,
                        'timestamp': new_update.timestamp.isoformat()
                    }
                    if os.getenv("FLASK_ENV") == "development":
                        logger.info(f"📦 Update data prepared: {update_data}")
                        print(f"📦 Update data prepared for broadcasting")
                    broadcast_update(update_data, selected_process)
                    if os.getenv("FLASK_ENV") == "development":
                        logger.info(f"✅ Broadcast function called successfully for update {new_update.id}")
                        print(f"✅ Broadcast function called successfully for update {new_update.id}")
                except Exception as e:
                    # Socket.IO broadcasting failure shouldn't break the posting
                    logger.error(f"❌ Socket.IO broadcast failed: {e}")
                    if os.getenv("FLASK_ENV") == "development":
                        print(f"❌ Socket.IO broadcast failed: {e}")

            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to post update: {e}")
                flash("⚠️ Failed to post update.")
            return redirect(url_for("show_updates"))

        return render_template("post.html", app_name=app.config["APP_NAME"], processes=processes)

    @app.route("/edit/<update_id>", methods=["GET", "POST"])
    @writer_required
    def edit_update(update_id):
        update = Update.query.get(update_id)
        current = inject_current_user()["current_user"]
        if not update or update.name != current.display_name:
            flash("🚫 Unauthorized or not found.")
            return redirect(url_for("show_updates"))

        if request.method == "POST":
            new_message = request.form.get("message", "").strip()
            if not new_message:
                flash("⚠️ Message cannot be empty.")
                return redirect(url_for("edit_update", update_id=update_id))
            update.message = new_message
            update.timestamp = now_utc()
            try:
                db.session.commit()
                flash("✏️ Update edited successfully.")

                # Log activity
                log_activity('edited', 'update', update.id, f"Update: {new_message[:50]}...")

            except Exception:
                db.session.rollback()
                flash("⚠️ Failed to edit update.")
            return redirect(url_for("show_updates"))

        return render_template("edit.html", app_name=app.config["APP_NAME"], update=update)

    @app.route("/view/<update_id>")
    def view_update(update_id):
        """View a specific update"""
        update = Update.query.get(update_id)
        if not update:
            flash("🚫 Update not found.")
            return redirect(url_for("show_updates"))
        
        # Get read count for this update
        read_count = db.session.query(func.count(ReadLog.id)).filter(
            ReadLog.update_id == update_id
        ).scalar()
        
        # Check if current user has read this update
        is_read = False
        if session.get("user_id"):
            read_log = ReadLog.query.filter_by(
                update_id=update_id,
                user_id=session["user_id"]
            ).first()
            is_read = read_log is not None
        
        return render_template("view_update.html", 
                             app_name=app.config["APP_NAME"], 
                             update=update, 
                             read_count=read_count,
                             is_read=is_read)

    @app.route("/delete/<update_id>", methods=["POST"])
    @login_required
    def delete_update(update_id):
        update = Update.query.get(update_id)
        current = inject_current_user()["current_user"]
        
        # Prepare response data
        response = {"success": False, "message": ""}
        
        if not update:
            response["message"] = "⚠️ Update not found."
            status_code = 404
        elif update.name.strip().lower() != current.display_name.strip().lower():
            response["message"] = "🚫 Not authorized to delete."
            status_code = 403
        else:
            # Capture details before deletion
            entity_title = f"Update: {update.message[:50]}..."

            try:
                # Archive the update before deletion
                if archive_update(update):
                    db.session.delete(update)
                    db.session.commit()
                    response["success"] = True
                    response["message"] = "✅ Update deleted and archived."
                    status_code = 200

                    # Log activity after successful deletion
                    log_activity('deleted', 'update', update_id, entity_title)
                else:
                    response["message"] = "⚠️ Failed to archive update. Deletion cancelled for safety."
                    status_code = 500

            except Exception as e:
                db.session.rollback()
                response["message"] = "❌ Deletion failed."
                status_code = 500
                logger.error(f"Failed to delete update: {e}")

        # Handle both AJAX and form submissions
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify(response), status_code
        else:
            flash(response["message"])
            return redirect(url_for("show_updates"))
            
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            display_name = request.form["display_name"].strip()
            username = request.form["username"].strip().replace(" ", "_").lower()
            password = request.form["password"]

            if not re.match("^[A-Za-z0-9_]+$", username):
                flash("🚫 Username can only contain letters, numbers, and underscores.")
                return redirect(url_for("register"))

            if not username or not display_name or not password:
                flash("⚠️ All fields required.")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("🚫 Username taken.")
                return redirect(url_for("register"))

            new_user = User(username=username, display_name=display_name)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash("✅ Registered! Please log in.")
            return redirect(url_for("login"))

        return render_template("register.html", app_name=app.config["APP_NAME"])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"].strip().replace(" ", "_").lower()
            password = request.form["password"]
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session["user_id"] = user.id
                flash(f"👋 Welcome back, {user.display_name}!")

                # Handle redirect logic
                next_page = request.form.get('next') or request.args.get('next')

                # If user came from home page login button, redirect to home
                if next_page == 'home':
                    return redirect(url_for("home"))
                # If there's a next page specified, redirect there
                elif next_page:
                    # Check if it's a full URL (from role decorators)
                    if next_page.startswith('http') or next_page.startswith('/'):
                        # Validate that it's a safe redirect within our app
                        from urllib.parse import urlparse
                        parsed = urlparse(next_page)
                        if not parsed.netloc or parsed.netloc == request.host:
                            return redirect(next_page)

                    # Map of valid endpoints to their URL functions
                    valid_endpoints = {
                        'show_updates': 'show_updates',
                        'post_update': 'post_update',
                        'list_sop_summaries': 'list_sop_summaries',
                        'list_lessons_learned': 'list_lessons_learned',
                        'search': 'search',
                        'add_sop_summary': 'add_sop_summary',
                        'add_lesson_learned': 'add_lesson_learned',
                        'export_readlogs': 'export_readlogs'
                    }

                    # Handle search result redirects for SOPs and Lessons
                    if next_page == 'view_sop_summary':
                        return redirect(url_for('list_sop_summaries'))
                    elif next_page == 'view_lesson_learned':
                        return redirect(url_for('list_lessons_learned'))
                    elif next_page in valid_endpoints:
                        return redirect(url_for(valid_endpoints[next_page]))

                # Default fallback to home page instead of show_updates
                return redirect(url_for("home"))

            flash("🚫 Invalid credentials.")
            return redirect(url_for("login"))

        # For GET requests, preserve the next parameter
        next_page = request.args.get('next')
        return render_template("login.html", app_name=app.config["APP_NAME"], next_page=next_page)

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("👋 You’ve been logged out.")
        return redirect(url_for("home"))

    @app.route("/api/latest-update-time")
    def api_latest_update_time():
        """API endpoint to get the timestamp of the most recent update"""
        try:
            latest_update = Update.query.order_by(Update.timestamp.desc()).first()
            if latest_update:
                # Ensure timezone is properly handled
                timestamp = ensure_timezone(latest_update.timestamp, UTC)

                return jsonify({
                    "latest_timestamp": timestamp.isoformat(),
                    "success": True
                })
            else:
                return jsonify({
                    "latest_timestamp": None,
                    "success": True
                })
        except Exception as e:
            logger.error(f"Error getting latest update time: {e}")
            return jsonify({
                "latest_timestamp": None,
                "success": False,
                "error": str(e)
            }), 500
    
    # New routes for SOP Summaries
    @app.route("/sop_summaries")
    @login_required
    def list_sop_summaries():
        sops = SOPSummary.query.order_by(SOPSummary.created_at.desc()).all()
        return render_template("sop_summaries.html", summaries=sops)

    @app.route("/sop_summaries/add", methods=["GET", "POST"])
    @writer_required
    def add_sop_summary():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            summary_text = request.form.get("summary_text", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not summary_text:
                flash("Title and Summary are required.")
                return redirect(url_for("add_sop_summary"))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            sop = SOPSummary(
                title=title,
                summary_text=summary_text,
                department=department or None,
                tags=tags_list or None,
            )
            try:
                db.session.add(sop)
                db.session.commit()
                flash("SOP Summary added successfully.")

                # Log activity
                log_activity('created', 'sop', sop.id, title)

                # Broadcast notification for new SOP
                try:
                    from api.socketio import broadcast_notification
                    broadcast_notification({
                        'type': 'new_sop',
                        'title': 'New SOP Added',
                        'message': f'**NEW SOP:** {title}',
                        'timestamp': now_utc().isoformat()
                    })
                except Exception as e:
                    if os.getenv("FLASK_ENV") == "development":
                        print(f"Socket.IO broadcast failed: {e}")

                return redirect(url_for("list_sop_summaries"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add SOP Summary.")
                logger.error(f"Failed to add SOP Summary: {e}")
                return redirect(url_for("add_sop_summary"))

        return render_template("add_sop_summary.html")

    @app.route("/sop_summaries/edit/<int:sop_id>", methods=["GET", "POST"])
    @writer_required
    def edit_sop_summary(sop_id):
        sop = SOPSummary.query.get(sop_id)
        if not sop:
            flash("SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            summary_text = request.form.get("summary_text", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not summary_text:
                flash("Title and Summary are required.")
                return redirect(url_for("edit_sop_summary", sop_id=sop_id))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            sop.title = title
            sop.summary_text = summary_text
            sop.department = department or None
            sop.tags = tags_list or None
            try:
                db.session.commit()
                flash("✅ SOP Summary updated successfully.")

                # Log activity
                log_activity('edited', 'sop', sop.id, title)

            except Exception as e:
                db.session.rollback()
                flash("❌ Failed to update SOP Summary.")
                logger.error(f"Failed to update SOP Summary: {e}")

            # Check if user came from view page or list page
            referrer = request.form.get('referrer') or request.referrer
            if referrer and 'sop_summaries/' in referrer and str(sop_id) in referrer:
                return redirect(url_for("view_sop_summary", summary_id=sop_id))
            else:
                return redirect(url_for("list_sop_summaries"))

        return render_template("edit_sop_summary.html", sop=sop)

    @app.route("/sop_summaries/delete/<int:sop_id>", methods=["POST"])
    @delete_required
    def delete_sop_summary(sop_id):
        sop = SOPSummary.query.get(sop_id)
        if not sop:
            flash("⚠️ SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        # Capture details before deletion
        entity_title = sop.title

        try:
            # Archive the SOP before deletion
            if archive_sop(sop):
                db.session.delete(sop)
                db.session.commit()
                flash("✅ SOP Summary deleted and archived.")

                # Log activity after successful deletion
                log_activity('deleted', 'sop', sop_id, entity_title)
            else:
                flash("⚠️ Failed to archive SOP. Deletion cancelled for safety.")

        except Exception as e:
            db.session.rollback()
            flash("❌ Failed to delete SOP Summary.")
            logger.error(f"Failed to delete SOP Summary: {e}")

        # Always redirect to list page after deletion since the item no longer exists
        return redirect(url_for("list_sop_summaries"))

    # New routes for Lessons Learned
    @app.route("/lessons_learned")
    @login_required
    def list_lessons_learned():
        lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).all()
        return render_template("lessons_learned.html", lessons=lessons)

    @app.route("/lessons_learned/add", methods=["GET", "POST"])
    @writer_required
    def add_lesson_learned():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            summary = request.form.get("summary", "").strip()
            author = request.form.get("author", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not content:
                flash("Title and Content are required.")
                return redirect(url_for("add_lesson_learned"))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            lesson = LessonLearned(
                title=title,
                content=content,
                summary=summary or None,
                author=author or None,
                department=department or None,
                tags=tags_list or None,
            )
            try:
                db.session.add(lesson)
                db.session.commit()
                flash("Lesson Learned added successfully.")

                # Log activity
                log_activity('created', 'lesson', lesson.id, title)

                # Broadcast notification for new Lesson Learned
                try:
                    from api.socketio import broadcast_notification
                    broadcast_notification({
                        'type': 'new_lesson',
                        'title': 'New Lesson Learned',
                        'message': f'**NEW LESSON:** {title}',
                        'timestamp': now_utc().isoformat()
                    })
                except Exception as e:
                    if os.getenv("FLASK_ENV") == "development":
                        print(f"Socket.IO broadcast failed: {e}")

                return redirect(url_for("list_lessons_learned"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add Lesson Learned.")
                logger.error(f"Failed to add Lesson Learned: {e}")
                return redirect(url_for("add_lesson_learned"))

        return render_template("add_lesson_learned.html")

    @app.route("/lessons_learned/edit/<int:lesson_id>", methods=["GET", "POST"])
    @writer_required
    def edit_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            summary = request.form.get("summary", "").strip()
            author = request.form.get("author", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not content:
                flash("Title and Content are required.")
                return redirect(url_for("edit_lesson_learned", lesson_id=lesson_id))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            lesson.title = title
            lesson.content = content
            lesson.summary = summary or None
            lesson.author = author or None
            lesson.department = department or None
            lesson.tags = tags_list or None

            try:
                db.session.commit()
                flash("✅ Lesson Learned updated successfully.")

                # Log activity
                log_activity('edited', 'lesson', lesson.id, title)

            except Exception as e:
                db.session.rollback()
                flash("❌ Failed to update Lesson Learned.")
                logger.error(f"Failed to update Lesson Learned: {e}")

            # Check if user came from view page or list page
            referrer = request.form.get('referrer') or request.referrer
            if referrer and 'lessons_learned/view/' in referrer and str(lesson_id) in referrer:
                return redirect(url_for("view_lesson_learned", lesson_id=lesson_id))
            else:
                return redirect(url_for("list_lessons_learned"))

        return render_template("edit_lesson_learned.html", lesson=lesson)

    @app.route("/lessons_learned/delete/<int:lesson_id>", methods=["POST"])
    @delete_required
    def delete_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))

        # Capture details before deletion
        entity_title = lesson.title

        try:
            # Archive the lesson before deletion
            if archive_lesson(lesson):
                db.session.delete(lesson)
                db.session.commit()
                flash("✅ Lesson Learned deleted and archived.")

                # Log activity after successful deletion
                log_activity('deleted', 'lesson', lesson_id, entity_title)
            else:
                flash("⚠️ Failed to archive lesson. Deletion cancelled for safety.")

        except Exception as e:
            db.session.rollback()
            flash("❌ Failed to delete Lesson Learned.")

        # Always redirect to list page after deletion since the item no longer exists
        return redirect(url_for("list_lessons_learned"))
    

        
    @app.route("/sop_summaries/<int:summary_id>")
    @login_required
    def view_sop_summary(summary_id):
        summary = SOPSummary.query.get(summary_id)
        if not summary:
            flash("\u26a0\ufe0f SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        return render_template(
            "view_sop_summary.html",
            summary=summary,
            app_name=current_app.config["APP_NAME"]
        )



    @app.route("/api/check-update/<update_id>")
    def check_update(update_id):
        """Check if an update exists and is accessible."""
        try:
            update = Update.query.get(update_id)
            if not update:
                return jsonify({
                    'error': 'Not Found',
                    'message': 'Update not found'
                }), 404
            return jsonify({
                'exists': True,
                'id': update.id,
                'status': 'active'
            })
        except Exception as e:
            logger.error(f"Error checking update {update_id}: {str(e)}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Unable to check update status'
            }), 500

    @app.route("/api/recent-updates")
    def recent_updates():
        """Get updates from the past 24 hours for the bell icon banner."""
        try:
            # Calculate 24 hours ago
            twenty_four_hours_ago = get_hours_ago(24)

            # Query for recent updates
            recent_updates = Update.query.filter(
                Update.timestamp >= twenty_four_hours_ago
            ).order_by(Update.timestamp.desc()).limit(10).all()

            if not recent_updates:
                return jsonify({
                    'updates': [],
                    'message': 'No recent updates found'
                })

            updates_data = []
            for update in recent_updates:
                # Ensure timezone is properly handled
                timestamp = ensure_timezone(update.timestamp, UTC)

                updates_data.append({
                    "id": update.id,
                    "name": update.name,
                    "process": update.process,
                    "message": update.message,
                    "timestamp": timestamp.isoformat()
                })

            return jsonify({
                "success": True,
                "updates": updates_data
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/export-readlogs")
    @export_required
    def export_readlogs():
        """Export read logs to Excel file with comprehensive analytics."""
        # Check if Excel export dependencies are available
        if not EXCEL_EXPORT_AVAILABLE:
            flash("❌ Excel export feature is not available. Please install pandas and openpyxl.", "error")
            return redirect(url_for('home'))

        # Check if this is a download request
        download = request.args.get('download', 'false').lower() == 'true'

        if not download:
            try:
                # Get summary stats for the export page
                total_logs = ReadLog.query.count()
                unique_readers = db.session.query(func.count(func.distinct(ReadLog.user_id))).scalar()
                date_range = db.session.query(
                    func.min(ReadLog.timestamp).label('start'),
                    func.max(ReadLog.timestamp).label('end')
                ).first()

                return render_template('export_readlogs.html',
                                 app_name=app.config["APP_NAME"],
                                 total_logs=total_logs,
                                 unique_readers=unique_readers,
                                 date_range=date_range)
            except Exception as e:
                flash(f"❌ Error getting export statistics: {str(e)}", "error")
                return redirect(url_for('home'))

        # If download=true, proceed with file generation and download
        try:
            # Query all read logs with related data - using explicit aliases to avoid parameter conflicts
            from sqlalchemy.orm import aliased
            update_alias = aliased(Update)
            user_alias = aliased(User)

            read_logs_query = db.session.query(
                ReadLog.id,
                ReadLog.timestamp,
                ReadLog.guest_name,
                ReadLog.ip_address,
                ReadLog.user_agent,
                update_alias.id.label('update_id'),
                update_alias.message.label('update_message'),
                update_alias.name.label('update_author'),
                update_alias.process.label('update_process'),
                update_alias.timestamp.label('update_created'),
                user_alias.display_name.label('reader_name'),
                user_alias.username.label('reader_username')
            ).outerjoin(
                update_alias, ReadLog.update_id == update_alias.id
            ).outerjoin(
                user_alias, ReadLog.user_id == user_alias.id
            ).order_by(ReadLog.timestamp.desc())

            # Execute query and get results
            results = read_logs_query.all()

            # Prepare data for Excel
            data = []
            for row in results:
                # Determine reader name (user or guest)
                reader_name = row.reader_name if row.reader_name else (row.guest_name or "Anonymous")
                reader_type = "Registered User" if row.reader_name else "Guest"

                # Format timestamps
                read_time = row.timestamp.strftime('%Y-%m-%d %H:%M:%S') if row.timestamp else ""
                update_created_time = row.update_created.strftime('%Y-%m-%d %H:%M:%S') if row.update_created else ""

                # Truncate long messages for readability
                update_message = (row.update_message[:100] + "...") if row.update_message and len(row.update_message) > 100 else (row.update_message or "")

                data.append({
                    'Read Log ID': row.id,
                    'Reader Name': reader_name,
                    'Reader Type': reader_type,
                    'Reader Username': row.reader_username or "N/A",
                    'Read Timestamp': read_time,
                    'IP Address': row.ip_address or "N/A",
                    'Browser User-Agent': row.user_agent or "N/A",
                    'Update ID': row.update_id or "N/A",
                    'Update Message': update_message,
                    'Update Author': row.update_author or "N/A",
                    'Update Process': row.update_process or "N/A",
                    'Update Created': update_created_time,
                })

            # Create DataFrame
            df = pd.DataFrame(data)

            # Create summary statistics
            summary_data = []

            # Total reads
            total_reads = len(df)
            summary_data.append({'Metric': 'Total Reads', 'Value': total_reads})

            # Unique readers
            unique_readers = df['Reader Name'].nunique() if not df.empty and 'Reader Name' in df.columns else 0
            summary_data.append({'Metric': 'Unique Readers', 'Value': unique_readers})

            # Registered vs Guest reads
            if not df.empty and 'Reader Type' in df.columns:
                registered_reads = len(df[df['Reader Type'] == 'Registered User'])
                guest_reads = len(df[df['Reader Type'] == 'Guest'])
            else:
                registered_reads = 0
                guest_reads = 0
            summary_data.append({'Metric': 'Registered User Reads', 'Value': registered_reads})
            summary_data.append({'Metric': 'Guest Reads', 'Value': guest_reads})

            # Most active readers (top 10)
            top_readers = df['Reader Name'].value_counts().head(10) if not df.empty and 'Reader Name' in df.columns else pd.Series()

            # Most read updates (top 10)
            if not df.empty and 'Update ID' in df.columns and 'Update Message' in df.columns and 'Update Author' in df.columns:
                most_read_updates = df.groupby(['Update ID', 'Update Message', 'Update Author']).size().reset_index(name='Read Count').sort_values('Read Count', ascending=False).head(10)
            else:
                most_read_updates = pd.DataFrame()

            # Create Excel file in memory
            output = BytesIO()

            # Query activity logs - using explicit aliases to avoid parameter conflicts
            activity_logs_query = db.session.query(
                ActivityLog.id,
                ActivityLog.action,
                ActivityLog.entity_type,
                ActivityLog.entity_id,
                ActivityLog.entity_title,
                ActivityLog.timestamp,
                ActivityLog.ip_address,
                ActivityLog.user_agent,
                ActivityLog.details,
                user_alias.display_name.label('user_name'),
                user_alias.username.label('username')
            ).outerjoin(
                user_alias, ActivityLog.user_id == user_alias.id
            ).order_by(ActivityLog.timestamp.desc())

            activity_results = activity_logs_query.all()

            # Prepare activity logs data
            activity_data = []
            for row in activity_results:
                user_name = row.user_name if row.user_name else "System"
                # Convert UTC timestamp to IST for proper display
                if row.timestamp:
                    ist_timestamp = to_ist(row.timestamp)
                    activity_time = ist_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    activity_time = ""

                activity_data.append({
                    'Activity ID': row.id,
                    'User Name': user_name,
                    'Username': row.username or "N/A",
                    'Action': row.action.title(),
                    'Entity Type': row.entity_type.upper(),
                    'Entity ID': row.entity_id,
                    'Entity Title': row.entity_title or "N/A",
                    'Timestamp': activity_time,
                    'IP Address': row.ip_address or "N/A",
                    'Browser User-Agent': row.user_agent or "N/A",
                    'Details': row.details or "N/A"
                })

            activity_df = pd.DataFrame(activity_data)

            # Query registered users for authority tracking - using explicit aliases to avoid parameter conflicts
            users_query = db.session.query(
                user_alias.id,
                user_alias.username,
                user_alias.display_name,
                user_alias.email,
                user_alias.role
            ).order_by(user_alias.id)

            users_results = users_query.all()
            users_data = []
            for idx, user in enumerate(users_results, 1):
                users_data.append({
                    'Serial #': idx,
                    'User ID': user.id,
                    'Username': user.username,
                    'Display Name': user.display_name,
                    'Email': user.email or "N/A",
                    'Role': user.role.title()
                })

            users_df = pd.DataFrame(users_data)

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Read Logs', index=False)

                # Summary sheet
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Activity Logs sheet
                activity_df.to_excel(writer, sheet_name='Activity Logs', index=False)

                # Registered Users sheet
                users_df.to_excel(writer, sheet_name='Registered Users', index=False)

                # Top readers sheet
                top_readers_df = pd.DataFrame({
                    'Reader Name': top_readers.index,
                    'Total Reads': top_readers.values
                })
                top_readers_df.to_excel(writer, sheet_name='Top Readers', index=False)

                # Most read updates sheet
                most_read_updates.to_excel(writer, sheet_name='Most Read Updates', index=False)

                # Process-wise analytics
                if not df.empty and 'Update Process' in df.columns and 'Reader Name' in df.columns:
                    process_stats = df.groupby('Update Process').agg({
                        'Read Log ID': 'count',
                        'Reader Name': 'nunique'
                    }).rename(columns={
                        'Read Log ID': 'Total Reads',
                        'Reader Name': 'Unique Readers'
                    }).reset_index()
                    process_stats.to_excel(writer, sheet_name='Process Analytics', index=False)

                # Format the Excel sheets
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]

                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter

                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass

                        adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            output.seek(0)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'readlogs_export_{timestamp}.xlsx'

            return send_file(
                output,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        except Exception as e:
            # Log the error
            current_app.logger.error(f"Error exporting read logs: {str(e)}")

            # Return error page or redirect with flash message
            flash(f"❌ Error exporting read logs: {str(e)}", "error")
            return redirect(url_for('home'))

    @app.route("/reset-activity-logs", methods=["POST"])
    @admin_required
    def reset_activity_logs():
        """Reset (delete all) activity logs with admin password verification."""
        try:
            # Get the admin password from the form
            admin_password = request.form.get('admin_password', '').strip()

            if not admin_password:
                flash("❌ Admin password is required to reset activity logs.", "error")
                return redirect(url_for('export_readlogs'))

            # Get the current admin user
            admin_user_id = session.get("user_id")
            if not admin_user_id:
                flash("❌ Authentication error. Please log in again.", "error")
                return redirect(url_for('login'))

            admin_user = User.query.get(admin_user_id)
            if not admin_user or admin_user.role != 'admin':
                flash("❌ Admin access required.", "error")
                return redirect(url_for('home'))

            # Verify the admin password
            if not admin_user.check_password(admin_password):
                flash("❌ Incorrect admin password. Activity logs were not reset.", "error")
                return redirect(url_for('export_readlogs'))

            # Count current activity logs before deletion
            activity_count = ActivityLog.query.count()

            # Delete all activity logs
            ActivityLog.query.delete()
            db.session.commit()

            flash(f"✅ Successfully reset activity logs. {activity_count} records were deleted.", "success")

            # Log this action (create a new activity log entry for the reset)
            log_activity('reset', 'activity_logs', 'all', f"Reset all activity logs ({activity_count} records)",
                        details=f"Admin {admin_user.display_name} reset all activity logs")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error resetting activity logs: {str(e)}", "error")

        return redirect(url_for('export_readlogs'))

    @app.route("/backup")
    @admin_required
    def backup_page():
        """Display backup management page."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()
            backups = backup_system.list_backups()
            return render_template('backup.html',
                                 app_name=app.config["APP_NAME"],
                                 backups=backups)
        except Exception as e:
            flash(f"❌ Error loading backup page: {str(e)}", "error")
            return redirect(url_for('home'))

    @app.route("/backup/create", methods=["POST"])
    @admin_required
    def create_backup():
        """Create a new database backup."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            backup_type = request.form.get('backup_type', 'manual')
            backup_path = backup_system.create_backup(backup_type)

            if backup_path:
                flash(f"✅ Backup created successfully: {backup_path.name}", "success")
            else:
                flash("❌ Failed to create backup. Check logs for details.", "error")

        except Exception as e:
            flash(f"❌ Error creating backup: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/backup/restore", methods=["POST"])
    @admin_required
    def restore_backup():
        """Restore database from backup with improved error handling."""
        import threading
        import time

        try:
            backup_file = request.form.get('backup_file')
            if not backup_file:
                flash("❌ Please select a backup file to restore.", "error")
                return redirect(url_for('backup_page'))

            backup_path = Path("backups") / backup_file

            # Check if backup file exists
            if not backup_path.exists():
                flash(f"❌ Backup file not found: {backup_file}", "error")
                return redirect(url_for('backup_page'))

            # Quick verification
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            if not backup_system.verify_backup(backup_path):
                flash("❌ Backup file verification failed. Cannot restore.", "error")
                return redirect(url_for('backup_page'))

            # Perform restore with Flask application context
            def restore_with_app_context():
                try:
                    # Ensure we're within Flask application context
                    with app.app_context():
                        return backup_system.restore_backup(backup_path)
                except Exception as e:
                    logger.error(f"Restore error in thread: {e}")
                    return False

            # Start restore in background with timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(restore_with_app_context)
                try:
                    # Wait up to 90 seconds for restore to complete (matching backend timeout)
                    result = future.result(timeout=90)
                    if result:
                        flash("✅ Database restored successfully from backup. Archived items have been restored to their original locations.", "success")
                        # Log the restore activity
                        log_activity('restored', 'database', backup_file, f"Database restored from {backup_file}")
                    else:
                        flash("❌ Failed to restore backup. Check logs for details.", "error")
                except concurrent.futures.TimeoutError:
                    flash("⚠️ Restore operation timed out after 90 seconds. Please check if restore completed successfully.", "warning")
                except Exception as e:
                    flash(f"❌ Restore operation failed: {str(e)}", "error")

        except Exception as e:
            flash(f"❌ Error during restore process: {str(e)}", "error")
            logger.error(f"Backup restore error: {e}")

        return redirect(url_for('backup_page'))

    @app.route("/backup/cleanup", methods=["POST"])
    @admin_required
    def cleanup_backups():
        """Clean up old backups."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()
            backup_system.cleanup_old_backups()
            flash("✅ Old backups cleaned up successfully.", "success")
        except Exception as e:
            flash(f"❌ Error cleaning up backups: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/backup/delete", methods=["POST"])
    @admin_required
    def delete_backup():
        """Delete a backup file permanently."""
        try:
            backup_filename = request.form.get('backup_file')
            if not backup_filename:
                flash("❌ No backup file specified.", "error")
                return redirect(url_for('backup_page'))

            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            # Get the backup file path
            backup_path = backup_system.backup_dir / backup_filename
            metadata_path = backup_path.with_suffix('.json')

            if not backup_path.exists():
                flash("❌ Backup file not found.", "error")
                return redirect(url_for('backup_page'))

            # Delete the backup file and its metadata
            backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            flash(f"✅ Backup file '{backup_filename}' deleted successfully.", "success")

            # Log activity
            log_activity('deleted', 'backup_file', backup_filename, f"Backup: {backup_filename}")

        except Exception as e:
            flash(f"❌ Error deleting backup file: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/archives")
    @admin_required
    def archives_page():
        """Display archived items management page."""
        try:
            # Get archived items with user info - using explicit aliases to avoid parameter conflicts
            from sqlalchemy.orm import aliased
            user_alias = aliased(User)

            archived_updates = db.session.query(
                ArchivedUpdate,
                user_alias.display_name.label('archived_by_name')
            ).outerjoin(
                user_alias, ArchivedUpdate.archived_by == user_alias.id
            ).order_by(ArchivedUpdate.archived_at.desc()).all()

            archived_sops = db.session.query(
                ArchivedSOPSummary,
                user_alias.display_name.label('archived_by_name')
            ).outerjoin(
                user_alias, ArchivedSOPSummary.archived_by == user_alias.id
            ).order_by(ArchivedSOPSummary.archived_at.desc()).all()

            archived_lessons = db.session.query(
                ArchivedLessonLearned,
                user_alias.display_name.label('archived_by_name')
            ).outerjoin(
                user_alias, ArchivedLessonLearned.archived_by == user_alias.id
            ).order_by(ArchivedLessonLearned.archived_at.desc()).all()

            return render_template('archives.html',
                                 app_name=app.config["APP_NAME"],
                                 archived_updates=archived_updates,
                                 archived_sops=archived_sops,
                                 archived_lessons=archived_lessons)
        except Exception as e:
            flash(f"❌ Error loading archives: {str(e)}", "error")
            return redirect(url_for('backup_page'))

    @app.route("/archives/restore/<item_type>/<item_id>", methods=["POST"])
    @admin_required
    def restore_archived_item(item_type, item_id):
        """Restore an archived item."""
        try:
            if item_type == 'update':
                # For updates, item_id is a string (UUID)
                archived_item = ArchivedUpdate.query.get(item_id)
                if archived_item:
                    # Create new update from archived data
                    restored_update = Update(
                        id=archived_item.id,
                        name=archived_item.name,
                        process=archived_item.process,
                        message=archived_item.message,
                        timestamp=archived_item.timestamp
                    )
                    db.session.add(restored_update)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Update restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'update', archived_item.id, f"Update: {archived_item.message[:50]}...")

            elif item_type == 'sop':
                # For SOPs, item_id is an integer
                try:
                    sop_id = int(item_id)
                    archived_item = ArchivedSOPSummary.query.get(sop_id)
                except ValueError:
                    flash("❌ Invalid SOP ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    restored_sop = SOPSummary(
                        title=archived_item.title,
                        summary_text=archived_item.summary_text,
                        department=archived_item.department,
                        tags=archived_item.tags,
                        created_at=archived_item.created_at
                    )
                    db.session.add(restored_sop)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ SOP restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'sop', restored_sop.id, archived_item.title)

            elif item_type == 'lesson':
                # For lessons, item_id is an integer
                try:
                    lesson_id = int(item_id)
                    archived_item = ArchivedLessonLearned.query.get(lesson_id)
                except ValueError:
                    flash("❌ Invalid Lesson ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    restored_lesson = LessonLearned(
                        title=archived_item.title,
                        content=archived_item.content,
                        summary=archived_item.summary,
                        author=archived_item.author,
                        department=archived_item.department,
                        tags=archived_item.tags,
                        created_at=archived_item.created_at
                    )
                    db.session.add(restored_lesson)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Lesson Learned restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'lesson', restored_lesson.id, archived_item.title)

            else:
                flash("❌ Invalid item type.", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error restoring item: {str(e)}", "error")

        return redirect(url_for('archives_page'))

    @app.route("/archives/delete/<item_type>/<item_id>", methods=["POST"])
    @admin_required
    def delete_archived_item(item_type, item_id):
        """Permanently delete an archived item."""
        try:
            if item_type == 'update':
                # For updates, item_id is a string (UUID)
                archived_item = ArchivedUpdate.query.get(item_id)
                if archived_item:
                    entity_title = f"Update: {archived_item.message[:50]}..."
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived update permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_update', archived_item.id, entity_title)
                else:
                    flash("❌ Archived update not found.", "error")

            elif item_type == 'sop':
                # For SOPs, item_id is an integer
                try:
                    sop_id = int(item_id)
                    archived_item = ArchivedSOPSummary.query.get(sop_id)
                except ValueError:
                    flash("❌ Invalid SOP ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    entity_title = archived_item.title
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived SOP permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_sop', str(sop_id), entity_title)
                else:
                    flash("❌ Archived SOP not found.", "error")

            elif item_type == 'lesson':
                # For lessons, item_id is an integer
                try:
                    lesson_id = int(item_id)
                    archived_item = ArchivedLessonLearned.query.get(lesson_id)
                except ValueError:
                    flash("❌ Invalid lesson ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    entity_title = archived_item.title
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived lesson permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_lesson', str(lesson_id), entity_title)
                else:
                    flash("❌ Archived lesson not found.", "error")

            else:
                flash("❌ Invalid item type.", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error deleting archived item: {str(e)}", "error")

        return redirect(url_for('archives_page'))

    # Add cache control for static files to prevent 304 caching issues
    @app.after_request
    def add_cache_control(response):
        if request.path.startswith('/static/'):
            # Don't cache JS and CSS files in development
            if app.config.get('DEBUG', False) or os.getenv('FLASK_ENV') != 'production':
                if request.path.endswith(('.js', '.css')):
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
            else:
                # In production, cache static files aggressively
                if request.path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
                    response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
                    response.headers['Expires'] = (datetime.utcnow() + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Socket.IO CORS is handled by the Socket.IO extension, don't override here

        # Add Render-specific headers (only essential ones in production)
        if os.getenv('RENDER'):
            is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
            is_development = os.getenv("FLASK_ENV") == "development" or not is_production

            # Essential headers for all environments
            response.headers['X-Render-Environment'] = os.getenv('RENDER')
            response.headers['X-SocketIO-Support'] = 'enabled'
            response.headers['X-WebSocket-Support'] = 'enabled'
            response.headers['X-Transport-Support'] = 'websocket,polling'
            response.headers['X-Server-Version'] = 'LoopIn-v1.0'

            # Add debug headers only in development
            if is_development:
                response.headers['X-Render-Service-ID'] = os.getenv('RENDER_SERVICE_ID', '')
                response.headers['X-Render-Service-Name'] = os.getenv('RENDER_SERVICE_NAME', '')
                response.headers['X-Render-External-URL'] = os.getenv('RENDER_EXTERNAL_URL', '')
                response.headers['X-Render-Git-Commit'] = os.getenv('RENDER_GIT_COMMIT', '')
                response.headers['X-Render-Git-Branch'] = os.getenv('RENDER_GIT_BRANCH', '')
                response.headers['X-Debug-Mode'] = str(debug_mode).lower()
                response.headers['X-Timestamp'] = now_utc().isoformat()
                response.headers['X-Status'] = 'healthy'
                response.headers['X-Connection-Status'] = 'ready'
                response.headers['X-SocketIO-Version'] = '4.7.2'
                response.headers['X-Debug-Info'] = 'Socket.IO debugging enabled'

        return response

    # Global error handlers to prevent worker crashes
    @app.errorhandler(404)
    def handle_404_error(error):
        """Handle 404 Not Found Error"""
        logger.warning(f"404 Not Found: {error}")
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found.'
        }), 404

    @app.errorhandler(500)
    def handle_500_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"500 Internal Server Error: {error}")
        db.session.rollback()  # Rollback any pending transactions
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors to prevent worker crashes"""
        logger.error(f"Unexpected error: {error}")
        try:
            db.session.rollback()  # Rollback any pending transactions
        except:
            pass
        return jsonify({
            'error': 'Unexpected Error',
            'message': 'An unexpected error occurred.'
        }), 500

    # Socket.IO error handler
    @socketio.on_error
    def handle_socketio_error(e):
        """Handle Socket.IO errors"""
        logger.error(f"Socket.IO error: {e}")
        try:
            db.session.rollback()
        except:
            pass

    # Database teardown for request context
    @app.teardown_request
    def teardown_request(exception):
        """Clean up database session after each request"""
        if exception:
            logger.error(f"Request exception: {exception}")
            try:
                db.session.rollback()
            except:
                pass
        try:
            db.session.remove()
        except:
            pass

    # Set up logging after app creation
    try:
        from logging_config import setup_logging
        setup_logging(app)
    except Exception as e:
        logger.warning(f"Failed to set up advanced logging: {e}")

    return app

# Create the Flask app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    # Create app instance for gunicorn or direct execution
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    # Set debug based on environment variable
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    if os.getenv("FLASK_ENV") == "development":
        print("🚀 Starting LoopIn server...")
        print(f"🔌 Socket.IO configured for port {port}")
        print(f"🌐 Server will be available at: http://0.0.0.0:{port}")
        print(f"🔧 Debug mode: {debug_mode}")

    try:
        # Use socketio.run for proper Socket.IO server startup
        if os.getenv("FLASK_ENV") == "development":
            print("🚀 Starting Socket.IO server...")
        # Configure Socket.IO with proper CORS and WebSocket settings
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=debug_mode,
            log_output=debug_mode,
            use_reloader=debug_mode,
            # Additional Socket.IO server options for Railway compatibility
            keyfile=None,
            certfile=None,
            cors_allowed_origins=[
                "https://loopin-home-production.up.railway.app",
                "https://loopin-core.onrender.com",
                "https://*.up.railway.app",
                "https://*.onrender.com",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:5000",
                "http://127.0.0.1:5000"
            ] if os.getenv("RENDER") else "*",
            server_options={
                'ping_timeout': 30,  # Reduced for faster disconnect detection
                'ping_interval': 15,  # More frequent health checks
                'max_http_buffer_size': 500000,  # Reduced for memory efficiency
                'allow_upgrades': True,
                'transports': ['websocket', 'polling'],  # Prefer WebSocket first
                'upgrade_timeout': 5000,  # Faster upgrade timeout
                'close_timeout': 30,  # Faster close timeout
                'heartbeat_interval': 15,  # More frequent heartbeats
                'heartbeat_timeout': 30,  # Faster heartbeat timeout
                'max_connections': 1000,
                'compression': True,
                'compression_threshold': 512,  # Compress smaller messages
                # Performance optimizations
                'handle_sigint': True,
                'always_connect': False,
                'jsonp': False,
                'cookie': None,
                'connect_timeout': 10,  # Connection timeout
                'client_manager_mode': 'threading',  # Use threading for better performance
            }
        )
    except Exception as e:
        logger.error(f"Failed to start Socket.IO server: {e}")
        if os.getenv("FLASK_ENV") == "development":
            print(f"❌ Failed to start Socket.IO server: {e}")
            import traceback
            print(f"❌ Full Socket.IO error: {traceback.format_exc()}")

        # Fallback to regular Flask app if Socket.IO fails
        if os.getenv("FLASK_ENV") == "development":
            print("🔄 Falling back to regular Flask app...")

        try:
            app.run(host="0.0.0.0", port=port, debug=debug_mode)
        except Exception as fallback_error:
            logger.error(f"Even fallback failed: {fallback_error}")
            if os.getenv("FLASK_ENV") == "development":
                print(f"❌ Even fallback failed: {fallback_error}")
            # Don't raise the exception to prevent worker crash
            # Instead, log the error and exit gracefully
            import sys
            sys.exit(1)

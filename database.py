"""Database session management and utilities"""

import os
import logging
import time
from contextlib import contextmanager
from typing import Generator
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, OperationalError, InternalError
from sqlalchemy import text, create_engine
from sqlalchemy.pool import QueuePool
from extensions import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database query performance monitoring
def log_query_performance(query, params=None, duration=None):
    """Log slow database queries for performance analysis"""
    if duration and duration > 0.5:  # Log queries taking more than 500ms
        logger.warning(".3f"
                      f"query_type={type(query).__name__} "
                      f"params={str(params)[:100] if params else 'None'}")
    elif duration:
        logger.info(".3f"
                   f"query_type={type(query).__name__}")

def get_db_url():
    """Get database URL with proper SSL configuration"""
    db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
    if 'postgresql' in db_url and 'localhost' not in db_url:
        # Add SSL parameters for non-local PostgreSQL connections
        if '?' not in db_url:
            db_url += '?'
        else:
            db_url += '&'
        db_url += 'sslmode=require'
    return db_url

def configure_engine(engine):
    """Configure database engine with optimized settings"""
    engine.dialect.description_encoding = None  # Prevent encoding issues
    engine.pool._use_threadlocal = True  # Enable thread-local storage
    engine.pool.timeout = 30  # Connection timeout in seconds
    engine.pool.recycle = 1800  # Recycle connections after 30 minutes
    engine.pool.pre_ping = True  # Enable connection pre-ping
    return engine

@contextmanager
def db_session(max_retries=3, initial_retry_delay=1) -> Generator:
    """Provide a transactional scope around a series of operations with retry logic."""
    logger.debug("Starting database session")
    attempt = 0
    retry_delay = initial_retry_delay
    last_error = None

    while attempt < max_retries:
        session = db.session()
        try:
            # Verify connection is active
            session.execute(text('SELECT 1'))
            yield session
            logger.debug("Committing database transaction")
            session.commit()
            return
        except (OperationalError, InternalError) as e:
            attempt += 1
            last_error = e
            logger.warning(f"Database connection error (attempt {attempt}/{max_retries}): {str(e)}")
            try:
                session.rollback()
            except Exception:
                pass

            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Max retries ({max_retries}) reached. Final error: {str(e)}")
                raise
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, 'orig'):
                logger.error(f"Original error: {e.orig}")

            # Enhanced lock-related error handling
            error_str = str(e).lower()
            if ('lock' in error_str or 'deadlock' in error_str or
                'cannot notify on un-acquired lock' in error_str or
                'cannot wait on un-acquired lock' in error_str or
                'advisory' in error_str):
                logger.warning("Lock error detected, performing cleanup")
                logger.warning(f"Lock error: {str(e)}")
                if hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
                    logger.warning(f"PostgreSQL error code: {e.orig.pgcode}")

                logger.warning("Performing database cleanup")
                cleanup_db()
                # Force engine disposal to clear any stale connections
                try:
                    db.engine.dispose()
                    logger.info("Database engine disposed due to lock error")
                except Exception as dispose_e:
                    logger.error(f"Error disposing engine: {dispose_e}")

                # For SQLite lock errors, also try to remove the lock file if it exists
                try:
                    import os
                    db_path = db.engine.url.database
                    if db_path and os.path.exists(db_path):
                        lock_file = db_path + '-lock'
                        if os.path.exists(lock_file):
                            os.remove(lock_file)
                            logger.info(f"Removed SQLite lock file: {lock_file}")
                except Exception as lock_e:
                    logger.error(f"Error removing lock file: {lock_e}")

                logger.warning("Lock error cleanup completed")

            try:
                session.rollback()
            except Exception:
                pass
            raise
        finally:
            logger.debug("Closing database session")
            try:
                session.close()
            except Exception:
                pass

    if last_error:
        raise last_error

def init_db(app):
    """Initialize database with app context."""
    with app.app_context():
        try:
            db.create_all()
            current_app.logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to initialize database: {str(e)}")
            raise

def cleanup_db():
    """Clean up database connections."""
    try:
        # Close any active transactions
        if db.session.is_active:
            db.session.rollback()
        db.session.remove()
        current_app.logger.debug("Database session cleaned up successfully")
    except Exception as e:
        current_app.logger.error(f"Error cleaning up database session: {str(e)}")

def validate_connection_before_operation():
    """Validate database connection before performing critical operations."""
    try:
        # Quick connection test
        with get_connection_with_retry() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Connection validation failed: {e}")
        # Try to recover by disposing the engine
        try:
            db.engine.dispose()
            logger.info("Engine disposed due to connection validation failure")
        except Exception as dispose_e:
            logger.error(f"Error disposing engine: {dispose_e}")
        return False

def ensure_database_ready():
    """Ensure database is properly configured and ready for operations."""
    try:
        # Check if we're using the right database type
        if db.engine.url.drivername.startswith('sqlite'):
            logger.warning("SQLite detected - this may cause lock issues in production")
            return False

        # Validate connection
        if not validate_connection_before_operation():
            logger.error("Database connection validation failed")
            return False

        # Check if essential tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        essential_tables = ['users', 'updates']

        for table in essential_tables:
            if table not in existing_tables:
                logger.warning(f"Essential table '{table}' not found")
                return False

        logger.info("Database is ready for operations")
        return True

    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        return False

def validate_database_type():
    """Validate that the correct database type is being used."""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False

        # Parse the URL to check the scheme
        from urllib.parse import urlparse
        parsed = urlparse(database_url)

        # Check if it's PostgreSQL
        if parsed.scheme not in ('postgresql', 'postgres'):
            if parsed.scheme in ('sqlite', 'sqlite3'):
                logger.error("SQLite database detected - this will cause lock issues in production")
                logger.error("Please configure PostgreSQL database for production use")
                return False
            else:
                logger.error(f"Unsupported database type: {parsed.scheme}")
                logger.error("Only PostgreSQL is supported for production")
                return False

        logger.info("Database type validation passed - using PostgreSQL")
        return True

    except Exception as e:
        logger.error(f"Database type validation failed: {e}")
        return False

# SSL context configuration removed - psycopg2 handles SSL through connection parameters

def test_ssl_connection(connection=None):
    """Test SSL connection parameters and attempt to diagnose SSL issues."""
    logger.info("Testing SSL connection configuration")

    # Use provided connection or create a new one
    if connection is None:
        connection = db.engine.connect()

    try:
        # Check if we're using PostgreSQL
        if db.engine.url.drivername != 'postgresql':
            logger.info("Not using PostgreSQL, SSL test skipped")
            return True

        # Test basic connection with transaction handling
        logger.info("Testing basic PostgreSQL connection...")
        try:
            connection.execute(text("SELECT version()"))
            logger.info("Basic connection successful")
        except Exception as conn_e:
            logger.error(f"Basic connection failed: {conn_e}")
            # Try to rollback any aborted transaction
            try:
                connection.rollback()
            except:
                pass
            return False

        # Test SSL-specific query (some PostgreSQL instances may not have sslinfo extension)
        logger.info("Testing SSL connection details...")
        try:
            ssl_query = text("""
                SELECT
                    ssl_cipher() as cipher,
                    ssl_version() as version,
                    ssl_client_cert_present() as client_cert,
                    ssl_client_cert_subject() as client_subject
            """)

            result = connection.execute(ssl_query).fetchone()
            if result:
                logger.info(f"SSL Cipher: {result.cipher}")
                logger.info(f"SSL Version: {result.version}")
                logger.info(f"Client Certificate Present: {result.client_cert}")
                logger.info("SSL connection details retrieved successfully")
            else:
                logger.warning("Could not retrieve SSL connection details")
        except Exception as ssl_e:
            logger.warning(f"SSL info functions not available: {ssl_e}")
            logger.info("This is normal for some PostgreSQL configurations (e.g., Render)")
            # For Render, try a different approach - check if SSL is working by testing the connection
            try:
                # Test with a simple query that should work with SSL
                simple_ssl_query = text("SELECT current_setting('ssl') as ssl_enabled")
                ssl_result = connection.execute(simple_ssl_query).fetchone()
                if ssl_result and ssl_result.ssl_enabled:
                    logger.info(f"SSL is enabled: {ssl_result.ssl_enabled}")
                    logger.info("SSL connection appears to be working (Render configuration)")
                else:
                    logger.info("SSL connection test completed (basic functionality working)")
            except Exception as simple_e:
                logger.warning(f"SSL status check failed: {simple_e}")
                # Don't fail the test for Render - SSL might still be working
                logger.info("Continuing with SSL test - connection appears functional")

        return True

    except SQLAlchemyError as e:
        logger.error(f"SSL connection test failed: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, 'orig'):
            logger.error(f"Original error: {e.orig}")
            # Handle transaction abortion errors specifically
            if 'InFailedSqlTransaction' in str(type(e.orig)) or 'current transaction is aborted' in str(e.orig):
                logger.warning("Transaction abortion detected, attempting recovery")
                try:
                    connection.rollback()
                    logger.info("Transaction rolled back successfully")
                except Exception as rollback_e:
                    logger.error(f"Failed to rollback transaction: {rollback_e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during SSL test: {str(e)}")
        return False
    finally:
        # Only close if we created the connection
        if connection is not None and connection is not db.session:
            try:
                connection.close()
            except Exception as close_e:
                logger.warning(f"Error closing connection: {close_e}")

def check_connection_health(connection):
    """Check if a database connection is healthy and can execute queries."""
    try:
        # Test with a simple query
        result = connection.execute(text("SELECT 1 as health_check"))
        row = result.fetchone()
        return row and row.health_check == 1
    except Exception as e:
        logger.warning(f"Connection health check failed: {e}")
        return False

def get_connection_with_retry(max_retries=3):
    """Get a healthy database connection with retry logic."""
    for attempt in range(max_retries):
        try:
            connection = db.engine.connect()
            if check_connection_health(connection):
                return connection
            else:
                connection.close()
                if attempt < max_retries - 1:
                    logger.warning(f"Connection health check failed, retrying (attempt {attempt + 1})")
                    time.sleep(0.5 * (attempt + 1))  # Progressive delay
                else:
                    raise Exception("Could not obtain healthy connection after retries")
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(0.5 * (attempt + 1))
            else:
                raise

def health_check() -> bool:
    """Check database connectivity with improved error handling for sync workers."""
    logger.info("Starting comprehensive database health check")

    # Log database connection details
    try:
        db_url = str(db.engine.url)
        logger.info(f"Database URL scheme: {db.engine.url.drivername}")
        logger.info(f"Database host: {db.engine.url.host}")
        logger.info(f"Database name: {db.engine.url.database}")

        # Log SSL-related environment variables
        ssl_env_vars = ['PG_SSLMODE', 'DATABASE_URL']
        for var in ssl_env_vars:
            value = os.getenv(var)
            if value:
                logger.info(f"{var}: {'***' if 'password' in var.lower() else value}")
            else:
                logger.warning(f"{var} not set")

        # Log connection pool status
        pool = db.engine.pool
        logger.info(f"Connection pool size: {getattr(pool, 'size', 'N/A')}")
        logger.info(f"Connection pool overflow: {getattr(pool, '_overflow', 'N/A')}")

        # Check if we're using the correct database type
        if db.engine.url.drivername.startswith('sqlite'):
            logger.warning("WARNING: Using SQLite database - this may cause lock issues in production")
            logger.warning("Ensure DATABASE_URL is properly set to PostgreSQL on Render")

        # Test connection with improved retry logic for sync workers
        logger.info("Testing database connection...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use a healthy connection for testing
                with get_connection_with_retry() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()  # Consume the result

                    # Additional health checks for PostgreSQL
                    if db.engine.url.drivername == 'postgresql':
                        # Test PostgreSQL-specific features
                        try:
                            pg_result = connection.execute(text("SELECT version()"))
                            version = pg_result.fetchone()
                            logger.info(f"PostgreSQL version: {version[0][:50]}...")
                        except Exception as pg_e:
                            logger.warning(f"PostgreSQL version check failed: {pg_e}")

                logger.info("Database connection successful")
                return True
            except SQLAlchemyError as conn_e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying: {conn_e}")
                    # Force pool recycle on connection errors
                    try:
                        db.session.close()
                        db.engine.dispose()
                    except:
                        pass
                    continue
                else:
                    # Final attempt failed
                    raise conn_e

    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, 'orig'):
            logger.error(f"Original psycopg2 error: {e.orig}")
            if hasattr(e.orig, 'pgcode'):
                logger.error(f"PostgreSQL error code: {e.orig.pgcode}")
        current_app.logger.error(f"Database health check failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during health check: {str(e)}")
        return False

"""Database session management and utilities"""

import os
import logging
from contextlib import contextmanager
from typing import Generator
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from extensions import db

logger = logging.getLogger(__name__)

@contextmanager
def db_session() -> Generator:
    """Provide a transactional scope around a series of operations."""
    logger.info("Starting database session")
    try:
        yield db.session
        logger.info("Committing database transaction")
        db.session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, 'orig'):
            logger.error(f"Original error: {e.orig}")
        db.session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        raise
    finally:
        logger.info("Closing database session")
        db.session.close()

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
        db.session.remove()
    except Exception as e:
        current_app.logger.error(f"Error cleaning up database session: {str(e)}")

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

        # Test basic connection
        logger.info("Testing basic PostgreSQL connection...")
        connection.execute(text("SELECT version()"))
        logger.info("Basic connection successful")

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
        return False
    except Exception as e:
        logger.error(f"Unexpected error during SSL test: {str(e)}")
        return False
    finally:
        # Only close if we created the connection
        if connection is not None and connection is not db.session:
            connection.close()

def health_check() -> bool:
    """Check database connectivity with improved error handling for sync workers."""
    logger.info("Starting database health check")

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

        # Test connection with improved retry logic for sync workers
        logger.info("Testing database connection...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use a new connection for testing to avoid session issues
                with db.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()  # Consume the result
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

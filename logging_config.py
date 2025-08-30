"""Logging configuration"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(app):
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Set up file handler for error logging
    error_log = log_dir / "error.log"
    file_handler = RotatingFileHandler(
        error_log,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)

    # Set up general application logging
    app_log = log_dir / "application.log"
    app_handler = RotatingFileHandler(
        app_log,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app_handler.setLevel(logging.INFO)
    app.logger.addHandler(app_handler)

    # Set overall logging level
    app.logger.setLevel(logging.INFO)
    
    # Log application startup
    env = app.config.get('ENV', os.getenv('FLASK_ENV', 'production'))
    app.logger.info(f"Starting {app.config.get('APP_NAME', 'LoopIn')} in {env} mode")

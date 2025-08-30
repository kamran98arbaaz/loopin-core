"""Monitoring configuration for the application"""

import os
import logging.config

# Prometheus metrics configuration
METRICS_PORT = int(os.getenv("METRICS_PORT", 9090))
COLLECT_DEFAULT_METRICS = True

# Define custom metrics
CUSTOM_METRICS = {
    "app_uptime_seconds": {
        "type": "gauge",
        "description": "Application uptime in seconds"
    },
    "database_connections_active": {
        "type": "gauge",
        "description": "Number of active database connections"
    },
    "request_latency_seconds": {
        "type": "histogram",
        "description": "Request latency in seconds",
        "buckets": [0.1, 0.5, 1.0, 2.0, 5.0]
    },
    "requests_total": {
        "type": "counter",
        "description": "Total number of HTTP requests"
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "logging.Formatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "formatter": "json",
            "level": "INFO"
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "formatter": "json",
            "level": "ERROR"
        }
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "INFO"
    },
    "loggers": {
        "werkzeug": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False
        },
        "sqlalchemy.engine": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False
        }
    }
}

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Apply logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

# Error notification configuration
ERROR_NOTIFICATION_CONFIG = {
    "enabled": True,
    "min_severity": "ERROR",
    "notification_url": os.getenv("ERROR_NOTIFICATION_WEBHOOK"),
    "batch_size": 10,
    "batch_interval": 300,  # 5 minutes
    "ignored_errors": [
        "ConnectionResetError",
        "ClientDisconnectedError"
    ]
}

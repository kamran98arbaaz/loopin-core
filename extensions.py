# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
login_manager = LoginManager()

# Configure Socket.IO for Vercel deployment
# Determine environment for conditional configuration
is_production = os.getenv("FLASK_ENV") == "production"
is_development = os.getenv("FLASK_ENV") == "development" or not is_production

socketio = SocketIO(
    # Vercel-optimized CORS configuration
    cors_allowed_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "*"  # Allow all origins for Vercel deployment
    ],
    logger=is_development,  # Only enable logging in development
    engineio_logger=is_development,  # Only enable engineio logging in development
    ping_timeout=30,  # Reduced for Vercel
    ping_interval=15,  # More frequent for Vercel
    max_http_buffer_size=500000,  # Reduced for memory efficiency
    allow_upgrades=True,
    cookie=None,  # Disable cookies for Vercel compatibility
    cors_credentials=False,  # Disable credentials to avoid CORS issues
    cors_methods=["GET", "POST", "OPTIONS"],
    cors_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Forwarded-For"],
    # Vercel-specific configurations
    manage_session=False,  # Disable Flask session management for Vercel
    message_queue=None,  # Use in-memory queue for Vercel
    channel='socketio',  # Channel name for message queue
    # Socket.IO v5 compatible settings
    async_mode='threading',  # Use threading for Vercel compatibility
    path='/socket.io',  # Explicit Socket.IO path
    transports=['websocket', 'polling'],  # Support both transports
    # Optimized configurations for Vercel
    close_timeout=30,  # Shorter close timeout
    heartbeat_interval=15,  # Heartbeat interval
    heartbeat_timeout=30,  # Heartbeat timeout
    max_connections=500,  # Reasonable connection limit for Vercel
    compression=True,  # Enable compression for better performance
    compression_threshold=512,  # Compress smaller messages
    # Connection stability options
    client_manager_mode='threading',  # Threading client manager
    monitor_clients=True,  # Monitor client connections
    # Vercel optimization settings
    always_connect=False,  # Don't force connections
    jsonp=False,  # Disable JSONP for security
    # Socket.IO v4 compatibility
    engineio_path='/socket.io',  # Explicit engine.io path
    engineio_ping_timeout=30,
    engineio_ping_interval=15,
    engineio_max_http_buffer_size=500000,
    engineio_allow_upgrades=True,
    engineio_cookie=None,
    engineio_cors_allowed_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "*"  # Allow all origins for Vercel deployment
    ]
)

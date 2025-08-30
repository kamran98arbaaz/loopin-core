# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
login_manager = LoginManager()

# Configure Socket.IO for Render deployment
# Determine environment for conditional configuration
is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
is_development = os.getenv("FLASK_ENV") == "development" or not is_production

socketio = SocketIO(
    # Render-optimized CORS configuration
    cors_allowed_origins=[
        "https://loopin-home-production.up.railway.app",
        "https://loopin-core.onrender.com",
        "https://*.up.railway.app",
        "https://*.onrender.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ],
    logger=is_development,  # Only enable logging in development
    engineio_logger=is_development,  # Only enable engineio logging in development
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    allow_upgrades=True,
    cookie=None,  # Disable cookies for Render compatibility
    cors_credentials=False,  # Disable credentials to avoid CORS issues
    cors_methods=["GET", "POST", "OPTIONS"],
    cors_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Forwarded-For"],
    # Render-specific configurations
    manage_session=False,  # Disable Flask session management for Render
    message_queue=None,  # Use in-memory queue for single instance
    channel='socketio',  # Channel name for message queue
    # Socket.IO v5 compatible settings
    async_mode='threading',  # Use threading for sync worker compatibility
    path='/socket.io',  # Explicit Socket.IO path
    transports=['websocket', 'polling'],  # Prioritize WebSocket for Render
    # Enhanced stability configurations for Render
    close_timeout=60,  # Longer close timeout for stability
    heartbeat_interval=25,  # Heartbeat interval
    heartbeat_timeout=60,  # Heartbeat timeout
    max_connections=1000,  # Reasonable connection limit for Render
    compression=True,  # Enable compression for better performance
    compression_threshold=1024,  # Compress messages over 1KB
    # Connection stability options
    client_manager_mode='threading',  # Threading client manager
    monitor_clients=True,  # Monitor client connections
    # Render optimization settings
    always_connect=False,  # Don't force connections
    jsonp=False,  # Disable JSONP for security
    # Socket.IO v4 compatibility
    engineio_path='/socket.io',  # Explicit engine.io path
    engineio_ping_timeout=60,
    engineio_ping_interval=25,
    engineio_max_http_buffer_size=1000000,
    engineio_allow_upgrades=True,
    engineio_cookie=None,
    engineio_cors_allowed_origins=[
        "https://loopin-home-production.up.railway.app",
        "https://loopin-core.onrender.com",
        "https://*.up.railway.app",
        "https://*.onrender.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]
)

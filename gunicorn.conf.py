# Gunicorn configuration optimized for Render free tier (512MB RAM, 0.1 CPU)
import multiprocessing
import os

# Environment detection
is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
is_development = os.getenv("FLASK_ENV") == "development"

# Bind to the port provided by Render
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker configuration optimized for free tier
# Use only 1 worker to minimize memory usage
workers = 1
worker_class = 'sync'  # Use sync workers for SQLAlchemy compatibility
threads = 2  # Minimal threads for concurrency
worker_connections = 50  # Reduced connections per worker

# Timeouts optimized for free tier
timeout = 30  # Shorter timeout to free memory faster
keepalive = 5  # Shorter keepalive
graceful_timeout = 15  # Faster graceful shutdown

# Memory optimization
preload_app = True  # Preload app to share memory
max_requests = 200  # Restart worker after fewer requests to prevent memory leaks
max_requests_jitter = 20
worker_tmp_dir = '/dev/shm'  # Use memory for temp files

# Backlog and performance tuning
backlog = 128  # Smaller backlog for free tier

# Logging configuration
if is_production:
    loglevel = 'warning'  # Less verbose in production
    accesslog = None  # Disable access log in production
    errorlog = None  # Disable error log in production (use Render logs)
else:
    loglevel = 'info'
    accesslog = '-'
    errorlog = '-'

# Process naming
proc_name = 'loopin'

# Security settings
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 4096

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None

# SSL Configuration (handled by Render)
keyfile = None
certfile = None
ssl_version = 'TLS'
cert_reqs = 0  # SSL_NONE

# Hook functions for monitoring
def on_starting(server):
    """Log when the server starts."""
    server.log.info("Starting Loopin server with optimized free tier config")

def when_ready(server):
    """Log when the server is ready."""
    server.log.info("Loopin server is ready")

def worker_abort(worker):
    """Log when a worker is aborted."""
    worker.log.warning("Worker aborted - possible memory issue")

def on_reload(server):
    """Log when server is reloaded."""
    server.log.info("Server reloaded")

def post_fork(server, worker):
    """Log after worker fork."""
    server.log.info(f"Worker {worker.pid} forked")

def pre_fork(server, worker):
    """Log before worker fork."""
    server.log.info(f"Forking worker {worker.pid}")

def worker_int(worker):
    """Log when worker receives INT signal."""
    worker.log.info("Worker received INT signal")

def child_exit(server, worker):
    """Log when a worker exits"""
    server.log.info(f"Worker {worker.pid} exited")

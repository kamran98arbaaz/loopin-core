# Gunicorn configuration optimized for Render memory constraints
import multiprocessing
import os

# Render-optimized worker configuration (memory-efficient)
# Render typically provides 512MB-1GB, so we need to be conservative
cpu_count = multiprocessing.cpu_count()
if cpu_count > 1:
    workers = 2  # Fixed at 2 workers for Render
else:
    workers = 1

# Environment-specific configuration
is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
if is_production:
    # Production optimizations
    loglevel = 'warning'  # Less verbose in production
    accesslog = None  # Disable access log in production
    errorlog = None  # Disable error log in production (use Render logs)
else:
    # Development settings
    loglevel = 'info'
    accesslog = '-'
    errorlog = '-'

worker_class = 'sync'  # Use sync workers for SQLAlchemy compatibility
threads = 2  # Use threads for better concurrency
timeout = 30  # Shorter timeout to free memory faster
keepalive = 10  # Shorter keepalive

# Memory optimization
preload_app = True  # Preload app to share memory
max_requests = 500  # Restart worker after fewer requests
max_requests_jitter = 50
worker_connections = 100  # Reduce connections per worker

# Render-specific optimizations
import multiprocessing
import os

# Bind to the port provided by Render
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
threads = 4
worker_class = 'gevent'  # Use gevent for better async performance
worker_connections = 1000

# Timeouts
timeout = 120
keepalive = 5
graceful_timeout = 30

# SSL Configuration (handled by Render)
keyfile = None
certfile = None

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'loopin-gunicorn'

# Performance tuning
worker_tmp_dir = '/dev/shm'  # Use memory for temp files
max_requests = 1000
max_requests_jitter = 50
backlog = 2048

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None

# SSL Configuration
ssl_version = 'TLS'
cert_reqs = 0  # SSL_NONE

# Hook functions
def on_starting(server):
    """Log when the server starts"""
    server.log.info("Starting Gunicorn with gevent worker")

def on_reload(server):
    """Log when the server reloads"""
    server.log.info("Reloading Gunicorn workers")

def child_exit(server, worker):
    """Log when a worker exits"""
    server.log.info(f"Worker {worker.pid} exited")
backlog = 128  # Smaller backlog
graceful_timeout = 15  # Faster graceful shutdown

# Logging (keep minimal for memory)
accesslog = '-'
errorlog = '-'
loglevel = 'warning'  # Less verbose logging

# Security (keep minimal)
limit_request_line = 4094
limit_request_fields = 50  # Reduced
limit_request_field_size = 4096  # Reduced

# Process naming
proc_name = 'loopin'

def on_starting(server):
    """Log when the server starts."""
    server.log.info("Starting Loopin server")

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

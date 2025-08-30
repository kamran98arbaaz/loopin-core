"""Backup system configuration"""

import os
from datetime import timedelta

# Backup retention configuration
BACKUP_RETENTION_DAYS = 30  # Keep backups for 30 days
MAX_BACKUP_SIZE = 1024 * 1024 * 500  # 500MB max backup size
MIN_BACKUP_INTERVAL = timedelta(hours=12)  # Minimum time between backups

# Backup location configuration
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
BACKUP_TEMP_DIR = os.path.join(BACKUP_DIR, "temp")

# Ensure backup directories exist
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(BACKUP_TEMP_DIR, exist_ok=True)

# Backup file patterns
BACKUP_FILE_PREFIX = "loopin_backup_"
BACKUP_FILE_SUFFIX = ".sql"  # Updated to SQL format for Render compatibility

# Notification settings
BACKUP_NOTIFICATION_EMAILS = os.getenv("BACKUP_NOTIFICATION_EMAILS", "").split(",")
NOTIFY_ON_BACKUP_SUCCESS = True
NOTIFY_ON_BACKUP_FAILURE = True

# Compression settings
COMPRESS_BACKUPS = True
COMPRESSION_LEVEL = 6  # Range 1-9, higher means better compression but slower

# Validation settings
VALIDATE_BACKUPS = True
CHECKSUM_ALGORITHM = "sha256"

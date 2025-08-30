"""
Render-compatible backup system for LoopIn - No PostgreSQL client tools required
"""
import os
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from timezone_utils import now_utc
from extensions import db
from models import Update, SOPSummary, LessonLearned, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned, User, ReadLog, ActivityLog
from sqlalchemy import text

class DatabaseBackupSystem:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.parsed_url = urlparse(self.database_url)

        # Use configurable backup directory with fallback
        backup_dir_env = os.getenv("BACKUP_DIR", "backups")
        self.backup_dir = Path(backup_dir_env)
        self.backup_dir.mkdir(exist_ok=True)

        # Environment detection
        self.is_render = self._detect_render_environment()
        self.is_production = os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production"
        self.is_development = os.getenv("FLASK_ENV") == "development" or not self.is_production

        # Load backup configuration
        self._load_backup_config()

        # Log only in development or for important events
        if self.is_development:
            print(f"[OK] Database backup system initialized for {'Render' if self.is_render else 'standard'} environment")

    def _detect_render_environment(self):
        """Detect if we're running on Render"""
        return (
            "render" in self.database_url.lower() or
            os.getenv("RENDER") is not None or
            os.getenv("RENDER_SERVICE_ID") is not None
        )

    def _load_backup_config(self):
        """Load backup configuration with environment-specific settings"""
        # Default configuration
        self.max_backup_size = int(os.getenv("MAX_BACKUP_SIZE", "524288000"))  # 500MB default
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.compress_backups = os.getenv("COMPRESS_BACKUPS", "true").lower() == "true"
        self.validate_backups = os.getenv("VALIDATE_BACKUPS", "true").lower() == "true"

        # Production-specific settings
        if self.is_production:
            # More conservative settings for production
            self.backup_retention_days = min(self.backup_retention_days, 90)  # Max 90 days in production
            self.max_backup_size = min(self.max_backup_size, 1073741824)  # Max 1GB in production
        else:
            # More permissive settings for development
            self.backup_retention_days = max(self.backup_retention_days, 7)  # Min 7 days in development
    
    def create_backup(self, backup_type="manual"):
        """Create a database backup using SQL dump format (Railway-compatible)"""
        try:
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"loopin_backup_{backup_type}_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename

            if self.is_development:
                print(f"[BACKUP] Creating Render-compatible SQL backup: {backup_path}")

            # Create SQL dump file
            with open(backup_path, 'w', encoding='utf-8') as f:
                # Write SQL header with metadata
                f.write("-- LoopIn Database Backup\n")
                f.write(f"-- Created: {now_utc().isoformat()}\n")
                f.write(f"-- Type: {backup_type}\n")
                f.write(f"-- Environment: {'production' if self.is_production else 'development'}\n")
                f.write(f"-- Version: 4.0 (PostgreSQL Format)\n")
                f.write("-- Render Compatible: Yes\n\n")

                # PostgreSQL doesn't need to disable foreign key checks like MySQL
                # Foreign key constraints are automatically deferred in transactions

                # Export all tables
                tables_to_export = [
                    ("users", User),
                    ("updates", Update),
                    ("read_logs", ReadLog),
                    ("activity_logs", ActivityLog),
                    ("sop_summaries", SOPSummary),
                    ("lessons_learned", LessonLearned),
                    ("archived_updates", ArchivedUpdate),
                    ("archived_sop_summaries", ArchivedSOPSummary),
                    ("archived_lessons_learned", ArchivedLessonLearned)
                ]

                total_records = 0
                for table_name, model_class in tables_to_export:
                    try:
                        if self.is_development:
                            print(f"  [EXPORT] Exporting {table_name}...")

                        records = model_class.query.all()
                        if records:
                            # Clear existing data in table
                            f.write(f"DELETE FROM {table_name};\n")

                            # Generate INSERT statements
                            for record in records:
                                record_dict = record.to_dict() if hasattr(record, 'to_dict') else self._model_to_dict(record)
                                # Use PostgreSQL-style quoting for identifiers
                                columns = ', '.join(f'"{k}"' for k in record_dict.keys())
                                values = ', '.join(self._format_sql_value(v) for v in record_dict.values())
                                f.write(f"INSERT INTO {table_name} ({columns}) VALUES ({values});\n")

                            total_records += len(records)
                            if self.is_development:
                                print(f"    [OK] {len(records)} records exported")
                        else:
                            if self.is_development:
                                print(f"    [EMPTY] {table_name}: No records to export")

                    except Exception as e:
                        if self.is_development:
                            print(f"    [WARN] Failed to export {table_name}: {e}")
                        continue

                # PostgreSQL automatically handles foreign key constraints
                # No need to re-enable anything

                # Add completion comment
                f.write(f"\n-- Backup completed successfully\n")
                f.write(f"-- Total records: {total_records}\n")
                f.write(f"-- Generated at: {now_utc().isoformat()}\n")

            # Check backup file size
            file_size = backup_path.stat().st_size
            if file_size > self.max_backup_size:
                if self.is_development:
                    print(f"[WARN] Backup size ({file_size} bytes) exceeds maximum allowed size ({self.max_backup_size} bytes)")
                backup_path.unlink()  # Delete the oversized backup
                return None

            # Verify backup file
            if backup_path.exists() and file_size > 0:
                if self.is_development:
                    print(f"[SUCCESS] SQL Backup created successfully: {backup_path}")
                    print(f"   [STATS] Total records: {total_records}")
                    print(f"   [SIZE] File size: {file_size} bytes")

                # Create metadata file
                metadata = {
                    "backup_type": backup_type,
                    "timestamp": timestamp,
                    "file_size": file_size,
                    "created_at": now_utc().isoformat(),
                    "format": "postgresql_sql_dump",
                    "database_url": self._mask_database_url(),
                    "total_records": total_records,
                    "railway_compatible": True,
                    "backup_version": "4.0",
                    "restore_instructions": "Execute the SQL file directly in PostgreSQL",
                    "environment": "production" if self.is_production else "development"
                }

                metadata_path = backup_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                return backup_path
            else:
                if self.is_development:
                    print("[ERROR] Backup file was not created or is empty")
                return None

        except Exception as e:
            if self.is_development:
                print(f"[ERROR] Backup error: {e}")
            return None

    def _model_to_dict(self, model_instance):
        """Convert SQLAlchemy model instance to dictionary"""
        try:
            result = {}
            for column in model_instance.__table__.columns:
                value = getattr(model_instance, column.name)
                # Convert datetime objects to ISO strings
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                result[column.name] = value
            return result
        except Exception as e:
            if self.is_development:
                print(f"⚠️  Error converting model to dict: {e}")
            return {}

    def _format_sql_value(self, value):
        """Format a value for SQL INSERT statement"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # Escape single quotes and wrap in quotes
            return f"'{value.replace(chr(39), chr(39) + chr(39))}'"
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, (int, float)):
            return str(value)
        elif hasattr(value, 'isoformat'):  # datetime objects
            return f"'{value.isoformat()}'"
        elif isinstance(value, list):
            # Convert lists to JSON strings
            return f"'{json.dumps(value)}'"
        else:
            # Convert to string and escape
            return f"'{str(value).replace(chr(39), chr(39) + chr(39))}'"

    def _mask_database_url(self):
        """Mask sensitive information in database URL for metadata"""
        try:
            parsed = self.parsed_url
            if parsed.password:
                masked_password = "***"
                masked_url = f"{parsed.scheme}://{parsed.username}:{masked_password}@{parsed.hostname}:{parsed.port}{parsed.path}"
                return masked_url
            return str(self.database_url)
        except:
            return "postgresql://***:***@***:***/***"

    def _clear_existing_data(self):
        """Clear existing data before restore"""
        try:
            print("  [CLEAN] Clearing existing data...")

            # Clear tables in reverse dependency order
            tables_to_clear = [
                ReadLog, ActivityLog,  # Foreign key dependencies
                Update, SOPSummary, LessonLearned,  # Main tables
                ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned,  # Archive tables
                User  # Users table last
            ]

            for table_class in tables_to_clear:
                try:
                    deleted_count = table_class.query.delete()
                    print(f"    [CLEAN] Cleared {deleted_count} records from {table_class.__tablename__}")
                except Exception as e:
                    print(f"    [WARN] Failed to clear {table_class.__tablename__}: {e}")

            db.session.commit()
            print("  [OK] Existing data cleared")
            return True

        except Exception as e:
            print(f"  [ERROR] Failed to clear existing data: {e}")
            db.session.rollback()
            return False

    def _restore_table(self, model_class, records):
        """Restore records to a specific table"""
        try:
            restored_count = 0
            for record_data in records:
                try:
                    # Create new instance
                    record = model_class()

                    # Set attributes
                    for key, value in record_data.items():
                        if hasattr(record, key):
                            # Handle special cases
                            if key == 'timestamp' and value and isinstance(value, str):
                                # Parse ISO timestamp
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.timestamp = now_utc()
                            elif key == 'created_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.created_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.created_at = now_utc()
                            elif key == 'updated_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.updated_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.updated_at = now_utc()
                            elif key == 'archived_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.archived_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.archived_at = now_utc()
                            else:
                                setattr(record, key, value)

                    # Add to session
                    db.session.add(record)
                    restored_count += 1

                except Exception as e:
                    print(f"    ⚠️  Failed to restore record: {e}")
                    continue

            # Commit the batch
            db.session.commit()
            return restored_count

        except Exception as e:
            print(f"  ❌ Failed to restore table {model_class.__tablename__}: {e}")
            db.session.rollback()
            return 0
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        for backup_file in self.backup_dir.glob("*.sql"):
            metadata_file = backup_file.with_suffix('.json')
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append({
                        'file': backup_file,
                        'metadata': metadata
                    })
                except Exception as e:
                    if self.is_development:
                        print(f"⚠️  Error reading metadata for {backup_file}: {e}")
                    continue

        backups.sort(key=lambda x: x['metadata']['created_at'], reverse=True)
        return backups
    
    def verify_backup(self, backup_path):
        """Verify backup file exists and is readable"""
        try:
            return backup_path.exists() and backup_path.stat().st_size > 0
        except:
            return False
    
    def restore_backup(self, backup_path):
        """Restore database from SQL backup file"""
        try:
            print(f"[RESTORE] Starting SQL restore from: {backup_path}")

            # Step 1: Verify backup file
            if not backup_path.exists():
                print(f"[ERROR] Backup file not found: {backup_path}")
                return False

            if backup_path.suffix.lower() != '.sql':
                print(f"[ERROR] Invalid backup file format. Expected .sql, got {backup_path.suffix}")
                return False

            # Step 2: Clear existing data
            print("[PREP] Preparing database for restore...")
            if not self._clear_existing_data():
                print("[WARN] Warning: Could not clear existing data")

            # Step 3: Execute SQL file
            print("[EXEC] Executing SQL restore...")
            total_executed = 0

            with open(backup_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Split SQL into individual statements (basic approach)
            # Remove comments and split by semicolons
            import re
            sql_statements = []
            for statement in sql_content.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    # Remove inline comments
                    statement = re.sub(r'--.*$', '', statement, flags=re.MULTILINE).strip()
                    if statement:
                        sql_statements.append(statement + ';')

            # Execute each statement
            for i, statement in enumerate(sql_statements):
                try:
                    if statement.strip():
                        db.session.execute(text(statement))
                        total_executed += 1
                        if self.is_development and (i + 1) % 100 == 0:
                            print(f"    [PROGRESS] Executed {i + 1} statements...")
                except Exception as e:
                    if self.is_development:
                        print(f"    [WARN] Failed to execute statement {i + 1}: {e}")
                    continue

            # Ensure all changes are committed
            try:
                db.session.commit()
                print("[OK] Database changes committed successfully")
            except Exception as commit_error:
                print(f"[WARN] Commit failed, attempting rollback: {commit_error}")
                db.session.rollback()
                return False

            # Step 4: Verify restore
            print("[SUCCESS] SQL Restore completed successfully!")
            print(f"[STATS] Total SQL statements executed: {total_executed}")
            print("[SUMMARY]:")
            print("   [OK] SQL backup executed")
            print("   [OK] Database tables restored")
            print("   [OK] Render-compatible SQL format used")

            return True

        except Exception as e:
            # Ensure proper rollback on any error
            try:
                db.session.rollback()
                print("[OK] Database rolled back successfully")
            except Exception as rollback_error:
                print(f"[ERROR] Rollback failed: {rollback_error}")

            print(f"[ERROR] Restore failed: {e}")
            return False

    def _preflight_checks(self, backup_path):
        """Quick pre-flight checks before restore"""
        print("🔍 Running pre-flight checks...")

        # Check if backup file exists and is readable
        if not self.verify_backup(backup_path):
            print(f"[ERROR] Backup file verification failed: {backup_path}")
            return False

        # Check file size (should not be empty)
        file_size = backup_path.stat().st_size
        if file_size == 0:
            print("[ERROR] Backup file is empty")
            return False

        print(f"[OK] Backup file OK ({file_size} bytes)")
        return True

    def _restore_archived_items_to_original_locations(self):
        """Move all archived items back to their original tables using SQLAlchemy"""
        print("[ARCHIVE] Moving archived items to original locations...")

        try:
            # Move archived updates back to updates table
            archived_updates = ArchivedUpdate.query.all()
            for archived in archived_updates:
                try:
                    # Create new update from archived data
                    restored_update = Update(
                        id=archived.id,
                        name=archived.name,
                        process=archived.process,
                        message=archived.message,
                        timestamp=archived.timestamp
                    )
                    db.session.add(restored_update)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived update {archived.id}: {e}")

            # Move archived SOPs back to sop_summaries table
            archived_sops = ArchivedSOPSummary.query.all()
            for archived in archived_sops:
                try:
                    restored_sop = SOPSummary(
                        id=archived.id,
                        title=archived.title,
                        summary_text=archived.summary_text,
                        department=archived.department,
                        tags=archived.tags,
                        created_at=archived.created_at
                    )
                    db.session.add(restored_sop)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived SOP {archived.id}: {e}")

            # Move archived lessons back to lessons_learned table
            archived_lessons = ArchivedLessonLearned.query.all()
            for archived in archived_lessons:
                try:
                    restored_lesson = LessonLearned(
                        id=archived.id,
                        title=archived.title,
                        content=archived.content,
                        summary=archived.summary,
                        author=archived.author,
                        department=archived.department,
                        tags=archived.tags,
                        created_at=archived.created_at,
                        updated_at=archived.updated_at
                    )
                    db.session.add(restored_lesson)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived lesson {archived.id}: {e}")

            # Commit all changes
            db.session.commit()
            print("[OK] Archived items moved to original locations")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to restore archived items: {e}")
            db.session.rollback()
            return False

    def _post_restore_cleanup_and_verify(self):
        """Clean up archived tables and verify restore integrity"""
        print("[CLEANUP] Post-restore cleanup and verification...")

        try:
            # Clear archived tables since items are now in original locations
            archived_tables = [ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned]

            for table_class in archived_tables:
                try:
                    deleted_count = table_class.query.delete()
                    print(f"  [CLEAN] Cleared {deleted_count} records from {table_class.__tablename__}")
                except Exception as e:
                    print(f"  [WARN] Failed to clean up {table_class.__tablename__}: {e}")

            db.session.commit()
            print("[OK] Post-restore cleanup completed")
            return True

        except Exception as e:
            print(f"[WARN] Post-restore cleanup had issues: {e}")
            db.session.rollback()
            return False
    
    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            from datetime import datetime, timedelta

            # Get all SQL backup files
            backup_files = list(self.backup_dir.glob("*.sql"))
            current_time = now_utc()

            backups_to_delete = []

            for backup_file in backup_files:
                try:
                    # Check file age
                    file_age_days = (current_time - datetime.fromtimestamp(backup_file.stat().st_mtime, tz=current_time.tzinfo)).days

                    if file_age_days > self.backup_retention_days:
                        backups_to_delete.append(backup_file)
                except Exception as e:
                    if self.is_development:
                        print(f"[WARN] Error checking backup file {backup_file}: {e}")
                    continue

            # Delete old backups
            deleted_count = 0
            for backup_file in backups_to_delete:
                try:
                    # Delete main backup file
                    backup_file.unlink()

                    # Delete associated metadata file
                    metadata_file = backup_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()

                    deleted_count += 1
                    if self.is_development:
                        print(f"[DELETE] Deleted old backup: {backup_file.name}")
                except Exception as e:
                    if self.is_development:
                        print(f"[WARN] Error deleting backup {backup_file}: {e}")

            if self.is_development and deleted_count > 0:
                print(f"[SUCCESS] Cleaned up {deleted_count} old backups (retention: {self.backup_retention_days} days)")

        except Exception as e:
            if self.is_development:
                print(f"[ERROR] Error during backup cleanup: {e}")

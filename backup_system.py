"""Database backup and restore system for LoopIn"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from flask import current_app
from extensions import db
from models import User, Update, ReadLog, SOPSummary, LessonLearned, ActivityLog, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned
from timezone_utils import now_utc, format_ist

logger = logging.getLogger(__name__)

class DatabaseBackupSystem:
    """Handles database backup and restore operations"""

    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, backup_type: str = "manual") -> Optional[str]:
        """Create a database backup"""
        try:
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"loopin_backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / backup_filename

            # Create backup data structure
            backup_data = {
                "metadata": {
                    "timestamp": now_utc().isoformat(),
                    "type": backup_type,
                    "version": "1.0",
                    "app_name": current_app.config.get("APP_NAME", "LoopIn")
                },
                "data": {}
            }

            # Backup users
            users = User.query.all()
            backup_data["data"]["users"] = [
                {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "password_hash": user.password_hash,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "is_active": user.is_active
                } for user in users
            ]

            # Backup updates
            updates = Update.query.all()
            backup_data["data"]["updates"] = [
                {
                    "id": update.id,
                    "name": update.name,
                    "process": update.process,
                    "message": update.message,
                    "timestamp": update.timestamp.isoformat()
                } for update in updates
            ]

            # Backup read logs
            read_logs = ReadLog.query.all()
            backup_data["data"]["read_logs"] = [
                {
                    "id": log.id,
                    "update_id": log.update_id,
                    "user_id": log.user_id,
                    "guest_name": log.guest_name,
                    "timestamp": log.timestamp.isoformat(),
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent
                } for log in read_logs
            ]

            # Backup SOP summaries
            sops = SOPSummary.query.all()
            backup_data["data"]["sop_summaries"] = [
                {
                    "id": sop.id,
                    "title": sop.title,
                    "summary_text": sop.summary_text,
                    "department": sop.department,
                    "tags": sop.tags,
                    "created_at": sop.created_at.isoformat()
                } for sop in sops
            ]

            # Backup lessons learned
            lessons = LessonLearned.query.all()
            backup_data["data"]["lessons_learned"] = [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content,
                    "summary": lesson.summary,
                    "author": lesson.author,
                    "department": lesson.department,
                    "tags": lesson.tags,
                    "created_at": lesson.created_at.isoformat()
                } for lesson in lessons
            ]

            # Backup activity logs
            activities = ActivityLog.query.all()
            backup_data["data"]["activity_logs"] = [
                {
                    "id": activity.id,
                    "user_id": activity.user_id,
                    "action": activity.action,
                    "entity_type": activity.entity_type,
                    "entity_id": activity.entity_id,
                    "entity_title": activity.entity_title,
                    "timestamp": activity.timestamp.isoformat(),
                    "ip_address": activity.ip_address,
                    "user_agent": activity.user_agent,
                    "details": activity.details
                } for activity in activities
            ]

            # Save backup to JSON file
            with open(f"{backup_path}.json", 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def verify_backup(self, backup_path: Path) -> bool:
        """Verify backup file integrity"""
        try:
            if not backup_path.exists():
                return False

            with open(f"{backup_path}.json", 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Basic validation
            if "metadata" not in backup_data or "data" not in backup_data:
                return False

            if "users" not in backup_data["data"]:
                return False

            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore database from backup"""
        try:
            # Load backup data
            with open(f"{backup_path}.json", 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Clear existing data (optional - be careful!)
            # Uncomment the following lines if you want to clear existing data before restore
            # ActivityLog.query.delete()
            # ReadLog.query.delete()
            # LessonLearned.query.delete()
            # SOPSummary.query.delete()
            # Update.query.delete()
            # User.query.delete()

            # Restore users
            for user_data in backup_data["data"]["users"]:
                user = User(
                    id=user_data["id"],
                    username=user_data["username"],
                    display_name=user_data["display_name"],
                    password_hash=user_data["password_hash"],
                    role=user_data.get("role", "user"),
                    created_at=datetime.fromisoformat(user_data["created_at"]) if user_data["created_at"] else None,
                    is_active=user_data.get("is_active", True)
                )
                db.session.add(user)

            # Restore updates
            for update_data in backup_data["data"]["updates"]:
                update = Update(
                    id=update_data["id"],
                    name=update_data["name"],
                    process=update_data["process"],
                    message=update_data["message"],
                    timestamp=datetime.fromisoformat(update_data["timestamp"])
                )
                db.session.add(update)

            # Restore read logs
            for log_data in backup_data["data"]["read_logs"]:
                log = ReadLog(
                    id=log_data["id"],
                    update_id=log_data["update_id"],
                    user_id=log_data["user_id"],
                    guest_name=log_data["guest_name"],
                    timestamp=datetime.fromisoformat(log_data["timestamp"]),
                    ip_address=log_data["ip_address"],
                    user_agent=log_data["user_agent"]
                )
                db.session.add(log)

            # Restore SOP summaries
            for sop_data in backup_data["data"]["sop_summaries"]:
                sop = SOPSummary(
                    id=sop_data["id"],
                    title=sop_data["title"],
                    summary_text=sop_data["summary_text"],
                    department=sop_data["department"],
                    tags=sop_data["tags"],
                    created_at=datetime.fromisoformat(sop_data["created_at"])
                )
                db.session.add(sop)

            # Restore lessons learned
            for lesson_data in backup_data["data"]["lessons_learned"]:
                lesson = LessonLearned(
                    id=lesson_data["id"],
                    title=lesson_data["title"],
                    content=lesson_data["content"],
                    summary=lesson_data["summary"],
                    author=lesson_data["author"],
                    department=lesson_data["department"],
                    tags=lesson_data["tags"],
                    created_at=datetime.fromisoformat(lesson_data["created_at"])
                )
                db.session.add(lesson)

            # Restore activity logs
            for activity_data in backup_data["data"]["activity_logs"]:
                activity = ActivityLog(
                    id=activity_data["id"],
                    user_id=activity_data["user_id"],
                    action=activity_data["action"],
                    entity_type=activity_data["entity_type"],
                    entity_id=activity_data["entity_id"],
                    entity_title=activity_data["entity_title"],
                    timestamp=datetime.fromisoformat(activity_data["timestamp"]),
                    ip_address=activity_data["ip_address"],
                    user_agent=activity_data["user_agent"],
                    details=activity_data["details"]
                )
                db.session.add(activity)

            db.session.commit()
            logger.info(f"Backup restored successfully from: {backup_path}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to restore backup: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        try:
            backups = []
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Ensure metadata exists
                    if "metadata" not in data:
                        logger.warning(f"Backup file {backup_file} missing metadata, skipping")
                        continue

                    metadata = data["metadata"]

                    # Ensure required metadata fields exist
                    if "timestamp" not in metadata or "type" not in metadata:
                        logger.warning(f"Backup file {backup_file} missing required metadata fields, skipping")
                        continue

                    backups.append({
                        "filename": backup_file.stem,
                        "timestamp": metadata["timestamp"],
                        "type": metadata.get("type", "unknown"),
                        "size": backup_file.stat().st_size,
                        "path": str(backup_file)
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in backup file {backup_file}: {e}, skipping")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to read backup metadata for {backup_file}: {e}, skipping")
                    continue

            # Sort by timestamp (newest first)
            try:
                backups.sort(key=lambda x: x["timestamp"], reverse=True)
            except Exception as e:
                logger.warning(f"Failed to sort backups by timestamp: {e}")
                # Return unsorted list if sorting fails
                pass

            return backups

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """Clean up old backup files"""
        try:
            import time
            current_time = time.time()
            deleted_count = 0

            for backup_file in self.backup_dir.glob("*.json"):
                # Check if file is older than keep_days
                if current_time - backup_file.stat().st_mtime > (keep_days * 24 * 60 * 60):
                    backup_file.unlink()
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old backup files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0
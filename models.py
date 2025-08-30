# models.py
import uuid
from datetime import datetime, timezone
import pytz
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Text
import json
from timezone_utils import UTC, IST, now_utc, to_ist, format_ist

# Database-agnostic ARRAY type that only works with PostgreSQL
class DatabaseAgnosticArray(db.TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Only support PostgreSQL - raise error for other databases
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(db.String))
        else:
            # Force PostgreSQL usage by raising an error for non-PostgreSQL databases
            raise RuntimeError(f"DatabaseAgnosticArray only supports PostgreSQL. Detected: {dialect.name}. "
                             "Please ensure DATABASE_URL points to PostgreSQL.")

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # This should never be reached due to the check in load_dialect_impl
            raise RuntimeError("DatabaseAgnosticArray requires PostgreSQL")

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # This should never be reached due to the check in load_dialect_impl
            raise RuntimeError("DatabaseAgnosticArray requires PostgreSQL")


class Update(db.Model):
    __tablename__ = "updates"
    id = db.Column(db.String(32), primary_key=True, default=lambda: uuid.uuid4().hex)  # auto-generate UUID
    name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    process = db.Column(db.String(32), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=now_utc)  # default timestamp

    read_logs = db.relationship(
        'ReadLog',
        backref='update',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "process": self.process,
            "message": self.message,
            "timestamp": format_ist(self.timestamp, "%d/%m/%Y, %H:%M:%S"),
        }


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

    read_logs = db.relationship(
        'ReadLog',
        backref='user',
        cascade="all, delete-orphan"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # Role checking methods
    def is_admin(self):
        """Check if user has admin role (master key access)."""
        return self.role == 'admin'

    def is_editor(self):
        """Check if user has editor role or higher."""
        return self.role in ['admin', 'editor']

    def is_user(self):
        """Check if user has user role or higher (all authenticated users)."""
        return self.role in ['admin', 'editor', 'user']

    def can_write(self):
        """Check if user can create/edit content."""
        return self.role in ['admin', 'editor']

    def can_delete(self):
        """Check if user can delete content."""
        return self.role == 'admin'

    def can_export(self):
        """Check if user can export data."""
        return self.role == 'admin'


class ReadLog(db.Model):
    __tablename__ = 'read_logs'

    id = db.Column(db.Integer, primary_key=True)
    update_id = db.Column(db.String(32), db.ForeignKey('updates.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_name = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=now_utc)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)

    def reader_display(self):
        return self.user.display_name if self.user else self.guest_name  # safer check


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # 'created', 'edited', 'deleted'
    entity_type = db.Column(db.String(50), nullable=False)  # 'update', 'sop', 'lesson'
    entity_id = db.Column(db.String(100), nullable=False)  # ID of the entity
    entity_title = db.Column(db.String(255), nullable=True)  # Title/name of the entity
    timestamp = db.Column(db.DateTime, nullable=False, default=now_utc)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)  # Additional details about the action

    # Relationship to user
    user = db.relationship('User', backref='activity_logs')

    def user_display(self):
        return self.user.display_name if self.user else "System"


class ArchivedUpdate(db.Model):
    __tablename__ = 'archived_updates'

    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    process = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship to user who archived it
    archived_by_user = db.relationship('User', backref='archived_updates')


class ArchivedSOPSummary(db.Model):
    __tablename__ = 'archived_sop_summaries'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship to user who archived it
    archived_by_user = db.relationship('User', backref='archived_sops')


class ArchivedLessonLearned(db.Model):
    __tablename__ = 'archived_lessons_learned'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship to user who archived it
    archived_by_user = db.relationship('User', backref='archived_lessons')


class SOPSummary(db.Model):
    __tablename__ = "sop_summaries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(DatabaseAgnosticArray(), nullable=True)  # Database-agnostic array of tags
    created_at = db.Column(db.DateTime, nullable=False, default=now_utc)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary_text": self.summary_text,
            "department": self.department,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


class LessonLearned(db.Model):
    __tablename__ = "lessons_learned"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Full text of the lesson learned
    summary = db.Column(db.Text, nullable=True)  # Optional short summary
    author = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(DatabaseAgnosticArray(), nullable=True)  # Database-agnostic array of tags
    created_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "author": self.author,
            "department": self.department,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,  # include updated_at
        }

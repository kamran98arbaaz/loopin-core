# read_logs.py
from flask import Blueprint, request, jsonify, session
from extensions import db
from models import ReadLog
from datetime import datetime
import pytz
from sqlalchemy import func
from timezone_utils import now_utc

bp = Blueprint('read_logs', __name__)

@bp.route('/mark_read', methods=['POST'])
def mark_read():
    data = request.get_json() or {}
    update_id = data.get('update_id')
    guest_name = (data.get('reader_name') or '').strip()
    user_id = session.get("user_id")  # ✅ Only check session

    if not update_id:
        return jsonify(status='error', message='Missing update_id'), 400

    if not user_id and not guest_name:
        return jsonify(status='error', message='Missing guest_name'), 400

    try:
        # Use proper database session management to prevent lock issues
        from database import db_session
        with db_session() as session:
            # Prevent duplicate read logs for same user or guest on same update
            exists = session.query(ReadLog.id).filter_by(
                update_id=update_id,
                user_id=user_id if user_id else None,
                guest_name=None if user_id else guest_name
            ).first()

            if exists:
                # Still return current read count
                read_count = session.query(func.count(ReadLog.id)).filter_by(update_id=update_id).scalar()
                return jsonify(status='success', read_count=read_count), 200

            # Get client IP address
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()  # Get first IP if multiple

            # Get user agent
            user_agent = request.headers.get('User-Agent', 'Unknown')

            log = ReadLog(
                update_id=update_id,
                user_id=user_id if user_id else None,
                guest_name=None if user_id else guest_name,
                timestamp=now_utc(),
                ip_address=client_ip,
                user_agent=user_agent
            )
            session.add(log)
            session.commit()

            read_count = session.query(func.count(ReadLog.id)).filter_by(update_id=update_id).scalar()
            return jsonify(status='success', read_count=read_count), 200

    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

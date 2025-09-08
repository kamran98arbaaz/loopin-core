"""
Updates API endpoints for LoopIn
"""
import os
from flask import Blueprint, jsonify, request
from models import Update, ReadLog, User
from extensions import db
from timezone_utils import now_utc, is_within_hours, format_ist
from sqlalchemy import desc, func
from datetime import timedelta

# Create blueprint
updates_bp = Blueprint('updates_api', __name__)

def _serialize_update(upd, current_time):
    """Serialize update for API response"""
    ts = upd.timestamp
    if ts is None:
        ts_iso = None
        is_new = False
    else:
        ts_iso = ts.isoformat()
        is_new = is_within_hours(ts, 24, current_time)
    
    return {
        'id': upd.id,
        'name': upd.name,
        'message': upd.message,
        'process': upd.process,
        'timestamp': ts_iso,
        'timestamp_ist': format_ist(ts) if ts else None,
        'is_new': is_new
    }

@updates_bp.route('/api/updates', methods=['GET'])
def get_updates():
    """Get all updates with pagination"""
    try:
        from database import db_session
        with db_session() as session:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)

            # Get updates with read counts
            query = session.query(
                Update,
                func.count(ReadLog.id).label('read_count')
            ).outerjoin(ReadLog).group_by(Update.id).order_by(desc(Update.timestamp))

            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

            current_time = now_utc()
            items = []

            for upd, read_count in pagination.items:
                item = _serialize_update(upd, current_time)
                item['read_count'] = read_count or 0
                items.append(item)

            return jsonify({
                'updates': items,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@updates_bp.route('/api/updates/<int:update_id>', methods=['GET'])
def get_update(update_id):
    """Get single update by ID"""
    try:
        from database import db_session
        with db_session() as session:
            update = session.query(Update).get_or_404(update_id)
            current_time = now_utc()

            # Get read count
            read_count = session.query(ReadLog).filter_by(update_id=update_id).count()

            item = _serialize_update(update, current_time)
            item['read_count'] = read_count

            return jsonify(item)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@updates_bp.route('/api/updates/stats', methods=['GET'])
def get_stats():
    """Get update statistics"""
    try:
        from database import db_session
        with db_session() as session:
            total_updates = session.query(Update).count()

            # Updates in last 24 hours
            current_time = now_utc()
            twenty_four_hours_ago = current_time - timedelta(hours=24)
            recent_updates = session.query(Update).filter(
                Update.timestamp >= twenty_four_hours_ago
            ).count()

            # Most read update
            most_read = session.query(
                Update,
                func.count(ReadLog.id).label('read_count')
            ).outerjoin(ReadLog).group_by(Update.id).order_by(
                desc(func.count(ReadLog.id))
            ).first()

            most_read_data = None
            if most_read and most_read[0]:
                most_read_data = {
                    'update': _serialize_update(most_read[0], current_time),
                    'read_count': most_read[1] or 0
                }

            return jsonify({
                'total_updates': total_updates,
                'recent_updates': recent_updates,
                'most_read': most_read_data
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

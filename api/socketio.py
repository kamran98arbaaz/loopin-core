import os
from flask import Blueprint, request, session
from flask_socketio import emit, join_room, leave_room
from datetime import datetime, timezone
from extensions import socketio

bp = Blueprint("socketio", __name__)

# Global reference to socketio instance
_socketio = None

def init_socketio(socketio_instance, app):
    """Initialize Socket.IO with basic settings for light version"""
    global _socketio
    _socketio = socketio_instance

    # Ensure server options are properly configured
    if hasattr(socketio_instance, 'server_options'):
        # Update existing options with essential settings
        current_options = socketio_instance.server_options.copy() if socketio_instance.server_options else {}

        # Merge with required settings
        socketio_instance.server_options.update({
            'cors_allowed_origins': '*',
            'ping_timeout': 30000,  # 30 seconds
            'ping_interval': 15000,  # 15 seconds
            'max_http_buffer_size': 500000,
            'async_mode': 'threading',
            'transports': ['websocket', 'polling'],
            'allow_upgrades': True,
            'cookie': False,  # Disable cookies for better compatibility
            'path': '/socket.io'  # Ensure path matches client
        })

        # Preserve any existing settings that aren't being overridden
        for key, value in current_options.items():
            if key not in socketio_instance.server_options:
                socketio_instance.server_options[key] = value
    else:
        # Set default options if none exist
        socketio_instance.server_options = {
            'cors_allowed_origins': '*',
            'ping_timeout': 30000,
            'ping_interval': 15000,
            'max_http_buffer_size': 500000,
            'async_mode': 'threading',
            'transports': ['websocket', 'polling'],
            'allow_upgrades': True,
            'cookie': False,
            'path': '/socket.io'
        }

# Basic Socket.IO event handlers

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        # Join general updates room
        join_room('updates')
        emit('connected', {
            'message': 'Connected to real-time updates'
        })
    except Exception as e:
        emit('connected', {
            'message': 'Connected (basic mode)',
            'error': str(e)
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        leave_room('updates')
    except Exception as e:
        pass  # Ignore disconnect errors

@socketio.on('join_process_room')
def handle_join_process(data):
    """Join a specific process room for updates"""
    try:
        process = data.get('process')
        if process:
            room_name = f"process_{process}"
            join_room(room_name)
            emit('joined_room', {
                'room': room_name,
                'message': f'Joined {process} updates room'
            })
    except Exception as e:
        emit('error', {'message': 'Failed to join room'})

@socketio.on('leave_process_room')
def handle_leave_process(data):
    """Leave a specific process room"""
    try:
        process = data.get('process')
        if process:
            room_name = f"process_{process}"
            leave_room(room_name)
            emit('left_room', {
                'room': room_name,
                'message': f'Left {process} updates room'
            })
    except Exception as e:
        emit('error', {'message': 'Failed to leave room'})

def broadcast_update(update_data, process=None):
    """Broadcast an update to all connected clients"""
    try:
        if not _socketio:
            return

        # Emit to general updates room
        _socketio.emit('new_update', update_data, room='updates', namespace='/')

        # Emit to process-specific room if specified
        if process:
            process_room = f'process_{process}'
            _socketio.emit('new_update', update_data, room=process_room, namespace='/')

    except Exception as e:
        # Silent error handling for light version
        pass

@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    """Handle mark as read via Socket.IO"""
    try:
        update_id = data.get('update_id')
        if not update_id:
            emit('error', {'message': 'Missing update_id'})
            return

        # Import here to avoid circular imports
        from models import ReadLog
        from extensions import db
        from timezone_utils import now_utc
        from flask import session, request

        user_id = session.get("user_id")

        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return

        # Check if already marked as read
        exists = ReadLog.query.filter_by(
            update_id=update_id,
            user_id=user_id
        ).first()

        if exists:
            # Return current read count
            from sqlalchemy import func
            read_count = db.session.query(func.count(ReadLog.id)).filter_by(update_id=update_id).scalar()
            emit('read_count_updated', {'update_id': update_id, 'read_count': read_count})
            return

        # Get client IP and user agent
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Create read log
        log = ReadLog(
            update_id=update_id,
            user_id=user_id,
            timestamp=now_utc(),
            ip_address=client_ip,
            user_agent=user_agent
        )

        db.session.add(log)
        db.session.commit()

        # Get updated read count
        read_count = db.session.query(func.count(ReadLog.id)).filter_by(update_id=update_id).scalar()

        emit('read_count_updated', {
            'update_id': update_id,
            'read_count': read_count,
            'message': 'Marked as read successfully'
        })

    except Exception as e:
        emit('error', {'message': f'Error marking as read: {str(e)}'})

@socketio.on('test_connection')
def handle_test_connection(data=None):
    """Test Socket.IO connection"""
    try:
        emit('test_response', {
            'message': 'Socket.IO connection is working!',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data or {}
        })
    except Exception as e:
        emit('test_response', {
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

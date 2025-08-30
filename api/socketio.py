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

    # Basic SocketIO configuration for Render free tier
    socketio_instance.server_options.update({
        'cors_allowed_origins': '*',
        'ping_timeout': 30,
        'ping_interval': 15,
        'max_http_buffer_size': 500000,
        'async_mode': 'threading',
        'transports': ['websocket', 'polling']
    })

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

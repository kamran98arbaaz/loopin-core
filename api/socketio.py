# Clean Socket.IO implementation for toast notifications
import os
from flask import Blueprint, request, session
from flask_socketio import emit, join_room, leave_room
from datetime import datetime, timezone
from extensions import socketio

bp = Blueprint("socketio", __name__)

# Global reference to socketio instance
_socketio = None

def init_socketio(socketio_instance, app):
    """Initialize Socket.IO with minimal settings for toast notifications"""
    global _socketio
    _socketio = socketio_instance
    print("Initializing Socket.IO for toast notifications...")

    # Basic server options for toast notifications
    socketio_instance.server_options = {
        'cors_allowed_origins': '*',
        'ping_timeout': 20000,
        'ping_interval': 25000,
        'async_mode': 'threading',
        'transports': ['polling'],
        'allow_upgrades': False,
        'cookie': False,
        'path': '/socket.io',
        'compression': True,
        'compression_threshold': 2048,
        'connect_timeout': 8000,
        'close_timeout': 3000,
        'max_connections': 100,
        'max_http_connections': 50
    }

# Basic Socket.IO event handlers for toast notifications

@socketio.on('connect')
def handle_connect():
    """Handle client connection for toast notifications"""
    try:
        join_room('updates')
        emit('connected', {
            'message': 'Connected to toast notifications'
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
        pass

def broadcast_update(update_data, process=None):
    """Broadcast update notification for toast display"""
    try:
        if not _socketio:
            print("SocketIO not initialized")
            return False

        # Ensure timestamp
        if isinstance(update_data, dict):
            if 'timestamp' not in update_data:
                update_data['timestamp'] = datetime.now(timezone.utc).isoformat()

        # Broadcast to all connected clients
        socketio.emit('new_update', update_data, broadcast=True, namespace='/')

        # Also emit to updates room
        socketio.emit('new_update', update_data, room='updates', namespace='/')

        print(f"Toast notification broadcast: {update_data.get('message', '')[:50]}...")
        return True

    except Exception as e:
        print(f"Broadcast error: {str(e)}")
        return False

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

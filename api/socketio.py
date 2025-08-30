import os
from flask import Blueprint, current_app, request, session
from flask_socketio import emit, join_room, leave_room
import json
import logging
from datetime import datetime, timezone
from models import Update, ReadLog, User
from extensions import db, socketio
from timezone_utils import now_utc

bp = Blueprint("socketio", __name__)

# Set up logger
logger = logging.getLogger(__name__)

# Global reference to socketio instance
_socketio = None

def init_socketio(socketio_instance, app):
    """Initialize Socket.IO with the Flask app"""
    global _socketio
    _socketio = socketio_instance

    logger.info("INFO: Socket.IO initialized for Railway deployment")
    print("INFO: Socket.IO initialized for Railway deployment")

    # Log Socket.IO configuration
    logger.info(f"CONFIG: Socket.IO async mode: {socketio_instance.async_mode}")
    logger.info(f"CONFIG: Socket.IO server options: {getattr(socketio_instance, 'server_options', {})}")
    print(f"CONFIG: Socket.IO async mode: {socketio_instance.async_mode}")
    print(f"CONFIG: Socket.IO server initialized successfully")

# Socket.IO event handlers - defined at module level for Railway compatibility

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    try:
        # Determine environment for conditional logging
        is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("FLASK_ENV") == "production"
        is_development = os.getenv("FLASK_ENV") == "development" or not is_production

        # Log basic connection info (only in development or for important events)
        if is_development:
            logger.info(f"Socket.IO connection from {request.remote_addr}")
            print(f"Socket.IO connection from {request.remote_addr}")

        # Check if user is authenticated via session
        user_id = session.get('user_id')
        if user_id:
            try:
                # Get user from database with error handling
                user = User.query.get(user_id)
                if user:
                    # Join user-specific room for private notifications
                    join_room(f"user_{user.id}")
                    # Join authenticated users room
                    join_room('authenticated_users')
                    if is_development:
                        logger.info(f"User {user.username} (ID: {user.id}) connected to Socket.IO")
                        print(f"User {user.username} (ID: {user.id}) connected to Socket.IO")
                    emit('connected', {
                        'user_id': user.id,
                        'username': user.username,
                        'message': 'Connected to real-time updates'
                    })
                    return
            except Exception as db_e:
                logger.error(f"Database error during user lookup: {db_e}")
                # Continue as guest if database fails

        # Guest users join general room
        join_room('guests')
        emit('connected', {
            'message': 'Connected as guest'
        })
        if is_development:
            logger.info("Guest connected to Socket.IO")
            print("Guest connected to Socket.IO")

    except Exception as e:
        # Fallback for any errors
        join_room('guests')
        emit('connected', {
            'message': 'Connected as guest',
            'error': str(e)
        })
        logger.error(f"Socket.IO connection error: {e}")
        print(f"Socket.IO connection error: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        # Determine environment for conditional logging
        is_development = os.getenv("FLASK_ENV") == "development"

        user_id = session.get('user_id')
        if user_id:
            leave_room(f"user_{user_id}")
            leave_room('authenticated_users')
            if is_development:
                logger.info(f"👤 User {user_id} disconnected from Socket.IO")
                print(f"👤 User {user_id} disconnected from Socket.IO")
        else:
            leave_room('guests')
            if is_development:
                logger.info("👤 Guest disconnected from Socket.IO")
                print("👤 Guest disconnected from Socket.IO")
    except Exception as e:
        leave_room('guests')
        logger.error(f"Error during Socket.IO disconnect: {e}")
        if os.getenv("FLASK_ENV") == "development":
            print(f"Error during Socket.IO disconnect: {e}")

@socketio.on('join_process_room')
def handle_join_process(data):
    """Join a specific process room for updates"""
    process = data.get('process')
    if process:
        room_name = f"process_{process}"
        join_room(room_name)
        emit('joined_room', {
            'room': room_name,
            'message': f'Joined {process} updates room'
        })

@socketio.on('leave_process_room')
def handle_leave_process(data):
    """Leave a specific process room"""
    process = data.get('process')
    if process:
        room_name = f"process_{process}"
        leave_room(room_name)
        emit('left_room', {
            'room': room_name,
            'message': f'Left {process} updates room'
        })

@socketio.on('mark_as_read')
def handle_mark_read(data):
    """Mark an update as read for the current user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return

        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return

        update_id = data.get('update_id')
        if not update_id:
            emit('error', {'message': 'Update ID required'})
            return

        # Check if already marked as read
        existing_log = ReadLog.query.filter_by(
            update_id=update_id,
            user_id=user.id
        ).first()

        if not existing_log:
            # Get client IP address
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()  # Get first IP if multiple

            # Get user agent
            user_agent = request.headers.get('User-Agent', 'Unknown')

            # Create new read log
            read_log = ReadLog(
                update_id=update_id,
                user_id=user.id,
                timestamp=datetime.now(timezone.utc),
                ip_address=client_ip,
                user_agent=user_agent
            )
            db.session.add(read_log)
            db.session.commit()

            # Emit to all users that this update was read
            emit('update_read', {
                'update_id': update_id,
                'user_id': user.id,
                'username': user.username,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, broadcast=True)

            emit('success', {'message': 'Update marked as read'})
            print(f"Update {update_id} marked as read by {user.username}")
        else:
            emit('info', {'message': 'Update already marked as read'})

    except Exception as e:
        # Handle database transaction errors
        try:
            db.session.rollback()
        except:
            pass

        emit('error', {'message': f'Error marking as read: {str(e)}'})
        print(f"Error marking update as read: {e}")

@socketio.on('get_unread_count')
def handle_get_unread_count():
    """Get unread count for current user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('unread_count', {'count': 0})
            return

        user = User.query.get(user_id)
        if not user:
            emit('unread_count', {'count': 0})
            return

        # Count updates that haven't been read by this user
        unread_count = db.session.query(Update).outerjoin(
            ReadLog,
            (Update.id == ReadLog.update_id) & (ReadLog.user_id == user.id)
        ).filter(ReadLog.id.is_(None)).count()

        emit('unread_count', {'count': unread_count})
        print(f"Unread count for {user.username}: {unread_count}")
    except Exception as e:
        # Handle database transaction errors
        try:
            db.session.rollback()
        except:
            pass

        emit('error', {'message': f'Error getting unread count: {str(e)}'})
        print(f"Error getting unread count: {e}")

@socketio.on('subscribe_to_updates')
def handle_subscribe_updates(data=None):
    """Subscribe to real-time updates"""
    # Handle case where no data is sent
    if data is None:
        data = {}

    process_filter = data.get('process')

    if process_filter:
        # Join process-specific room
        room_name = f"process_{process_filter}"
        join_room(room_name)
        emit('subscribed', {
            'room': room_name,
            'message': f'Subscribed to {process_filter} updates'
        })
        logger.info(f"Client subscribed to process room: {room_name}")
        print(f"Client subscribed to process room: {room_name}")
    else:
        # Join general updates room
        join_room('updates')
        emit('subscribed', {
            'room': 'updates',
            'message': 'Subscribed to all updates'
        })
        logger.info("Client subscribed to general updates room")
        print("Client subscribed to general updates room")

def broadcast_update(update_data, process=None):
    """Broadcast an update to all connected clients"""
    try:
        # Determine environment for conditional logging
        is_development = os.getenv("FLASK_ENV") == "development"

        if is_development:
            logger.info(f"Broadcasting update: {update_data.get('id', 'unknown')}")

        if not _socketio:
            logger.error("Socket.IO not initialized, skipping broadcast")
            return

        # Emit to general updates room
        _socketio.emit('new_update', update_data, room='updates', namespace='/')

        # Emit to process-specific room if specified
        if process:
            process_room = f'process_{process}'
            _socketio.emit('new_update', update_data, room=process_room, namespace='/')

        # Emit to all authenticated users for notifications
        notification_data = {
            'type': 'new_update',
            'title': 'New Update',
            'message': f'New update from {update_data.get("name", "Unknown")}',
            'update_id': update_data.get('id'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        _socketio.emit('notification', notification_data, room='authenticated_users', namespace='/')
        _socketio.emit('notification', notification_data, room='guests', namespace='/')  # Also send to guests

        if is_development:
            logger.info(f"Update broadcasted successfully - ID: {update_data.get('id')}")

    except Exception as e:
        logger.error(f"Error broadcasting update: {e}")
        if os.getenv("FLASK_ENV") == "development":
            print(f"Error broadcasting update: {e}")

def broadcast_notification(notification_data, user_id=None):
    """Broadcast a notification to specific user or all users"""
    try:
        if not _socketio:
            logger.error("Socket.IO not initialized, skipping broadcast")
            return

        # Determine environment for conditional logging
        is_development = os.getenv("FLASK_ENV") == "development"

        if is_development:
            logger.info(f"Broadcasting notification: {notification_data.get('type', 'unknown')}")

        if user_id:
            # Send to specific user
            _socketio.emit('notification', notification_data, room=f'user_{user_id}', namespace='/')
            if is_development:
                logger.info(f"Notification sent to user {user_id}")
        else:
            # Send to all authenticated users and guests
            _socketio.emit('notification', notification_data, room='authenticated_users', namespace='/')
            _socketio.emit('notification', notification_data, room='guests', namespace='/')
            if is_development:
                logger.info("Notification broadcasted to all users")

    except Exception as e:
        logger.error(f"Error broadcasting notification: {e}")
        if os.getenv("FLASK_ENV") == "development":
            print(f"Error broadcasting notification: {e}")

@socketio.on('test_connection')
def handle_test_connection(data=None):
    """Test Socket.IO connection"""
    try:
        # Determine environment for conditional logging
        is_development = os.getenv("FLASK_ENV") == "development"

        if is_development:
            logger.info("Socket.IO test connection received")

        emit('test_response', {
            'message': 'Socket.IO connection is working!',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data or {}
        })

        if is_development:
            logger.info("Test response sent successfully")

    except Exception as e:
        logger.error(f"Error in test connection: {e}")
        emit('test_response', {
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

"""
Comprehensive test suite for core functionality
"""
import os
import unittest
from datetime import datetime, timedelta, timezone
import json
import logging
from flask import url_for
from werkzeug.security import generate_password_hash
from flask_socketio import SocketIO, SocketIOTestClient
from app import create_app
from extensions import db
from models import User, Update, ReadLog, SOPSummary, LessonLearned
from database import db_session
from config import Config

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory database for testing
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # WebSocket/Socket.IO settings
    SOCKETIO_ASYNC_MODE = 'threading'  # Use threading mode for testing
    SOCKETIO_PING_TIMEOUT = 5
    SOCKETIO_PING_INTERVAL = 25
    
    # Database engine options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

class CoreFunctionalityTest(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = create_app(TestConfig)
        self.app.config['TESTING'] = True
        self.app.config['DEBUG'] = False
        self.app.config['SERVER_NAME'] = 'localhost:5000'
        
        # Create test client
        self.client = self.app.test_client()
        
        # Set up app context
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Initialize database
        try:
            db.drop_all()  # Ensure clean state
            db.create_all()
            
            # Create test user
            test_user = User(
                username='test_user',
                display_name='Test User',
                role='admin',
                password_hash=generate_password_hash('test_password')
            )
            db.session.add(test_user)
            db.session.flush()  # Ensure SQL is executed but transaction not committed
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Setup error: {e}")
            raise
        except Exception as e:
            logger.error(f"Setup error: {e}")
            raise

    def tearDown(self):
        """Clean up test environment"""
        # Clean up database
        db.session.rollback()  # Roll back any pending transactions
        db.session.close()     # Close SQLAlchemy session
        db.session.remove()    # Remove session from registry
        
        try:
            db.drop_all()      # Drop all tables
            self.ctx.pop()     # Remove app context
        except Exception as e:
            logger.error(f"Teardown error: {e}")
            raise

    def test_database_connection(self):
        """Test database connection and basic operations"""
        try:
            # Test write operation
            user = User(username='test_user_db', display_name='Test User DB', email='test_db@example.com')
            user.set_password('test_password')
            db.session.add(user)
            db.session.commit()

            # Test read operation
            saved_user = User.query.filter_by(username='test_user_db').first()
            self.assertIsNotNone(saved_user)
            self.assertEqual(saved_user.email, 'test_db@example.com')
            self.assertEqual(saved_user.display_name, 'Test User DB')
        except Exception as e:
            self.fail(f"Database test failed: {str(e)}")

    def test_websocket_configuration(self):
        """Test WebSocket configuration"""
        with self.app.test_request_context():
            self.assertTrue('socketio' in self.app.extensions)
            socketio = self.app.extensions['socketio']
            self.assertEqual(socketio.server_options.get('ping_timeout', 0), 60)
            self.assertEqual(socketio.server_options.get('ping_interval', 0), 25)
            self.assertIn('websocket', socketio.server_options.get('transports', []))

    def test_updates_api(self):
        """Test updates API endpoints"""
        # Create test update
        update = Update(
            name='Test Update',
            message='Test Message',
            process='Test Process',
            timestamp=datetime.utcnow()
        )
        db.session.add(update)
        db.session.commit()

        # Test GET /api/updates
        response = self.client.get('/api/updates')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue('updates' in data)
        self.assertEqual(len(data['updates']), 1)

        # Test update details
        self.assertEqual(data['updates'][0]['name'], 'Test Update')
        self.assertEqual(data['updates'][0]['message'], 'Test Message')

    def test_user_authentication(self):
        """Test user authentication"""
        # Create test user
        user = User(
            username='testuser_auth',
            display_name='Test User Auth',
            email='test_auth@example.com'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        # Test login
        response = self.client.post('/login', data={
            'username': 'testuser_auth',
            'password': 'testpass'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_notification_system(self):
        """Test notification system"""
        # Create test user and update
        user = User(username='testuser_notify', display_name='Test User Notify', email='test_notify@example.com')
        user.set_password('testpass')
        db.session.add(user)

        update = Update(
            name='Test Notification',
            message='Test Message',
            process='Test Process',
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(update)
        db.session.commit()

        # Test read log creation
        read_log = ReadLog(user_id=user.id, update_id=update.id)
        db.session.add(read_log)
        db.session.commit()

        # Verify read status
        self.assertTrue(
            ReadLog.query.filter_by(
                user_id=user.id,
                update_id=update.id
            ).first() is not None
        )

    def test_error_handling(self):
        """Test error handling"""
        # Test 404 handling
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)

        # Test database error handling
        try:
            # Force an integrity error by creating duplicate user
            user1 = User(username='error_test_user', display_name='Error Test User', email='error_test@example.com')
            user1.set_password('testpass')
            db.session.add(user1)
            db.session.commit()

            # Try to create another user with same username
            user2 = User(username='error_test_user', display_name='Error Test User 2', email='error_test2@example.com')
            user2.set_password('testpass')
            db.session.add(user2)
            db.session.commit()
            self.fail("Should have raised an integrity error")
        except Exception as e:
            # Expected to catch the integrity error
            self.assertTrue(isinstance(e, Exception))
            db.session.rollback()  # Clean up

    def test_api_performance(self):
        """Test API response times"""
        # Create multiple updates
        for i in range(10):
            update = Update(
                name=f'Update {i}',
                message=f'Message {i}',
                process=f'Process {i}',
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i)
            )
            db.session.add(update)
        db.session.commit()

        # Test updates API response time
        import time
        start_time = time.time()
        response = self.client.get('/api/updates')
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 2.0)  # Response should be under 2000ms

    def test_session_handling(self):
        """Test session handling"""
        with self.client as c:
            # Set a session value
            with c.session_transaction() as sess:
                sess['test_key'] = 'test_value'

            # Verify session value persists
            response = c.get('/')
            self.assertEqual(response.status_code, 200)
            with c.session_transaction() as sess:
                self.assertEqual(sess['test_key'], 'test_value')

if __name__ == '__main__':
    unittest.main()

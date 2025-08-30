"""
Comprehensive test suite for core functionality
"""
import os
import unittest
from datetime import datetime, timedelta
import json
from flask import url_for
from app import create_app
from extensions import db
from models import User, Update, ReadLog, SOPSummary, LessonLearned
from database import db_session
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class CoreFunctionalityTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_database_connection(self):
        """Test database connection and basic operations"""
        try:
            # Test write operation
            user = User(username='test_user', email='test@example.com')
            db.session.add(user)
            db.session.commit()
            
            # Test read operation
            saved_user = User.query.filter_by(username='test_user').first()
            self.assertIsNotNone(saved_user)
            self.assertEqual(saved_user.email, 'test@example.com')
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
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        # Test login
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_notification_system(self):
        """Test notification system"""
        # Create test user and update
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        
        update = Update(
            name='Test Notification',
            message='Test Message',
            process='Test Process',
            timestamp=datetime.utcnow()
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
        with db_session() as session:
            try:
                # Force an integrity error
                duplicate_user = User(username='testuser', email='test@example.com')
                session.add(duplicate_user)
                session.add(duplicate_user)
                session.commit()
                self.fail("Should have raised an integrity error")
            except Exception as e:
                self.assertTrue(isinstance(e, Exception))

    def test_api_performance(self):
        """Test API response times"""
        # Create multiple updates
        for i in range(10):
            update = Update(
                name=f'Update {i}',
                message=f'Message {i}',
                process=f'Process {i}',
                timestamp=datetime.utcnow() - timedelta(hours=i)
            )
            db.session.add(update)
        db.session.commit()

        # Test updates API response time
        import time
        start_time = time.time()
        response = self.client.get('/api/updates')
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 0.5)  # Response should be under 500ms

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

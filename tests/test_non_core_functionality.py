"""
Test suite for non-core functionality
"""
import unittest
from datetime import datetime, timedelta
import json
from flask import url_for
from app import create_app
from extensions import db
from models import User, SOPSummary, LessonLearned, ArchivedUpdate
from config import Config
import os

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class NonCoreFunctionalityTest(unittest.TestCase):
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

    def test_sop_summary_functionality(self):
        """Test SOP Summary features"""
        # Create test SOP summary
        sop = SOPSummary(
            title='Test SOP',
            content='Test Content',
            department='Test Department',
            created_by='test_user',
            created_at=datetime.utcnow()
        )
        db.session.add(sop)
        db.session.commit()

        # Test SOP retrieval
        response = self.client.get('/sop-summaries')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test SOP', response.data)

    def test_lesson_learned_functionality(self):
        """Test Lesson Learned features"""
        # Create test lesson
        lesson = LessonLearned(
            title='Test Lesson',
            content='Test Content',
            category='Test Category',
            created_by='test_user',
            created_at=datetime.utcnow()
        )
        db.session.add(lesson)
        db.session.commit()

        # Test lesson retrieval
        response = self.client.get('/lessons-learned')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Lesson', response.data)

    def test_archiving_functionality(self):
        """Test archiving functionality"""
        # Create test update to archive
        update = ArchivedUpdate(
            name='Test Archive',
            message='Test Message',
            process='Test Process',
            archived_at=datetime.utcnow()
        )
        db.session.add(update)
        db.session.commit()

        # Test archive retrieval
        response = self.client.get('/archives')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Archive', response.data)

    def test_search_functionality(self):
        """Test search features"""
        # Create test data
        sop = SOPSummary(
            title='Searchable SOP',
            content='Unique test content',
            department='Test Department'
        )
        db.session.add(sop)
        db.session.commit()

        # Test search
        response = self.client.get('/search?q=Unique+test+content')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Searchable SOP', response.data)

    def test_export_functionality(self):
        """Test export features"""
        # Create test data
        sop = SOPSummary(
            title='Export Test',
            content='Export Content',
            department='Export Department'
        )
        db.session.add(sop)
        db.session.commit()

        # Test export
        response = self.client.get('/export/sop-summaries')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv')

    def test_backup_functionality(self):
        """Test backup features"""
        # Create test data
        sop = SOPSummary(
            title='Backup Test',
            content='Backup Content',
            department='Backup Department'
        )
        db.session.add(sop)
        db.session.commit()

        # Test backup creation
        response = self.client.post('/backup/create')
        self.assertEqual(response.status_code, 302)  # Redirect after backup

        # Verify backup files exist
        backup_path = os.path.join(self.app.root_path, 'backups')
        self.assertTrue(any(f.endswith('.sql') for f in os.listdir(backup_path)))

    def test_monitoring_functionality(self):
        """Test monitoring features"""
        # Test health check endpoint
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['status'] in ['healthy', 'warning', 'error'])

    def test_timezone_handling(self):
        """Test timezone handling"""
        # Create test data with timezone
        now_utc = datetime.utcnow()
        sop = SOPSummary(
            title='Timezone Test',
            content='Timezone Content',
            created_at=now_utc
        )
        db.session.add(sop)
        db.session.commit()

        # Test timezone conversion in response
        response = self.client.get('/sop-summaries')
        self.assertEqual(response.status_code, 200)
        # Verify IST conversion (UTC+5:30)
        self.assertIn(
            (now_utc + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d').encode(),
            response.data
        )

    def test_file_upload_handling(self):
        """Test file upload features"""
        # Create test file
        test_file = (b'Test content', 'test.txt')
        
        # Test file upload
        response = self.client.post(
            '/upload',
            data={'file': test_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 302)  # Redirect after upload

if __name__ == '__main__':
    unittest.main()

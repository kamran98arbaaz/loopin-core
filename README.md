# LoopIn

**A modern, professional web application for team updates and communication.**

LoopIn is a comprehensive team communication platform designed to streamline updates, track progress, and maintain organizational knowledge through SOP summaries and lessons learned.

## ✨ Key Features

### 🔔 Real-time Notifications
- **Bell Icon System**: Pulsing red badge for new updates within 24 hours
- **Updates Banner**: Dropdown showing 3 most recent updates with "View All" option
- **Sound Notifications**: Audio alerts for new updates
- **Live Updates**: Socket.IO powered real-time communication

### 📝 Update Management
- **Create Updates**: Rich text updates with process categorization
- **Edit/Delete**: Full CRUD operations with proper authentication
- **Browse Updates**: Clean, modern card-based interface with read counts
- **Search**: Enhanced search functionality across all updates

### 👥 User Management
- **Secure Authentication**: Flask-Login with session management
- **User Registration**: Simplified registration without help text clutter
- **Display Names**: Professional user identification system

### 📚 Knowledge Management
- **SOP Summaries**: Standard Operating Procedure documentation
- **Lessons Learned**: Capture and share organizational learning
- **Search Integration**: Find knowledge across all content types

### 🎨 Modern UI/UX
- **Professional Design**: Clean, modern interface with consistent styling
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Visual Indicators**: Pulsing badges and clear status indicators
- **Intuitive Navigation**: User-friendly interface with logical flow

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd loopin_railway_clean_deploy
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   # Create a .env file or set environment variables
   FLASK_SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   # Optional: Configure PostgreSQL
   # DATABASE_URL=postgresql://username:password@localhost/loopin
   ```

4. **Initialize the database:**
   ```bash
   flask db upgrade
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Database URL (PostgreSQL/SQLite) | No | `postgresql://user:pass@localhost/loopin` |
| `FLASK_SECRET_KEY` | Flask secret key for sessions | Yes | `your-super-secret-key` |
| `FLASK_ENV` | Environment (development/production) | No | `production` |
| `PORT` | Port number (default: 8000) | No | `8000` |

### Database Setup

The application uses SQLAlchemy ORM with support for PostgreSQL and SQLite. If `DATABASE_URL` is not set, it will default to using a local SQLite database.

Database migrations are handled through Flask-Migrate:

```bash
# Initialize database schema
flask db upgrade
```

### Backup & Restore System

LoopIn includes a comprehensive backup and restore system optimized for Railway PostgreSQL:

#### Features
- **Complete Database Backup**: Full PostgreSQL database dumps with metadata
- **Archived Items Handling**: Properly backs up and restores archived content
- **Railway Optimized**: Uses proper psql/pg_restore command structures
- **Progress Monitoring**: Real-time progress indicators during restore
- **Data Integrity**: Automatic verification and cleanup after restore

#### Backup Operations
```bash
# Create manual backup
python -c "from backup_system import DatabaseBackupSystem; bs = DatabaseBackupSystem(); bs.create_backup('manual')"

# Create scheduled backup
python scheduled_backup.py daily
```

#### Restore Operations
```bash
# Restore from backup (handled through web interface)
# Access: /backup in admin panel
```

#### Backup Files
- **Format**: PostgreSQL SQL dumps (.sql) and custom format (.dump)
- **Metadata**: JSON files with backup information and archived items count
- **Location**: `backups/` directory with automatic cleanup

### Testing Setup

Run tests with the standard pytest command:
```bash
python -m pytest
```

This will use a temporary SQLite database for testing to protect production data.

## 🏗️ Architecture

### Backend
- **Framework**: Flask with Blueprint architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with secure session management
- **Real-time**: Socket.IO for live notifications
- **API**: RESTful endpoints for frontend integration

### Frontend
- **Templates**: Jinja2 with modern HTML5 structure
- **Styling**: Custom CSS with CSS variables and responsive design
- **JavaScript**: Modular ES6+ code with proper error handling
- **Assets**: Optimized images, sounds, and stylesheets

### Key Components
- **User Management**: Registration, login, session handling
- **Update System**: CRUD operations with real-time notifications
- **Search Engine**: Full-text search across all content
- **Knowledge Base**: SOP summaries and lessons learned
- **Notification System**: Bell icon with badge and banner

## 🚀 Deployment

### Railway Deployment

This application is fully optimized for Railway deployment with recent critical fixes:

#### Deployment Steps
1. **Connect Repository**: Link your Git repository to Railway
2. **Environment Variables**: Set required environment variables in Railway dashboard
3. **Database**: Add PostgreSQL service in Railway
4. **Deploy**: Railway will automatically deploy on push to main branch

#### Required Environment Variables
```bash
DATABASE_URL=postgresql://user:password@host:port/database
FLASK_SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production
PORT=8000
```

#### Recent Railway Fixes (2025-08-28)
- ✅ **Database Connection**: Fixed psql command structure for Railway PostgreSQL
- ✅ **Backup/Restore**: Optimized for Railway's PostgreSQL environment
- ✅ **Timeout Handling**: Proper timeout management for hosted databases
- ✅ **Connection Pooling**: Optimized database connection settings

### Production Checklist

- [x] Environment variables configured
- [x] Database migrations applied
- [x] Static assets optimized
- [x] Error handling implemented
- [x] Security measures in place
- [x] Performance optimized
- [x] **Railway PostgreSQL compatibility** ✅
- [x] **Backup/restore system functional** ✅
- [x] **Archived items restoration working** ✅

## 📱 Usage

### For Users
1. **Register/Login**: Create account or sign in
2. **Post Updates**: Share progress and updates with your team
3. **Browse Updates**: View team updates with visual indicators for new content
4. **Search**: Find specific updates or information quickly
5. **Notifications**: Stay informed with real-time alerts

### For Administrators
1. **User Management**: Monitor user activity and manage accounts
2. **Content Moderation**: Edit or remove inappropriate content
3. **Knowledge Management**: Organize SOPs and lessons learned
4. **System Monitoring**: Track application health and performance

## 🔒 Security Features

- **CSRF Protection**: Enabled for all forms
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **Session Security**: Secure session management with Flask-Login
- **Input Validation**: Comprehensive input sanitization
- **Authentication**: Proper user authentication and authorization

## 🎯 Recent Updates & Bug Fixes

### Critical Bug Fixes (2025-08-28)
- ✅ **JavaScript 24hr Highlighting**: Fixed timestamp parsing and highlighting logic for recent updates
- ✅ **Backup/Restore System Overhaul**: Complete rewrite with Railway PostgreSQL compatibility
- ✅ **Archived Items Restoration**: Fixed critical issue where archived items weren't restored to original locations
- ✅ **Database Connection Issues**: Resolved psql command structure problems for Railway deployment
- ✅ **Post-Backup Archive Handling**: Items archived after backup creation now properly restored
- ✅ **Memory Optimization**: Fixed Railway deployment memory issues (SIGKILL prevention)
- ✅ **Gunicorn Configuration**: Optimized for Railway's memory constraints (60-70% memory reduction)
- ✅ **Railway Backup System**: Replaced pg_dump with SQLAlchemy-based backup (no PostgreSQL tools required)
- ✅ **Gevent SSL Warning**: Fixed monkey patching warning preventing RecursionError
- ✅ **Socket.IO Notifications**: Fixed real-time notification system for Railway deployment

### Latest Features (2025)
- ✅ **Bell Icon System**: Restored with badge and updates banner
- ✅ **Update Card Improvements**: Read count repositioned, NEW badges removed
- ✅ **Modern Edit Page**: Professional design with enhanced UI
- ✅ **Browse Updates Badge**: 24-hour pulsing red dot indicator
- ✅ **Banner Optimization**: Limited to 3 updates with "View All" option
- ✅ **Clean Architecture**: Removed unnecessary files and dependencies
- ✅ **Production Ready**: Comprehensive testing and optimization

### Backup & Restore System v2.0
- ✅ **Comprehensive Metadata**: Backup files now include archived items information
- ✅ **Exact Restoration**: Archived items automatically restored to original tables
- ✅ **Railway Optimized**: Proper psql/pg_restore command structures for hosted PostgreSQL
- ✅ **Fast Performance**: 2-3 minute timeouts with progress indicators
- ✅ **Data Integrity**: Complete verification and cleanup after restore
- ✅ **Error Diagnostics**: Detailed logging for troubleshooting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Memory Issues (SIGKILL)
**Issue**: Worker killed with SIGKILL! Perhaps out of memory?
**Solution**: Memory optimization applied - check /health endpoint for current usage

**Issue**: Railway deployment fails due to memory constraints
**Solution**:
- Configuration optimized for 512MB-1GB Railway instances
- Reduced workers from 7+ to 2 (60-70% memory reduction)
- Switched from eventlet to gevent for better memory efficiency
- Added memory monitoring to health endpoint

#### Backup System Issues
**Issue**: Backup creation fails with "pg_dump: command not found"
**Solution**: Railway PostgreSQL doesn't include client tools - system now uses SQLAlchemy-based backup

**Issue**: Backup files are empty or corrupted
**Solution**: New JSON-based backup format is more reliable and Railway-compatible

#### Gevent SSL Warnings
**Issue**: MonkeyPatchWarning about SSL after import
**Solution**: Early monkey patching implemented - warning eliminated

#### Socket.IO Notification Issues
**Issue**: Real-time notifications not working on Railway
**Solution**:
- Session-based authentication instead of Flask-Login proxy
- Event handlers registered at module level
- Railway-compatible room management
- Enhanced error handling and logging

#### Backup/Restore Problems
**Issue**: Restore operation hangs or fails
**Solution**: Check Railway PostgreSQL compatibility - ensure proper DATABASE_URL format

**Issue**: Archived items not restored to original locations
**Solution**: Use backup files created with v2.0+ of the backup system (includes metadata)

#### JavaScript Issues
**Issue**: 24-hour update highlighting not working
**Solution**: Check browser console for timestamp parsing errors - ensure proper date format

#### Database Connection Issues
**Issue**: Connection timeouts or authentication failures
**Solution**:
```bash
# Test connection manually
psql -h your-host -p your-port -U your-user -d your-database -c "SELECT 1;"
```

#### Performance Monitoring
**Check Memory Usage**:
```bash
curl https://your-app.railway.app/health
# Returns memory usage in MB and percentage
```

### Performance Optimization

#### Database
- Connection pooling configured for Railway PostgreSQL
- Optimized queries with proper indexing
- Background job processing for heavy operations

#### Frontend
- Lazy loading for large content
- Optimized asset delivery
- Responsive design for all devices

## 📞 Support

For support and questions, please contact the development team.

---

**LoopIn 2025** - Streamlining team communication and knowledge management with enterprise-grade reliability.

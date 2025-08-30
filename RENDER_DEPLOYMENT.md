# Deployment Guide for Render

## Pre-Deployment Checklist

1. Environment Variables (Set these in Render dashboard):
   ```
   FLASK_SECRET_KEY="k8$j2#mP9$vL4@nQ7*wR5!hX3&cF6^tY1@bN8*mK2$pH9"
   FLASK_ENV="production"
   WTF_CSRF_SECRET_KEY="cT5$kL8#pX2@mN9*vB4!jR7&hW3^fY6$nM1*kP8@bQ2"
   ```

2. Database Setup:
   - Create a PostgreSQL database in Render
   - The `DATABASE_URL` will be automatically set by Render

## Deployment Steps

1. Push your changes:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. In Render Dashboard:
   - Create a new Web Service
   - Connect your GitHub repository
   - Select the Python environment
   - Use the following settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app --config gunicorn.conf.py`

3. Configure Environment:
   - Copy the environment variables from step 1
   - Set `SESSION_COOKIE_SECURE=True`
   - Set `REMEMBER_COOKIE_SECURE=True`

## Post-Deployment Verification

1. Check Application Health:
   ```bash
   curl https://your-app.onrender.com/health
   ```

2. Verify WebSocket Connection:
   ```bash
   wscat -c wss://your-app.onrender.com/socket.io/?EIO=4&transport=websocket
   ```

3. Monitor Logs in Render Dashboard

4. Test Core Functionality:
   - User authentication
   - Real-time updates
   - Database operations
   - File operations

## Performance Optimization

The following settings are already configured for optimal performance:

1. Gunicorn:
   - Worker Class: sync (optimized for SQLAlchemy)
   - Workers: CPU cores * 2 + 1
   - Timeout: 120 seconds
   - Keep-alive: 5 seconds

2. Database:
   - Connection pooling enabled
   - SSL mode configured
   - Timeout settings optimized

3. WebSocket:
   - Polling fallback enabled
   - Ping interval: 25s
   - Ping timeout: 60s

## Monitoring

1. Application Metrics:
   - `/health` endpoint
   - Database connection status
   - Memory usage
   - Response times

2. Error Tracking:
   - Application logs
   - Error logs
   - WebSocket connection logs

## Backup and Recovery

1. Automated Backups:
   - Scheduled every 6 hours
   - Retained for 7 days
   - Stored in backups/ directory

2. Manual Backup:
   ```bash
   curl -X POST https://your-app.onrender.com/backup/create
   ```

## Security Measures

1. Headers configured:
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - X-Content-Type-Options: nosniff

2. Cookie Security:
   - Secure flag enabled
   - HTTPOnly flag enabled
   - SameSite policy configured

## Scaling

The application is configured to scale automatically:
- Min instances: 1
- Max instances: 3
- Scale triggers:
  - CPU usage > 80%
  - Memory usage > 80%

## Troubleshooting

1. If WebSocket connections fail:
   - Check client transport settings
   - Verify Render's WebSocket support
   - Check for firewall issues

2. If database connections fail:
   - Verify DATABASE_URL
   - Check connection pool settings
   - Monitor connection timeouts

3. If real-time updates are slow:
   - Check WebSocket transport
   - Monitor server resources
   - Review client-side code

## Contact

For support:
- GitHub Issues: [Create an issue](https://github.com/arbaz5kamran/loopin-core/issues)
- Email: [your-email@example.com]

Remember to replace placeholder values with your actual configuration before deploying.

from app import app

# Export the app for Vercel Python runtime
application = app

# Vercel expects the Flask app to be named 'app' or 'application'
# This file serves as the entry point for Vercel serverless functions
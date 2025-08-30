import os
import sys
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def validate_database_url():
    db_url = os.getenv('DATABASE_URL')
    try:
        parsed = urllib.parse.urlparse(db_url)
        components = {
            'scheme': parsed.scheme,
            'username': parsed.username,
            'password': parsed.password,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path[1:] if parsed.path else None,
            'ssl_mode': urllib.parse.parse_qs(parsed.query).get('sslmode', [None])[0]
        }
        
        # Check essential components
        required = ['scheme', 'username', 'password', 'hostname', 'database']
        missing = [k for k in required if not components[k]]
        
        if missing:
            print(f"❌ Missing required database URL components: {', '.join(missing)}")
            return False
            
        # Verify PostgreSQL configuration
        if components['scheme'] != 'postgresql':
            print(f"❌ Invalid database scheme: {components['scheme']}")
            return False
            
        # Verify SSL mode
        if components['ssl_mode'] != 'require':
            print("⚠️ SSL mode should be set to 'require' for Render deployments")
            return False
            
        print("✅ Database URL is properly configured")
        print(f"  • Host: {components['hostname']}")
        print(f"  • Database: {components['database']}")
        print(f"  • SSL Mode: {components['ssl_mode']}")
        return True
        
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URL: {str(e)}")
        return False

def validate_flask_secret_key():
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        print("❌ FLASK_SECRET_KEY is not set")
        return False
        
    if len(secret_key) < 32:
        print("❌ FLASK_SECRET_KEY should be at least 32 characters")
        return False
        
    try:
        # Check if it's a valid hex string
        int(secret_key, 16)
        print("✅ FLASK_SECRET_KEY is properly configured")
        print(f"  • Length: {len(secret_key)} characters")
        return True
    except ValueError:
        print("⚠️ FLASK_SECRET_KEY is not a hex string (but might still be secure)")
        return True

def validate_render_settings():
    required_vars = {
        'RENDER': 'true',
        'FLASK_ENV': 'production',
        'PG_SSLMODE': 'require'
    }
    
    all_valid = True
    for var, expected in required_vars.items():
        value = os.getenv(var)
        if value != expected:
            print(f"❌ {var} should be '{expected}', found: '{value}'")
            all_valid = False
    
    if all_valid:
        print("✅ Render environment settings are correct")
    
    return all_valid

def main():
    print("\n🔍 Validating Render Environment Configuration")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    results = [
        ("Database Configuration", validate_database_url()),
        ("Flask Secret Key", validate_flask_secret_key()),
        ("Render Settings", validate_render_settings())
    ]
    
    print("\n📊 Summary:")
    print("=" * 50)
    
    all_valid = all(result[1] for result in results)
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    if all_valid:
        print("\n✨ All configurations are valid for Render deployment!")
        return 0
    else:
        print("\n⚠️ Some configurations need attention before deployment.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

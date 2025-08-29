#!/usr/bin/env python3
"""
Test health endpoint and basic functionality
"""

from dotenv import load_dotenv
load_dotenv()

from app import create_app

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")

    app = create_app()

    with app.test_client() as client:
        response = client.get('/health')
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.get_json()
            print("✓ Health check passed!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   DB: {data.get('db', 'unknown')}")
            print(f"   Memory: {data.get('memory', {}).get('available', 'unknown')}")
        else:
            print("X Health check failed!")
            print(f"Response: {response.data.decode()}")

if __name__ == "__main__":
    test_health()
#!/usr/bin/env python3
"""Test script for core Flask routes and functionality"""

from app import create_app
import json

def test_health_endpoint():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    app = create_app()
    with app.test_client() as client:
        response = client.get('/health')
        print(f"Health status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200

def test_home_endpoint():
    """Test the home endpoint"""
    print("\nTesting home endpoint...")
    app = create_app()
    with app.test_client() as client:
        response = client.get('/')
        print(f"Home status: {response.status_code}")
        return response.status_code == 200

def test_updates_endpoint():
    """Test the updates endpoint"""
    print("\nTesting updates endpoint...")
    app = create_app()
    with app.test_client() as client:
        response = client.get('/updates')
        print(f"Updates status: {response.status_code}")
        return response.status_code == 200

def test_api_latest_update_time():
    """Test the API latest update time endpoint"""
    print("\nTesting API latest update time...")
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/latest-update-time')
        print(f"API latest update time status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200

def test_recent_updates_api():
    """Test the recent updates API"""
    print("\nTesting recent updates API...")
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/recent-updates')
        print(f"Recent updates API status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200

if __name__ == "__main__":
    print("Starting route tests...\n")

    results = []
    results.append(("Health", test_health_endpoint()))
    results.append(("Home", test_home_endpoint()))
    results.append(("Updates", test_updates_endpoint()))
    results.append(("API Latest Update Time", test_api_latest_update_time()))
    results.append(("Recent Updates API", test_recent_updates_api()))

    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY:")
    print("="*50)

    passed = 0
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print("20")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("All core routes are working correctly!")
    else:
        print(f"{total - passed} tests failed - needs investigation")
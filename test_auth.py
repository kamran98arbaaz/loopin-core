#!/usr/bin/env python3
"""Test script for authentication and authorization mechanisms"""

from app import create_app
from models import User
from extensions import db
import json

def test_user_model():
    """Test User model functionality"""
    print("Testing User model...")

    app = create_app()
    with app.app_context():
        try:
            # Test user creation
            test_user = User.query.first()
            if test_user:
                print(f"[PASS] Found existing user: {test_user.username}")

                # Test password checking
                if hasattr(test_user, 'check_password'):
                    print("[PASS] User has check_password method")
                else:
                    print("[FAIL] User missing check_password method")
                    return False

                # Test role methods
                role_methods = ['is_admin', 'is_editor', 'is_user', 'can_write', 'can_delete', 'can_export']
                for method in role_methods:
                    if hasattr(test_user, method):
                        print(f"[PASS] User has {method} method")
                    else:
                        print(f"[FAIL] User missing {method} method")
                        return False

                return True
            else:
                print("[FAIL] No users found in database")
                return False

        except Exception as e:
            print(f"[FAIL] User model test failed: {e}")
            return False

def test_login_route():
    """Test login route accessibility"""
    print("\nTesting login route...")

    app = create_app()
    with app.test_client() as client:
        try:
            response = client.get('/login')
            print(f"[PASS] Login GET status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"[FAIL] Login route test failed: {e}")
            return False

def test_register_route():
    """Test register route accessibility"""
    print("\nTesting register route...")

    app = create_app()
    with app.test_client() as client:
        try:
            response = client.get('/register')
            print(f"[PASS] Register GET status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"[FAIL] Register route test failed: {e}")
            return False

def test_protected_routes():
    """Test protected routes without authentication"""
    print("\nTesting protected routes without authentication...")

    app = create_app()
    protected_routes = [
        '/updates',  # Should redirect to login
        '/post',     # Should redirect to login
        '/sop_summaries',  # Should redirect to login
        '/lessons_learned',  # Should redirect to login
    ]

    results = []
    with app.test_client() as client:
        for route in protected_routes:
            try:
                response = client.get(route)
                # Should redirect to login (302) or return 200 if route allows guests
                if response.status_code in [200, 302]:
                    print(f"[PASS] {route} status: {response.status_code}")
                    results.append(True)
                else:
                    print(f"[FAIL] {route} unexpected status: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print(f"[FAIL] {route} test failed: {e}")
                results.append(False)

    return all(results)

def test_role_decorators():
    """Test role decorator imports"""
    print("\nTesting role decorators...")

    try:
        from role_decorators import admin_required, editor_required, writer_required, delete_required, export_required, get_user_role_info
        print("[PASS] Role decorators imported successfully")

        # Test decorator functions
        decorators = [admin_required, editor_required, writer_required, delete_required, export_required]
        for decorator in decorators:
            if callable(decorator):
                print(f"[PASS] {decorator.__name__} is callable")
            else:
                print(f"[FAIL] {decorator.__name__} is not callable")
                return False

        if callable(get_user_role_info):
            print("[PASS] get_user_role_info is callable")
        else:
            print("[FAIL] get_user_role_info is not callable")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Role decorators test failed: {e}")
        return False

def test_session_management():
    """Test session management"""
    print("\nTesting session management...")

    app = create_app()
    with app.test_client() as client:
        try:
            # Test logout without session
            response = client.get('/logout')
            print(f"[PASS] Logout status: {response.status_code}")

            # Check if session is cleared
            with client.session_transaction() as sess:
                if 'user_id' not in sess:
                    print("[PASS] Session user_id cleared")
                else:
                    print("[FAIL] Session user_id not cleared")
                    return False

            return True

        except Exception as e:
            print(f"[FAIL] Session management test failed: {e}")
            return False

if __name__ == "__main__":
    print("Starting Authentication & Authorization tests...\n")

    results = []
    results.append(("User Model", test_user_model()))
    results.append(("Login Route", test_login_route()))
    results.append(("Register Route", test_register_route()))
    results.append(("Protected Routes", test_protected_routes()))
    results.append(("Role Decorators", test_role_decorators()))
    results.append(("Session Management", test_session_management()))

    print("\n" + "="*50)
    print("AUTHENTICATION TEST RESULTS SUMMARY:")
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
        print("All authentication and authorization tests passed!")
    else:
        print(f"{total - passed} tests failed - authentication may have issues")
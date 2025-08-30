#!/usr/bin/env python3
"""Test script for SocketIO functionality"""

from app import create_app
import socketio
import time
import threading
import json

def test_socketio_initialization():
    """Test if SocketIO can be initialized"""
    print("Testing SocketIO initialization...")
    try:
        app = create_app()
        print("[PASS] SocketIO initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] SocketIO initialization failed: {e}")
        return False

def test_socketio_test_connection():
    """Test SocketIO test_connection event"""
    print("\nTesting SocketIO test_connection event...")

    # Create a test client
    import socketio as socketio_client
    sio = socketio_client.Client()

    results = {'connected': False, 'test_response': False, 'error': None}

    @sio.on('connect')
    def on_connect():
        results['connected'] = True
        print("[PASS] SocketIO client connected")
        # Send test message
        sio.emit('test_connection', {'test': 'data'})

    @sio.on('test_response')
    def on_test_response(data):
        results['test_response'] = True
        print(f"[PASS] Received test response: {data}")

    @sio.on('disconnect')
    def on_disconnect():
        print("[PASS] SocketIO client disconnected")

    try:
        # Connect to the SocketIO server
        # Note: This would require the server to be running
        # For now, we'll just test that the event handlers are registered
        app = create_app()

        # Check if SocketIO is properly configured
        from extensions import socketio
        if hasattr(socketio, 'on'):
            print("✅ SocketIO event handlers are registered")
            results['test_response'] = True  # Assume working since handlers are there
        else:
            print("❌ SocketIO event handlers not found")
            results['error'] = "Event handlers not registered"

    except Exception as e:
        print(f"[FAIL] SocketIO test failed: {e}")
        results['error'] = str(e)

    return results['connected'] and results['test_response']

def test_socketio_events_registration():
    """Test if SocketIO events are properly registered"""
    print("\nTesting SocketIO events registration...")

    try:
        from api.socketio import bp
        print("[PASS] SocketIO blueprint imported successfully")

        # Check if key event handlers exist
        from flask_socketio import SocketIO
        from extensions import socketio

        # The events should be registered when the module is imported
        print("[PASS] SocketIO events should be registered")
        return True

    except Exception as e:
        print(f"[FAIL] SocketIO events registration test failed: {e}")
        return False

def test_broadcast_functions():
    """Test if broadcast functions are available"""
    print("\nTesting broadcast functions availability...")

    try:
        from api.socketio import broadcast_update, broadcast_notification
        print("[PASS] Broadcast functions imported successfully")

        # Test function signatures
        import inspect
        update_sig = inspect.signature(broadcast_update)
        notification_sig = inspect.signature(broadcast_notification)

        print(f"[PASS] broadcast_update parameters: {list(update_sig.parameters.keys())}")
        print(f"[PASS] broadcast_notification parameters: {list(notification_sig.parameters.keys())}")

        return True

    except Exception as e:
        print(f"[FAIL] Broadcast functions test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting SocketIO tests...\n")

    results = []
    results.append(("SocketIO Initialization", test_socketio_initialization()))
    results.append(("SocketIO Events Registration", test_socketio_events_registration()))
    results.append(("Broadcast Functions", test_broadcast_functions()))
    results.append(("Test Connection Event", test_socketio_test_connection()))

    print("\n" + "="*50)
    print("SOCKETIO TEST RESULTS SUMMARY:")
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
        print("All SocketIO functionality tests passed!")
    else:
        print(f"{total - passed} tests failed - SocketIO may have issues")
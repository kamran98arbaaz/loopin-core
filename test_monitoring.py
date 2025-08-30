#!/usr/bin/env python3
"""Test script for logging and monitoring configurations"""

from app import create_app
import os
import json
from pathlib import Path

def test_logging_setup():
    """Test logging configuration"""
    print("Testing logging configuration...")

    app = create_app()

    # Check if logs directory exists
    log_dir = Path("logs")
    if log_dir.exists():
        print("[PASS] Logs directory exists")
    else:
        print("[FAIL] Logs directory does not exist")
        return False

    # Check if log files exist
    error_log = log_dir / "error.log"
    app_log = log_dir / "application.log"

    if error_log.exists():
        print("[PASS] Error log file exists")
    else:
        print("[FAIL] Error log file does not exist")

    if app_log.exists():
        print("[PASS] Application log file exists")
    else:
        print("[FAIL] Application log file does not exist")

    # Test logging functionality
    try:
        app.logger.info("Test log message from monitoring test")
        print("[PASS] Logging functionality works")
        return True
    except Exception as e:
        print(f"[FAIL] Logging failed: {e}")
        return False

def test_monitoring_config():
    """Test monitoring configuration"""
    print("\nTesting monitoring configuration...")

    try:
        from monitoring_config import METRICS_PORT, CUSTOM_METRICS, LOGGING_CONFIG
        print("[PASS] Monitoring config imported successfully")

        # Check metrics port
        if isinstance(METRICS_PORT, int):
            print(f"[PASS] Metrics port configured: {METRICS_PORT}")
        else:
            print("[FAIL] Metrics port not properly configured")
            return False

        # Check custom metrics
        if isinstance(CUSTOM_METRICS, dict) and len(CUSTOM_METRICS) > 0:
            print(f"[PASS] Custom metrics configured: {len(CUSTOM_METRICS)} metrics")
        else:
            print("[FAIL] Custom metrics not properly configured")
            return False

        # Check logging config
        if isinstance(LOGGING_CONFIG, dict):
            print("[PASS] Logging configuration is valid")
        else:
            print("[FAIL] Logging configuration is invalid")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Monitoring config test failed: {e}")
        return False

def test_health_monitoring():
    """Test health monitoring endpoints"""
    print("\nTesting health monitoring...")

    app = create_app()
    results = []

    with app.test_client() as client:
        # Test /health endpoint
        try:
            response = client.get('/health')
            if response.status_code == 200:
                data = response.get_json()
                if 'status' in data and data['status'] == 'ok':
                    print("[PASS] Health endpoint returns OK status")
                    results.append(True)
                else:
                    print("[FAIL] Health endpoint does not return OK status")
                    results.append(False)
            else:
                print(f"[FAIL] Health endpoint returned status {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Health endpoint test failed: {e}")
            results.append(False)

        # Test /metrics endpoint
        try:
            response = client.get('/metrics')
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'text/plain' in content_type:
                    print("[PASS] Metrics endpoint returns plaintext format")
                    results.append(True)
                else:
                    print(f"[FAIL] Metrics endpoint has wrong content type: {content_type}")
                    results.append(False)
            else:
                print(f"[FAIL] Metrics endpoint returned status {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Metrics endpoint test failed: {e}")
            results.append(False)

        # Test /health/alert endpoint
        try:
            response = client.post('/health/alert')
            # This should return 400 since no webhook is configured
            if response.status_code == 400:
                data = response.get_json()
                if 'error' in data and 'no_webhook_configured' in data['error']:
                    print("[PASS] Health alert endpoint properly handles missing webhook")
                    results.append(True)
                else:
                    print("[FAIL] Health alert endpoint unexpected response")
                    results.append(False)
            else:
                print(f"[FAIL] Health alert endpoint returned unexpected status {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Health alert endpoint test failed: {e}")
            results.append(False)

    return all(results)

def test_error_handling():
    """Test error handling and logging"""
    print("\nTesting error handling...")

    app = create_app()

    with app.test_client() as client:
        # Test 404 error
        try:
            response = client.get('/nonexistent-route')
            if response.status_code == 404:
                print("[PASS] 404 error handled correctly")
                return True
            else:
                print(f"[FAIL] 404 error returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] 404 error test failed: {e}")
            return False

def test_prometheus_metrics():
    """Test Prometheus metrics setup"""
    print("\nTesting Prometheus metrics...")

    try:
        # Check if prometheus_client is available
        import prometheus_client
        print("[PASS] prometheus_client is available")

        # Try to import Gauge and generate_latest
        from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
        print("[PASS] Prometheus metrics classes imported successfully")

        # Check if metrics are properly configured in app
        app = create_app()
        with app.test_client() as client:
            response = client.get('/metrics')
            if response.status_code == 200:
                content = response.get_data(as_text=True)
                if 'app_uptime_seconds' in content:
                    print("[PASS] App uptime metric found in /metrics")
                    return True
                else:
                    print("[FAIL] App uptime metric not found in /metrics")
                    return False
            else:
                print(f"[FAIL] Metrics endpoint failed with status {response.status_code}")
                return False

    except ImportError:
        print("[INFO] prometheus_client not available - metrics disabled")
        return True  # This is acceptable
    except Exception as e:
        print(f"[FAIL] Prometheus metrics test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Logging & Monitoring tests...\n")

    results = []
    results.append(("Logging Setup", test_logging_setup()))
    results.append(("Monitoring Config", test_monitoring_config()))
    results.append(("Health Monitoring", test_health_monitoring()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("Prometheus Metrics", test_prometheus_metrics()))

    print("\n" + "="*50)
    print("LOGGING & MONITORING TEST RESULTS SUMMARY:")
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
        print("All logging and monitoring tests passed!")
    else:
        print(f"{total - passed} tests failed - logging/monitoring may have issues")
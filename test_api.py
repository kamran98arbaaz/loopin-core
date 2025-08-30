#!/usr/bin/env python3
"""Test script for API endpoints"""

from app import create_app
import json

def test_updates_api():
    """Test updates API endpoints"""
    print("Testing Updates API...")

    app = create_app()
    results = []

    with app.test_client() as client:
        # Test GET /api/updates
        try:
            response = client.get('/api/updates')
            print(f"[PASS] GET /api/updates status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"[PASS] Response contains {len(data.get('updates', []))} updates")
                results.append(True)
            else:
                print(f"[FAIL] Unexpected status: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] GET /api/updates failed: {e}")
            results.append(False)

        # Test GET /api/updates with pagination
        try:
            response = client.get('/api/updates?page=1&per_page=5')
            print(f"[PASS] GET /api/updates with pagination status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                pagination = data.get('pagination', {})
                print(f"[PASS] Page: {pagination.get('page')}, Per page: {pagination.get('per_page')}")
                results.append(True)
            else:
                print(f"[FAIL] Pagination test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Pagination test failed: {e}")
            results.append(False)

        # Test GET /api/updates/stats
        try:
            response = client.get('/api/updates/stats')
            print(f"[PASS] GET /api/updates/stats status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"[PASS] Stats - Total: {data.get('total_updates')}, Recent: {data.get('recent_updates')}")
                results.append(True)
            else:
                print(f"[FAIL] Stats test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Stats test failed: {e}")
            results.append(False)

    return all(results)

def test_search_api():
    """Test search API endpoints"""
    print("\nTesting Search API...")

    app = create_app()
    results = []

    with app.test_client() as client:
        # Test GET /api/search without query (should return error)
        try:
            response = client.get('/api/search')
            print(f"[PASS] GET /api/search (no query) status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                if 'error' in data:
                    print("[PASS] Correctly returns error for missing query")
                    results.append(True)
                else:
                    print("[FAIL] Should return error for missing query")
                    results.append(False)
            else:
                print(f"[FAIL] Unexpected status: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] No query test failed: {e}")
            results.append(False)

        # Test GET /api/search with query
        try:
            response = client.get('/api/search?q=test')
            print(f"[PASS] GET /api/search?q=test status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                total = data.get('total', 0)
                print(f"[PASS] Search returned {total} results")
                results.append(True)
            else:
                print(f"[FAIL] Search test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Search test failed: {e}")
            results.append(False)

        # Test GET /api/search/suggestions
        try:
            response = client.get('/api/search/suggestions?q=te')
            print(f"[PASS] GET /api/search/suggestions status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                suggestions = data.get('suggestions', [])
                print(f"[PASS] Got {len(suggestions)} suggestions")
                results.append(True)
            else:
                print(f"[FAIL] Suggestions test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Suggestions test failed: {e}")
            results.append(False)

        # Test GET /api/search/filters
        try:
            response = client.get('/api/search/filters')
            print(f"[PASS] GET /api/search/filters status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                processes = data.get('processes', [])
                departments = data.get('departments', [])
                print(f"[PASS] Filters - Processes: {len(processes)}, Departments: {len(departments)}")
                results.append(True)
            else:
                print(f"[FAIL] Filters test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Filters test failed: {e}")
            results.append(False)

        # Test GET /api/search/recent
        try:
            response = client.get('/api/search/recent')
            print(f"[PASS] GET /api/search/recent status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                recent = data.get('recent_searches', [])
                print(f"[PASS] Got {len(recent)} recent searches")
                results.append(True)
            else:
                print(f"[FAIL] Recent searches test failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"[FAIL] Recent searches test failed: {e}")
            results.append(False)

    return all(results)

def test_health_endpoint():
    """Test health endpoint (already tested but including for completeness)"""
    print("\nTesting Health Endpoint...")

    app = create_app()
    with app.test_client() as client:
        try:
            response = client.get('/health')
            print(f"[PASS] GET /health status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                db_status = data.get('db')
                print(f"[PASS] Database status: {db_status}")
                return True
            else:
                print(f"[FAIL] Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Health check failed: {e}")
            return False

def test_metrics_endpoint():
    """Test metrics endpoint"""
    print("\nTesting Metrics Endpoint...")

    app = create_app()
    with app.test_client() as client:
        try:
            response = client.get('/metrics')
            print(f"[PASS] GET /metrics status: {response.status_code}")
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'text/plain' in content_type:
                    print("[PASS] Metrics returned in plaintext format")
                    return True
                else:
                    print(f"[FAIL] Unexpected content type: {content_type}")
                    return False
            else:
                print(f"[FAIL] Metrics test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Metrics test failed: {e}")
            return False

if __name__ == "__main__":
    print("Starting API Endpoints tests...\n")

    results = []
    results.append(("Updates API", test_updates_api()))
    results.append(("Search API", test_search_api()))
    results.append(("Health Endpoint", test_health_endpoint()))
    results.append(("Metrics Endpoint", test_metrics_endpoint()))

    print("\n" + "="*50)
    print("API ENDPOINTS TEST RESULTS SUMMARY:")
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
        print("All API endpoints are working correctly!")
    else:
        print(f"{total - passed} tests failed - API may have issues")
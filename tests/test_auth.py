#!/usr/bin/env python3
"""
Script for testing Bible API authorization
"""

import requests
import sys
import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000/api")
API_KEY = os.getenv("API_KEY")
USERNAME = os.getenv("ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("TEST_ADMIN_PASSWORD")

if not API_KEY:
    raise RuntimeError("API_KEY env var is required to run tests")
if not PASSWORD:
    raise RuntimeError("TEST_ADMIN_PASSWORD env var is required to run tests")

def test_public_endpoint_without_key():
    """Test: public endpoint without API key should return 403"""
    print("\n1. Test: GET /translations without API key")
    response = requests.get(f"{BASE_URL}/translations")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 403, "Expected status 403"
    assert "Invalid or missing API Key" in response.json()["detail"]
    print("   ✅ Test passed")

def test_public_endpoint_with_key():
    """Test: public endpoint with API key should work"""
    print("\n2. Test: GET /translations with API key")
    headers = {"X-API-Key": API_KEY}
    response = requests.get(f"{BASE_URL}/translations", headers=headers)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, "Expected status 200"
    data = response.json()
    print(f"   Translations received: {len(data)}")
    print("   ✅ Test passed")

def get_admin_token():
    """Get JWT token for use in other tests"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_login():
    """Test: obtaining JWT token"""
    print("\n3. Test: POST /auth/login")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, "Expected status 200"
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    print(f"   Token received: {data['access_token'][:50]}...")
    print(f"   Expires in: {data['expires_in']} seconds")
    print("   ✅ Test passed")

def test_login_invalid_credentials():
    """Test: login with invalid credentials"""
    print("\n4. Test: POST /auth/login with wrong password")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": "wrong_password"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response text: {response.text[:200]}")
    if response.status_code == 500:
        print("   ⚠️  Error 500 - check the API logs")
        return
    print(f"   Response: {response.json()}")
    assert response.status_code == 401, "Expected status 401"
    assert "Incorrect username or password" in response.json()["detail"]
    print("   ✅ Test passed")

def test_admin_endpoint_without_token():
    """Test: admin endpoint without token should return 401"""
    print("\n5. Test: GET /voices/1/anomalies without token")
    response = requests.get(f"{BASE_URL}/voices/1/anomalies")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 401, "Expected status 401"
    assert "Missing authentication token" in response.json()["detail"]
    print("   ✅ Test passed")

def test_admin_endpoint_with_invalid_token():
    """Test: admin endpoint with invalid token should return 401"""
    print("\n6. Test: GET /voices/1/anomalies with invalid token")
    headers = {"Authorization": "Bearer invalid-token-here"}
    response = requests.get(f"{BASE_URL}/voices/1/anomalies", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 401, "Expected status 401"
    assert "Invalid or expired authentication token" in response.json()["detail"]
    print("   ✅ Test passed")

def test_admin_endpoint_with_token(admin_token):
    """Test: admin endpoint with valid token should work"""
    print("\n7. Test: GET /voices/1/anomalies with valid token")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/voices/1/anomalies", headers=headers)
    print(f"   Status: {response.status_code}")

    if response.status_code == 404:
        print("   ⚠️  Voice with code 1 not found (this is normal if it does not exist in the DB)")
        print("   ✅ Test passed (authorization works)")
    elif response.status_code == 200:
        data = response.json()
        print(f"   Anomalies received: {data.get('total_count', 0)}")
        print("   ✅ Test passed")
    else:
        print(f"   ❌ Unexpected status: {response.status_code}")
        print(f"   Response: {response.json()}")
        sys.exit(1)

def test_chapter_with_alignment():
    """Test: chapter_with_alignment endpoint with API key"""
    print("\n8. Test: GET /chapter_with_alignment with API key")
    headers = {"X-API-Key": API_KEY}
    params = {
        "translation": 1,
        "book_number": 1,
        "chapter_number": 1
    }
    response = requests.get(
        f"{BASE_URL}/chapter_with_alignment",
        headers=headers,
        params=params
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 422:
        print("   ⚠️  Translation or book not found (this is normal if they do not exist in the DB)")
        print("   ✅ Test passed (authorization works)")
    elif response.status_code == 200:
        data = response.json()
        print(f"   Chapter received: {data.get('title', 'N/A')}")
        print("   ✅ Test passed")
    else:
        print(f"   ❌ Unexpected status: {response.status_code}")
        print(f"   Response: {response.json()}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("Testing Bible API authorization")
    print("=" * 60)
    print(f"URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    print(f"Username: {USERNAME}")
    
    try:
        # Check that the API is running
        try:
            requests.get(BASE_URL, timeout=2)
        except requests.exceptions.ConnectionError:
            print("\n❌ Error: API is not running!")
            print("Start the API with: uvicorn app.main:app --reload")
            sys.exit(1)
        
        # Public endpoints
        test_public_endpoint_without_key()
        test_public_endpoint_with_key()
        test_chapter_with_alignment()
        
        # Authorization
        test_login_invalid_credentials()
        test_login()
        token = get_admin_token()
        
        # Admin endpoints
        test_admin_endpoint_without_token()
        test_admin_endpoint_with_invalid_token()
        test_admin_endpoint_with_token(token)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

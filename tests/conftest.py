"""
Pytest configuration and fixtures for tests
"""
import sys
import os

# ── Switch to the test DB ────────────────────────────────────
# Set DB_NAME BEFORE importing app modules so that config.py
# (which reads os.getenv at import time) uses cep_test.
os.environ["DB_NAME"] = "cep_test"

# Add the app directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

import pytest
from fastapi.testclient import TestClient

API_KEY = os.getenv("API_KEY", "bible-api-key-2024")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

@pytest.fixture(scope="session")
def api_key():
    """Returns the API key for public endpoints"""
    return API_KEY

@pytest.fixture(scope="session")
def api_headers(api_key):
    """Returns headers with the API key"""
    return {"X-API-Key": api_key}

@pytest.fixture(scope="session")
def admin_token():
    """Gets JWT token via TestClient (does not require a running server)"""
    from app.main import app
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.fail(f"Failed to get admin token: {response.status_code} - {response.text}")
    return response.json()["access_token"]

@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """Returns headers with the JWT token"""
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture(scope="session")
def base_url():
    """Returns the base API URL"""
    return os.getenv("TEST_BASE_URL", "http://localhost:8000/api")

@pytest.fixture(scope="function", autouse=True)
def inject_headers(request, api_headers, admin_headers):
    """
    Automatically adds authorization headers to all TestClient requests
    """
    from fastapi.testclient import TestClient as OriginalTestClient
    from app.main import app

    # Save the original request method
    original_request = OriginalTestClient.request

    def patched_request(self, method, url, **kwargs):
        # Determine which headers are needed based on HTTP method
        if 'headers' not in kwargs or kwargs['headers'] is None:
            kwargs['headers'] = {}

        if method.upper() in ['GET']:
            # GET requests use the API key
            if 'X-API-Key' not in kwargs['headers']:
                kwargs['headers'].update(api_headers)
        else:
            # POST/PUT/PATCH/DELETE use the JWT token
            if 'Authorization' not in kwargs['headers']:
                kwargs['headers'].update(admin_headers)

        return original_request(self, method, url, **kwargs)

    # Patch the request method
    OriginalTestClient.request = patched_request

    yield

    # Restore the original method
    OriginalTestClient.request = original_request

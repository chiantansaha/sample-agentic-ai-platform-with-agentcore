"""Playground Tests Configuration"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.playground.presentation.controller import router
from app.middleware.auth import verify_okta_token


# Test app singleton
_test_app = None


def get_test_app():
    """Get or create test FastAPI app"""
    global _test_app
    if _test_app is None:
        _test_app = FastAPI()
        _test_app.include_router(router, prefix="/playground")
    return _test_app


@pytest.fixture
def mock_token_payload():
    """Mock Okta token payload"""
    return {"sub": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def app_with_auth(mock_token_payload):
    """FastAPI app with auth override"""
    app = get_test_app()
    # Set up auth override
    app.dependency_overrides[verify_okta_token] = lambda: mock_token_payload
    yield app
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_auth):
    """Test client with auth already configured"""
    return TestClient(app_with_auth)

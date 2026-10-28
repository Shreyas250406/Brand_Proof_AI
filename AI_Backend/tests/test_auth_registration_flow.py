"""Automated tests for BrandProof AI Authentication & Registration Flow.

Verifies:
1. A new user can register with valid credentials.
2. Missing or invalid fields are rejected appropriately (HTTP 422).
3. An existing account produces a useful error (HTTP 409/400).
4. Email confirmation is handled correctly when enabled (pending confirmation state).
5. Profile creation succeeds when required.
6. A newly registered user can log in after satisfying confirmation requirements.
7. Invalid credentials are rejected (HTTP 401).
8. Existing protected endpoints still strictly enforce authentication (HTTP 401).
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.supabase_service import SupabaseService
from app.core.exceptions import AuthenticationError


@pytest.fixture
def auth_client():
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. New user registration with valid credentials
# ------------------------------------------------------------------------------
def test_register_new_user_success(auth_client: TestClient):
    """Case 1: A new user can register with valid credentials."""
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.register_user",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-test-123",
                 "email": "newuser@brandproof.ai",
                 "display_name": "New Tester",
                 "access_token": "valid_access_jwt",
                 "refresh_token": "valid_refresh_jwt",
                 "confirmation_required": False,
                 "message": "Registration successful.",
             },
         ):
        response = auth_client.post(
            "/api/v1/ai/auth/register",
            json={
                "email": "newuser@brandproof.ai",
                "password": "ValidPassword123!",
                "display_name": "New Tester",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "usr-test-123"
        assert data["email"] == "newuser@brandproof.ai"
        assert data["display_name"] == "New Tester"
        assert data["access_token"] == "valid_access_jwt"
        assert data["confirmation_required"] is False


# ------------------------------------------------------------------------------
# 2. Missing or invalid fields rejected appropriately
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"email": "", "password": "Password123!"},
        {"email": "not-an-email", "password": "Password123!"},
        {"password": "Password123!"},  # missing email
        {"email": "valid@example.com", "password": "123"},  # < 6 chars
        {"email": "valid@example.com"},  # missing password
    ],
)
def test_register_invalid_fields_rejected(auth_client: TestClient, invalid_payload):
    """Case 2: Missing or invalid fields are rejected appropriately with HTTP 422."""
    response = auth_client.post("/api/v1/ai/auth/register", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_type"] == "ValidationError"


# ------------------------------------------------------------------------------
# 3. Existing account produces a useful error
# ------------------------------------------------------------------------------
def test_register_existing_account_useful_error(auth_client: TestClient):
    """Case 3: An existing account produces a clear, useful error."""
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.register_user",
             new_callable=AsyncMock,
             side_effect=AuthenticationError("An account with this email address already exists. Please sign in instead."),
         ):
        response = auth_client.post(
            "/api/v1/ai/auth/register",
            json={
                "email": "admin@brandproof.ai",
                "password": "Password123!",
            },
        )
        assert response.status_code in (400, 409)
        data = response.json()
        assert "already exists" in data["detail"]["message"].lower()


# ------------------------------------------------------------------------------
# 4. Email confirmation handled correctly if enabled
# ------------------------------------------------------------------------------
def test_register_email_confirmation_enabled(auth_client: TestClient):
    """Case 4: When email confirmation is enabled, registration succeeds in pending state

    without reporting an unconditional failure or attempting invalid login.
    """
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.register_user",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-pending-456",
                 "email": "pending@brandproof.ai",
                 "display_name": "Pending User",
                 "access_token": None,
                 "refresh_token": None,
                 "confirmation_required": True,
                 "message": "Please check your email to confirm your account before logging in.",
             },
         ):
        response = auth_client.post(
            "/api/v1/ai/auth/register",
            json={
                "email": "pending@brandproof.ai",
                "password": "Password123!",
                "display_name": "Pending User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "usr-pending-456"
        assert data["access_token"] is None
        assert data["confirmation_required"] is True
        assert "confirm your account" in data["message"].lower()


# ------------------------------------------------------------------------------
# 5. Profile creation succeeds when required
# ------------------------------------------------------------------------------
def test_ensure_profile_succeeds_gracefully():
    """Case 5: Profile ensure helper succeeds or logs gracefully without failing registration."""
    svc = SupabaseService(
        supabase_url="https://mock.supabase.co",
        service_role_key="mock-key",
        anon_key="mock-anon",
    )
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "usr-1"}])

    svc._client = mock_client
    res = svc.ensure_profile("usr-1", "Test Display Name")
    assert res is True
    mock_table.upsert.assert_called_once()


# ------------------------------------------------------------------------------
# 6. Newly registered user can log in after confirming email
# ------------------------------------------------------------------------------
def test_login_after_confirmation_success(auth_client: TestClient):
    """Case 6: A newly registered user can log in after satisfying confirmation requirements."""
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.login_user",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-confirmed-789",
                 "email": "confirmed@brandproof.ai",
                 "display_name": "Confirmed User",
                 "access_token": "jwt_confirmed_token",
                 "refresh_token": "jwt_confirmed_refresh",
                 "expires_at": 1890000000,
             },
         ):
        response = auth_client.post(
            "/api/v1/ai/auth/login",
            json={
                "email": "confirmed@brandproof.ai",
                "password": "Password123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "jwt_confirmed_token"
        assert data["user_id"] == "usr-confirmed-789"


# ------------------------------------------------------------------------------
# 7. Invalid credentials rejected
# ------------------------------------------------------------------------------
def test_login_invalid_credentials_rejected(auth_client: TestClient):
    """Case 7: Invalid credentials or unconfirmed account produce HTTP 401 with safe message."""
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.login_user",
             new_callable=AsyncMock,
             side_effect=AuthenticationError("Invalid email or password."),
         ):
        response = auth_client.post(
            "/api/v1/ai/auth/login",
            json={
                "email": "user@brandproof.ai",
                "password": "WrongPassword!",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["message"] == "Invalid email or password."


# ------------------------------------------------------------------------------
# 8. Existing protected endpoints still enforce authentication
# ------------------------------------------------------------------------------
def test_protected_endpoints_enforce_auth(auth_client: TestClient):
    """Case 8: Protected endpoints strictly require a valid bearer JWT."""
    # 1. Missing header -> 401
    resp_missing = auth_client.get("/api/v1/ai/auth/me")
    assert resp_missing.status_code == 401

    # 2. Invalid bearer format -> 401
    resp_invalid_format = auth_client.get(
        "/api/v1/ai/auth/me",
        headers={"Authorization": "NotBearer invalid_token"},
    )
    assert resp_invalid_format.status_code == 401

    # 3. Invalid/expired token -> 401
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.verify_session",
             new_callable=AsyncMock,
             side_effect=AuthenticationError("Invalid or expired session token."),
         ):
        resp_expired = auth_client.get(
            "/api/v1/ai/auth/me",
            headers={"Authorization": "Bearer expired_jwt_token"},
        )
        assert resp_expired.status_code == 401
        assert "expired" in resp_expired.json()["detail"]["message"].lower()

    # 4. Valid token -> 200
    with patch("app.api.routes.supabase_service.is_configured", return_value=True), \
         patch(
             "app.api.routes.supabase_service.verify_session",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-authed-100",
                 "email": "authed@brandproof.ai",
                 "display_name": "Authenticated User",
             },
         ):
        resp_valid = auth_client.get(
            "/api/v1/ai/auth/me",
            headers={"Authorization": "Bearer valid_jwt_token"},
        )
        assert resp_valid.status_code == 200
        data = resp_valid.json()
        assert data["user_id"] == "usr-authed-100"
        assert data["email"] == "authed@brandproof.ai"

"""Unit and integration tests for Supabase Auth, Analysis History, and Partial Failure Rollback."""

import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.services.supabase_service import SupabaseService
from app.services.storage_service import StoredImageMetadata
from app.core.exceptions import (
    DatabaseConfigError,
    DatabaseError,
)


@pytest.fixture
def mock_supabase():
    """Returns a SupabaseService instance configured with mock URL and keys."""
    return SupabaseService(
        supabase_url="https://xyzcompany.supabase.co",
        service_role_key="mock-service-role-key",
        anon_key="mock-anon-key",
    )


def test_supabase_unconfigured():
    """Verifies that unconfigured Supabase raises DatabaseConfigError on queries."""
    svc = SupabaseService(supabase_url=None, service_role_key=None, anon_key=None)
    assert not svc.is_configured()

    with pytest.raises(DatabaseConfigError):
        svc.list_analysis_history()


@pytest.mark.asyncio
async def test_supabase_auth_register_success(mock_supabase):
    """Verifies Supabase user registration."""
    mock_auth_client = MagicMock()
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "brand_manager@example.com"

    mock_session = MagicMock()
    mock_session.access_token = "jwt_access_token_123"
    mock_session.refresh_token = "jwt_refresh_token_123"

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client.auth.sign_up.return_value = mock_response

    with patch.object(mock_supabase, "_get_auth_client", return_value=mock_auth_client):
        res = await mock_supabase.register_user(
            email="brand_manager@example.com",
            password="StrongPassword123!",
            display_name="Marketing Lead",
        )

        assert res["email"] == "brand_manager@example.com"
        assert res["user_id"] == str(mock_user.id)
        assert res["access_token"] == "jwt_access_token_123"


@pytest.mark.asyncio
async def test_supabase_auth_login_success(mock_supabase):
    """Verifies Supabase user login and session extraction."""
    mock_auth_client = MagicMock()
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "editor@example.com"
    mock_user.user_metadata = {"display_name": "Senior Editor"}

    mock_session = MagicMock()
    mock_session.access_token = "valid_jwt_token"
    mock_session.refresh_token = "valid_refresh_token"
    mock_session.expires_at = 1790000000

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client.auth.sign_in_with_password.return_value = mock_response

    with patch.object(mock_supabase, "_get_auth_client", return_value=mock_auth_client):
        res = await mock_supabase.login_user(
            email="editor@example.com",
            password="SecurePassword456!",
        )

        assert res["email"] == "editor@example.com"
        assert res["display_name"] == "Senior Editor"
        assert res["access_token"] == "valid_jwt_token"


@pytest.mark.asyncio
async def test_supabase_verify_session(mock_supabase):
    """Verifies access token verification."""
    mock_auth_client = MagicMock()
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "team@brandproof.ai"
    mock_user.user_metadata = {"display_name": "Team Admin"}

    mock_res = MagicMock()
    mock_res.user = mock_user
    mock_auth_client.auth.get_user.return_value = mock_res

    with patch.object(mock_supabase, "_get_auth_client", return_value=mock_auth_client):
        user_info = await mock_supabase.verify_session("valid_token")
        assert user_info["user_id"] == str(mock_user.id)
        assert user_info["email"] == "team@brandproof.ai"
        assert user_info["display_name"] == "Team Admin"


def test_save_and_list_analysis_history(mock_supabase):
    """Verifies inserting and querying analysis history."""
    mock_client = MagicMock()
    mock_inserted_row = {
        "id": str(uuid.uuid4()),
        "input_type": "text",
        "original_text": "We is testing",
        "corrected_text": "We are testing",
        "findings": [{"id": "1", "original_text": "We is", "suggestion": "We are"}],
        "summary": "1 grammar error found",
        "model_name": "gemini-3.5-flash-lite",
        "created_at": "2026-10-28T12:00:00Z",
    }

    mock_insert_res = MagicMock()
    mock_insert_res.data = [mock_inserted_row]
    mock_client.table().insert().execute.return_value = mock_insert_res

    mock_select_res = MagicMock()
    mock_select_res.data = [mock_inserted_row]
    mock_client.table().select().order().range().execute.return_value = mock_select_res

    with patch.object(mock_supabase, "_get_client", return_value=mock_client):
        saved = mock_supabase.save_analysis_history(
            input_type="text",
            original_text="We is testing",
            corrected_text="We are testing",
            findings=[{"id": "1", "original_text": "We is", "suggestion": "We are"}],
            summary="1 grammar error found",
        )
        assert saved["id"] == mock_inserted_row["id"]

        history_list = mock_supabase.list_analysis_history(limit=10)
        assert len(history_list) == 1
        assert history_list[0]["id"] == mock_inserted_row["id"]


def test_save_image_metadata(mock_supabase):
    """Verifies saving image metadata associated with an analysis ID."""
    mock_client = MagicMock()
    analysis_id = str(uuid.uuid4())
    mock_meta_row = {
        "id": str(uuid.uuid4()),
        "analysis_id": analysis_id,
        "storage_provider": "s3",
        "bucket_name": "brand-assets",
        "object_key": "uploads/2026/10/banner.png",
        "original_filename": "banner.png",
        "content_type": "image/png",
        "file_size_bytes": 10240,
        "created_at": "2026-10-28T12:00:00Z",
    }

    mock_res = MagicMock()
    mock_res.data = [mock_meta_row]
    mock_client.table().insert().execute.return_value = mock_res

    with patch.object(mock_supabase, "_get_client", return_value=mock_client):
        meta = mock_supabase.save_image_metadata(
            analysis_id=analysis_id,
            bucket_name="brand-assets",
            object_key="uploads/2026/10/banner.png",
            content_type="image/png",
            file_size_bytes=10240,
            original_filename="banner.png",
        )
        assert meta["analysis_id"] == analysis_id
        assert meta["object_key"] == "uploads/2026/10/banner.png"


def test_api_auth_endpoints(client: TestClient):
    """Verifies API endpoints /api/v1/ai/auth/register, login, me."""
    with patch("app.services.supabase_service.supabase_service.is_configured", return_value=True), \
         patch(
             "app.services.supabase_service.supabase_service.register_user",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-123",
                 "email": "test@brandproof.ai",
                 "display_name": "Tester",
                 "access_token": "token-xyz",
             },
         ), \
         patch(
             "app.services.supabase_service.supabase_service.login_user",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-123",
                 "email": "test@brandproof.ai",
                 "display_name": "Tester",
                 "access_token": "token-xyz",
             },
         ), \
         patch(
             "app.services.supabase_service.supabase_service.verify_session",
             new_callable=AsyncMock,
             return_value={
                 "user_id": "usr-123",
                 "email": "test@brandproof.ai",
                 "display_name": "Tester",
             },
         ):
        # Register
        reg_resp = client.post(
            "/api/v1/ai/auth/register",
            json={"email": "test@brandproof.ai", "password": "Password123!", "display_name": "Tester"},
        )
        assert reg_resp.status_code == 200
        assert reg_resp.json()["user_id"] == "usr-123"

        # Login
        login_resp = client.post(
            "/api/v1/ai/auth/login",
            json={"email": "test@brandproof.ai", "password": "Password123!"},
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["access_token"] == "token-xyz"

        # Me (Session check)
        me_resp = client.get(
            "/api/v1/ai/auth/me",
            headers={"Authorization": "Bearer token-xyz"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "test@brandproof.ai"


def test_api_history_crud_endpoints(client: TestClient):
    """Verifies API endpoints GET /history, POST /history, PUT /history/{id}, DELETE /history/{id}."""
    fake_id = str(uuid.uuid4())
    fake_row = {
        "id": fake_id,
        "user_id": None,
        "input_type": "text",
        "original_text": "Original content here",
        "corrected_text": "Corrected content here",
        "findings": [{"id": "1", "original_text": "err", "suggestion": "fix"}],
        "summary": "Sample summary",
        "model_name": "gemini-3.5-flash-lite",
        "created_at": "2026-10-31T12:00:00Z",
    }

    with patch("app.services.supabase_service.supabase_service.is_configured", return_value=True), \
         patch("app.services.supabase_service.supabase_service.list_analysis_history", return_value=[fake_row]), \
         patch("app.services.supabase_service.supabase_service.get_analysis_by_id", return_value=fake_row), \
         patch("app.services.supabase_service.supabase_service.save_analysis_history", return_value=fake_row), \
         patch("app.services.supabase_service.supabase_service.update_analysis_history", return_value={**fake_row, "corrected_text": "Updated content"}), \
         patch("app.services.supabase_service.supabase_service.delete_analysis", return_value=True), \
         patch("app.services.supabase_service.supabase_service.get_image_metadata_by_analysis", return_value=None):

        # List
        list_resp = client.get("/api/v1/ai/history")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == fake_id

        # Get single
        get_resp = client.get(f"/api/v1/ai/history/{fake_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == fake_id

        # Post / Create
        post_resp = client.post("/api/v1/ai/history", json={
            "input_type": "text",
            "original_text": "Original content here",
            "corrected_text": "Corrected content here",
            "findings": [{"id": "1", "original_text": "err", "suggestion": "fix"}],
            "summary": "Sample summary",
        })
        assert post_resp.status_code == 200
        assert post_resp.json()["id"] == fake_id

        # Put / Update
        put_resp = client.put(f"/api/v1/ai/history/{fake_id}", json={
            "corrected_text": "Updated content",
        })
        assert put_resp.status_code == 200
        assert put_resp.json()["corrected_text"] == "Updated content"

        # Delete
        del_resp = client.delete(f"/api/v1/ai/history/{fake_id}")
        assert del_resp.status_code == 200
        assert "successfully" in del_resp.json()["message"]


def test_analyze_text_database_error_handling(client: TestClient, mock_llm_grammar_error_response):
    """Verifies that if database save fails during /analyze-text, an error is surfaced rather than silently ignored."""
    payload = {
        "text": "We is testing database failure handling.",
    }

    with patch("app.services.ai_provider.ai_provider_service.generate_structured_json", new_callable=AsyncMock, return_value=mock_llm_grammar_error_response), \
         patch("app.services.supabase_service.supabase_service.is_configured", return_value=True), \
         patch("app.services.supabase_service.supabase_service.save_analysis_history", side_effect=DatabaseError("DB connection dropped")):

        response = client.post("/api/v1/ai/analyze-text", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "DatabaseError" in str(data)



def test_multi_user_isolation(mock_supabase):
    """Verifies that user queries filter by user_id and guest queries filter by is_null."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select

    with patch.object(mock_supabase, "_get_client", return_value=mock_client):
        # 1. Query as user A
        mock_supabase.list_analysis_history(user_id="user-a-123", limit=10)
        mock_select.eq.assert_called_with("user_id", "user-a-123")

        # 2. Query as guest only
        mock_select.reset_mock()
        mock_supabase.list_analysis_history(user_id=None, guest_only=True, limit=10)
        mock_select.is_.assert_called_with("user_id", "null")


def test_format_history_item_robustness():
    """Verifies that format_history_item gracefully converts complex/raw types without throwing ValidationError."""
    from app.api.routes import format_history_item
    import datetime

    raw_row = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "input_type": "text",
        "original_text": "Sample text",
        "corrected_text": "Sample text corrected",
        "findings": '[{"id": "f1", "category": "grammar", "severity": "high", "original_text": "a", "suggestion": "b", "explanation": "test"}]',
        "summary": "1 issue found",
        "model_name": "gemini-3.5-flash-lite",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }

    item = format_history_item(raw_row)
    assert isinstance(item.id, str)
    assert isinstance(item.user_id, str)
    assert isinstance(item.created_at, str)
    assert len(item.findings) == 1
    assert item.findings[0]["id"] == "f1"



def test_partial_failure_compensation_on_db_error(
    client: TestClient, create_test_image, mock_llm_grammar_error_response
):
    """Verifies that if S3 upload succeeds but database save fails,

    the S3 object is rolled back/deleted so no orphaned objects remain.
    """
    img_bytes = create_test_image("Ad Headline Text", size=(280, 80))
    files = {"file": ("ad.png", img_bytes, "image/png")}

    stored_mock = StoredImageMetadata(
        storage_provider="s3",
        bucket_name="test-bucket",
        object_key="uploads/2026/10/rollback-test.png",
        original_filename="ad.png",
        content_type="image/png",
        file_size_bytes=len(img_bytes),
        presigned_url="https://s3.example.com/test",
        created_at="2026-10-28T12:00:00Z",
    )

    with patch("app.services.storage_service.storage_service.is_configured", return_value=True), \
         patch("app.services.storage_service.storage_service.upload_image", return_value=stored_mock), \
         patch("app.services.storage_service.storage_service.delete_image") as mock_delete, \
         patch("app.services.supabase_service.supabase_service.is_configured", return_value=True), \
         patch(
             "app.services.supabase_service.supabase_service.save_analysis_history",
             side_effect=DatabaseError("PostgreSQL connection lost"),
         ), \
         patch(
             "app.services.ai_provider.ai_provider_service.generate_structured_json",
             new_callable=AsyncMock,
             return_value=mock_llm_grammar_error_response,
         ):
        response = client.post("/api/v1/ai/analyze-image", files=files)

        # Should return 500 DatabaseError
        assert response.status_code == 500
        data = response.json()
        assert "DatabaseError" in str(data)

        # Compensation verification: delete_image MUST have been called for rollback!
        mock_delete.assert_called_once_with("uploads/2026/10/rollback-test.png")

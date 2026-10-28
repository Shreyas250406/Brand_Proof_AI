"""Supabase database and authentication integration service."""

import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from app.core.config import settings
from app.core.exceptions import (
    DatabaseConfigError,
    DatabaseError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)


class SupabaseService:
    """Provides methods for Supabase Auth, profiles, analysis history,

    and image metadata storage.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        anon_key: Optional[str] = None,
    ):
        self.url = (supabase_url or settings.SUPABASE_URL or "").strip() or None
        self.service_role_key = (
            service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        ).strip() or None
        self.anon_key = (anon_key or settings.SUPABASE_ANON_KEY or "").strip() or None
        self._client: Optional[Client] = None
        self._auth_client: Optional[Client] = None

    def is_configured(self) -> bool:
        """Returns True if Supabase URL and at least one key are provided."""
        return bool(self.url and (self.service_role_key or self.anon_key))

    def _get_client(self) -> Client:
        """Initializes or returns client with service role key (or anon key fallback).

        Prefers service-role key for backend database queries.
        """
        if not self.is_configured():
            raise DatabaseConfigError(
                "Supabase is not configured. Please set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in environment."
            )

        if self._client is None:
            # Prefer service-role key for backend table access
            key = self.service_role_key or self.anon_key
            try:
                self._client = create_client(self.url, key)
            except Exception as exc:
                logger.error("Failed to initialize Supabase client: %s", exc)
                raise DatabaseConfigError(f"Could not connect to Supabase: {str(exc)}")

        return self._client

    def _get_auth_client(self) -> Client:
        """Returns a client suitable for user auth flows (uses anon_key if available)."""
        if not self.is_configured():
            raise DatabaseConfigError("Supabase Auth is not configured.")

        if self._auth_client is None:
            key = self.anon_key or self.service_role_key
            try:
                self._auth_client = create_client(self.url, key)
            except Exception as exc:
                logger.error("Failed to initialize Supabase Auth client: %s", exc)
                raise DatabaseConfigError(f"Could not initialize Supabase Auth: {str(exc)}")

        return self._auth_client

    # --------------------------------------------------------------------------
    # Authentication Methods
    # --------------------------------------------------------------------------

    async def register_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a new user using Supabase Auth.
        
        Passwords are encrypted and stored in auth.users by Supabase Auth,
        never in public.profiles.
        """
        auth_client = self._get_auth_client()
        try:
            signup_options = {}
            if display_name:
                signup_options["data"] = {"display_name": display_name}

            res = auth_client.auth.sign_up({
                "email": email,
                "password": password,
                "options": signup_options,
            })

            user_obj = res.user
            session_obj = res.session

            return {
                "user_id": str(user_obj.id) if user_obj else None,
                "email": user_obj.email if user_obj else email,
                "display_name": display_name,
                "access_token": session_obj.access_token if session_obj else None,
                "refresh_token": session_obj.refresh_token if session_obj else None,
            }
        except Exception as exc:
            logger.error("User registration failed for %s: %s", email, exc)
            raise AuthenticationError(f"Registration failed: {str(exc)}")

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates a user via Supabase Auth and returns the session tokens."""
        auth_client = self._get_auth_client()
        try:
            res = auth_client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            user_obj = res.user
            session_obj = res.session

            if not session_obj:
                raise AuthenticationError("Invalid email or password.")

            display_name = None
            if user_obj and user_obj.user_metadata:
                display_name = user_obj.user_metadata.get("display_name")

            return {
                "user_id": str(user_obj.id) if user_obj else None,
                "email": user_obj.email if user_obj else email,
                "display_name": display_name,
                "access_token": session_obj.access_token,
                "refresh_token": session_obj.refresh_token,
                "expires_at": session_obj.expires_at,
            }
        except Exception as exc:
            logger.error("User login failed for %s: %s", email, exc)
            raise AuthenticationError(f"Authentication failed: {str(exc)}")

    async def logout_user(self, access_token: str) -> bool:
        """Signs out the user session."""
        auth_client = self._get_auth_client()
        try:
            auth_client.auth.sign_out()
            return True
        except Exception as exc:
            logger.warning("Sign-out warning: %s", exc)
            return True

    async def verify_session(self, access_token: str) -> Dict[str, Any]:
        """Validates a JWT access token and returns the authenticated user data."""
        if not access_token:
            raise AuthenticationError("Missing access token.")

        auth_client = self._get_auth_client()
        try:
            user_response = auth_client.auth.get_user(access_token)
            user_obj = user_response.user if user_response else None

            if not user_obj:
                raise AuthenticationError("Invalid or expired session token.")

            display_name = None
            if user_obj.user_metadata:
                display_name = user_obj.user_metadata.get("display_name")

            return {
                "user_id": str(user_obj.id),
                "email": user_obj.email,
                "display_name": display_name,
            }
        except Exception as exc:
            logger.error("Session verification failed: %s", exc)
            raise AuthenticationError(f"Session verification failed: {str(exc)}")

    # --------------------------------------------------------------------------
    # Analysis History Methods
    # --------------------------------------------------------------------------

    def save_analysis_history(
        self,
        input_type: str,
        original_text: str,
        corrected_text: str,
        findings: List[Dict[str, Any]],
        summary: Optional[str] = None,
        model_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Saves a completed analysis result to public.analysis_history."""
        client = self._get_client()

        payload = {
            "input_type": input_type,
            "original_text": original_text,
            "corrected_text": corrected_text,
            "findings": findings,
            "summary": summary,
            "model_name": model_name or settings.effective_model,
        }

        if user_id:
            payload["user_id"] = user_id

        try:
            response = client.table("analysis_history").insert(payload).execute()
            if not response.data or len(response.data) == 0:
                raise DatabaseError("Failed to insert record into analysis_history.")
            return response.data[0]
        except Exception as exc:
            logger.error("Database error saving analysis history: %s", exc)
            raise DatabaseError(f"Could not persist analysis history: {str(exc)}")

    def list_analysis_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Queries analysis history ordered by created_at DESC."""
        client = self._get_client()
        try:
            query = client.table("analysis_history").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            response = query.execute()
            return response.data or []
        except Exception as exc:
            logger.error("Failed to list analysis history: %s", exc)
            raise DatabaseError(f"Could not retrieve analysis history: {str(exc)}")

    def get_analysis_by_id(
        self,
        analysis_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a single analysis record by UUID."""
        client = self._get_client()
        try:
            query = client.table("analysis_history").select("*").eq("id", analysis_id)
            if user_id:
                query = query.eq("user_id", user_id)
            response = query.execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as exc:
            logger.error("Failed to get analysis %s: %s", analysis_id, exc)
            raise DatabaseError(f"Could not fetch analysis record: {str(exc)}")

    def delete_analysis(
        self,
        analysis_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Deletes an analysis history record.

        Linked image_metadata rows are automatically cascade deleted.
        """
        client = self._get_client()
        try:
            query = client.table("analysis_history").delete().eq("id", analysis_id)
            if user_id:
                query = query.eq("user_id", user_id)
            response = query.execute()
            return bool(response.data)
        except Exception as exc:
            logger.error("Failed to delete analysis %s: %s", analysis_id, exc)
            raise DatabaseError(f"Could not delete analysis: {str(exc)}")

    # --------------------------------------------------------------------------
    # Image Metadata Methods
    # --------------------------------------------------------------------------

    def save_image_metadata(
        self,
        analysis_id: Optional[str],
        bucket_name: str,
        object_key: str,
        content_type: str,
        file_size_bytes: Optional[int] = None,
        original_filename: Optional[str] = None,
        storage_provider: str = "s3",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Saves image metadata to public.image_metadata table."""
        client = self._get_client()

        payload = {
            "storage_provider": storage_provider,
            "bucket_name": bucket_name,
            "object_key": object_key,
            "content_type": content_type,
            "file_size_bytes": file_size_bytes,
            "original_filename": original_filename,
        }

        if analysis_id:
            payload["analysis_id"] = analysis_id
        if user_id:
            payload["user_id"] = user_id

        try:
            response = client.table("image_metadata").insert(payload).execute()
            if not response.data or len(response.data) == 0:
                raise DatabaseError("Failed to insert record into image_metadata.")
            return response.data[0]
        except Exception as exc:
            logger.error("Database error saving image metadata: %s", exc)
            raise DatabaseError(f"Could not persist image metadata: {str(exc)}")

    def get_image_metadata_by_analysis(
        self,
        analysis_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves image metadata row associated with an analysis ID."""
        client = self._get_client()
        try:
            response = (
                client.table("image_metadata")
                .select("*")
                .eq("analysis_id", analysis_id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as exc:
            logger.error("Failed to fetch image metadata for analysis %s: %s", analysis_id, exc)
            raise DatabaseError(f"Could not retrieve image metadata: {str(exc)}")


# Default singleton instance
supabase_service = SupabaseService()

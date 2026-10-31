"""Supabase database and authentication integration service."""

import logging
from typing import Optional, Dict, Any, List
import httpx
from postgrest import SyncPostgrestClient
from app.core.config import settings
from app.core.exceptions import (
    DatabaseConfigError,
    DatabaseError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)

_UNSET = object()

DEMO_ADMIN_USER_ID = "b71b91b7-3ac2-43e3-b73b-b719caedc4a3"
LEGACY_DEMO_ADMIN_ID = "00000000-0000-4000-a000-000000000001"


class SupabaseService:
    """Provides methods for Supabase Auth, profiles, analysis history,

    and image metadata storage. Supports both JWT and sb_* API keys.
    """

    def __init__(
        self,
        supabase_url: Any = _UNSET,
        service_role_key: Any = _UNSET,
        anon_key: Any = _UNSET,
    ):
        raw_url = settings.SUPABASE_URL if supabase_url is _UNSET else supabase_url
        raw_serv = settings.SUPABASE_SERVICE_ROLE_KEY if service_role_key is _UNSET else service_role_key
        raw_anon = settings.SUPABASE_ANON_KEY if anon_key is _UNSET else anon_key

        self.url = (raw_url or "").strip() or None
        self.service_role_key = (raw_serv or "").strip() or None
        self.anon_key = (raw_anon or "").strip() or None
        self._client = None
        self._auth_client = None

    def is_configured(self) -> bool:
        """Returns True if Supabase URL and at least one key are provided."""
        return bool(self.url and (self.service_role_key or self.anon_key))

    def _get_client(self):
        """Initializes or returns postgrest client with service role key (or anon key fallback)."""
        if not self.is_configured():
            raise DatabaseConfigError(
                "Supabase is not configured. Please set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in environment."
            )

        if self._client is None:
            key = self.service_role_key or self.anon_key
            try:
                # Try official SDK first
                from supabase import create_client
                self._client = create_client(self.url, key)
            except Exception:
                # Fallback to PostgREST client directly (supports non-JWT sb_* keys)
                try:
                    rest_url = f"{self.url.rstrip('/')}/rest/v1"
                    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
                    self._client = SyncPostgrestClient(rest_url, headers=headers)
                except Exception as exc:
                    logger.error("Failed to initialize Supabase/PostgREST client: %s", exc)
                    raise DatabaseConfigError(f"Could not connect to Supabase: {str(exc)}")

        return self._client

    def _get_auth_client(self):
        """Attempts to initialize standard Supabase Auth client, returns None if key format unsupported."""
        if not self.is_configured():
            raise DatabaseConfigError("Supabase Auth is not configured.")

        if self._auth_client is None:
            key = self.anon_key or self.service_role_key
            try:
                from supabase import create_client
                self._auth_client = create_client(self.url, key)
            except Exception:
                self._auth_client = None

        return self._auth_client

    def ensure_profile(self, user_id: str, display_name: Optional[str] = None) -> bool:
        """Ensures a profile row exists for the given user without disrupting registration."""
        if not self.is_configured() or not user_id or self._client is None:
            return False
        try:
            client = self._get_client()
            table_obj = client.table("profiles") if hasattr(client, "table") else client.from_("profiles")
            table_obj.upsert({
                "id": user_id,
                "display_name": display_name,
            }, on_conflict="id").execute()
            return True
        except Exception as exc:
            logger.warning("Profile ensure notice (handled gracefully): %s", exc)
            return False

    # --------------------------------------------------------------------------
    # Authentication Methods
    # --------------------------------------------------------------------------

    async def register_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a new user account with Supabase Auth."""
        if not self.is_configured():
            raise DatabaseConfigError("Supabase Auth is not configured.")

        auth_client = self._get_auth_client()
        if auth_client and hasattr(auth_client, "auth"):
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
                identities = getattr(user_obj, "identities", None)
                if isinstance(identities, list) and len(identities) == 0:
                    raise AuthenticationError("An account with this email address already exists. Please sign in instead.")
                user_id = str(user_obj.id) if user_obj else None
                if user_id:
                    self.ensure_profile(user_id, display_name)
                access_token = session_obj.access_token if session_obj else None
                refresh_token = session_obj.refresh_token if session_obj else None
                confirmation_required = access_token is None
                return {
                    "user_id": user_id,
                    "email": user_obj.email if user_obj else email,
                    "display_name": display_name,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "confirmation_required": confirmation_required,
                    "message": (
                        "Please check your email to confirm your account before logging in."
                        if confirmation_required
                        else "Registration successful."
                    ),
                }
            except AuthenticationError:
                raise
            except Exception as exc:
                logger.error("User registration failed via SDK: %s", exc)
                raise AuthenticationError(f"Registration failed: {str(exc)}")

        # HTTP REST fallback for sb_* keys
        key = self.anon_key or self.service_role_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "password": password,
            "data": {"display_name": display_name} if display_name else {},
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                res = await http_client.post(
                    f"{self.url.rstrip('/')}/auth/v1/signup",
                    headers=headers,
                    json=payload,
                )
            if res.status_code not in (200, 201):
                err_data = {}
                try:
                    err_data = res.json()
                except Exception:
                    pass
                err_msg = (
                    err_data.get("msg")
                    or err_data.get("message")
                    or err_data.get("error_description")
                    or res.text
                )
                err_code = err_data.get("error_code") or err_data.get("code")
                if err_code == "over_email_send_rate_limit" or "rate limit" in str(err_msg).lower():
                    raise AuthenticationError("Email sending rate limit exceeded. Please wait a few minutes before trying again.")
                if res.status_code == 422 or "already registered" in str(err_msg).lower():
                    raise AuthenticationError("An account with this email address already exists. Please sign in instead.")
                raise AuthenticationError(f"Registration failed: {err_msg}")

            data = res.json()
            user_data = data.get("user") or data
            identities = user_data.get("identities")
            # In Supabase GoTrue, when an account with this email already exists, identities is returned as empty list []
            if isinstance(identities, list) and len(identities) == 0:
                raise AuthenticationError("An account with this email address already exists. Please sign in instead.")

            user_id = str(user_data.get("id")) if user_data.get("id") else None
            if user_id:
                self.ensure_profile(user_id, display_name)

            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            confirmation_required = access_token is None

            return {
                "user_id": user_id,
                "email": user_data.get("email", email),
                "display_name": display_name,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "confirmation_required": confirmation_required,
                "message": (
                    "Please check your email to confirm your account before logging in."
                    if confirmation_required
                    else "Registration successful."
                ),
            }
        except AuthenticationError:
            raise
        except Exception as exc:
            logger.error("User registration failed via HTTP: %s", exc)
            raise AuthenticationError(f"Registration failed: {str(exc)}")

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates a user via Supabase Auth and returns the session tokens."""
        # Instant verification for Brand Admin demo credentials
        clean_email = email.strip().lower()
        if clean_email == "admin@brandproof.ai" and password == "BrandProof2026!":
            return {
                "user_id": DEMO_ADMIN_USER_ID,
                "email": "admin@brandproof.ai",
                "display_name": "Brand Admin",
                "access_token": "brandproof_demo_admin_jwt_token",
                "refresh_token": "brandproof_demo_admin_refresh_token",
                "expires_at": 1999999999,
            }

        if not self.is_configured():
            raise DatabaseConfigError("Supabase Auth is not configured.")

        auth_client = self._get_auth_client()
        if auth_client and hasattr(auth_client, "auth"):
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
            except AuthenticationError:
                raise
            except Exception as exc:
                logger.error("User login failed via SDK: %s", exc)
                raise AuthenticationError(f"Authentication failed: {str(exc)}")

        # HTTP REST fallback for sb_* keys
        key = self.anon_key or self.service_role_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "password": password,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                res = await http_client.post(
                    f"{self.url.rstrip('/')}/auth/v1/token?grant_type=password",
                    headers=headers,
                    json=payload,
                )
            if res.status_code != 200:
                err_data = {}
                try:
                    err_data = res.json()
                except Exception:
                    pass
                raw_err = (
                    err_data.get("error_description")
                    or err_data.get("msg")
                    or err_data.get("message")
                    or "Invalid email or password."
                )
                if "email not confirmed" in str(raw_err).lower():
                    raise AuthenticationError("Email not confirmed. Please check your inbox to confirm your account before logging in.")
                raise AuthenticationError("Invalid email or password.")

            data = res.json()
            user_obj = data.get("user", {})
            user_meta = user_obj.get("user_metadata", {})
            display_name = user_meta.get("display_name")

            return {
                "user_id": user_obj.get("id"),
                "email": user_obj.get("email", email),
                "display_name": display_name,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_at": data.get("expires_at"),
            }
        except AuthenticationError:
            raise
        except Exception as exc:
            logger.error("User login failed via HTTP: %s", exc)
            raise AuthenticationError(f"Authentication failed: {str(exc)}")

    async def logout_user(self, access_token: str) -> bool:
        """Signs out the user session."""
        if not self.is_configured() or not access_token:
            return True

        auth_client = self._get_auth_client()
        if auth_client and hasattr(auth_client, "auth"):
            try:
                auth_client.auth.sign_out()
                return True
            except Exception as exc:
                logger.warning("Sign-out warning via SDK: %s", exc)

        key = self.anon_key or self.service_role_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                await http_client.post(
                    f"{self.url.rstrip('/')}/auth/v1/logout",
                    headers=headers,
                )
            return True
        except Exception as exc:
            logger.warning("Sign-out warning via HTTP: %s", exc)
            return True

    async def verify_session(self, access_token: str) -> Dict[str, Any]:
        """Validates a JWT access token and returns the authenticated user data."""
        if not access_token:
            raise AuthenticationError("Missing access token.")

        # Instant verification for Brand Admin demo token
        if access_token == "brandproof_demo_admin_jwt_token":
            return {
                "user_id": DEMO_ADMIN_USER_ID,
                "email": "admin@brandproof.ai",
                "display_name": "Brand Admin",
            }

        if not self.is_configured():
            raise DatabaseConfigError("Supabase is not configured.")

        auth_client = self._get_auth_client()
        if auth_client and hasattr(auth_client, "auth"):
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
            except AuthenticationError:
                raise
            except Exception:
                pass

        key = self.anon_key or self.service_role_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                res = await http_client.get(
                    f"{self.url.rstrip('/')}/auth/v1/user",
                    headers=headers,
                )
            if res.status_code != 200:
                raise AuthenticationError("Invalid or expired session token.")

            user_obj = res.json()
            user_meta = user_obj.get("user_metadata", {})
            return {
                "user_id": str(user_obj.get("id")),
                "email": user_obj.get("email"),
                "display_name": user_meta.get("display_name"),
            }
        except AuthenticationError:
            raise
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

        if user_id == LEGACY_DEMO_ADMIN_ID:
            user_id = DEMO_ADMIN_USER_ID

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
            table_obj = client.table("analysis_history") if hasattr(client, "table") else client.from_("analysis_history")
            response = table_obj.insert(payload).execute()
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
            table_obj = client.table("analysis_history") if hasattr(client, "table") else client.from_("analysis_history")
            query = table_obj.select("*")
            if user_id:
                if user_id == LEGACY_DEMO_ADMIN_ID:
                    user_id = DEMO_ADMIN_USER_ID
                query = query.eq("user_id", user_id)
            else:
                query = query.is_("user_id", "null")
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
        if user_id == LEGACY_DEMO_ADMIN_ID:
            user_id = DEMO_ADMIN_USER_ID
        try:
            table_obj = client.table("analysis_history") if hasattr(client, "table") else client.from_("analysis_history")
            query = table_obj.select("*").eq("id", analysis_id)
            if user_id:
                query = query.eq("user_id", user_id)
            response = query.execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as exc:
            logger.error("Failed to get analysis %s: %s", analysis_id, exc)
            raise DatabaseError(f"Could not fetch analysis record: {str(exc)}")

    def update_analysis_history(
        self,
        analysis_id: str,
        corrected_text: Optional[str] = None,
        findings: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates an existing analysis record in public.analysis_history."""
        client = self._get_client()
        if user_id == LEGACY_DEMO_ADMIN_ID:
            user_id = DEMO_ADMIN_USER_ID

        payload = {}
        if corrected_text is not None:
            payload["corrected_text"] = corrected_text
        if findings is not None:
            payload["findings"] = findings
        if summary is not None:
            payload["summary"] = summary

        if not payload:
            res = self.get_analysis_by_id(analysis_id, user_id=user_id)
            if not res:
                raise DatabaseError(f"Analysis {analysis_id} not found.")
            return res

        try:
            table_obj = client.table("analysis_history") if hasattr(client, "table") else client.from_("analysis_history")
            query = table_obj.update(payload).eq("id", analysis_id)
            if user_id:
                query = query.eq("user_id", user_id)
            response = query.execute()
            if not response.data or len(response.data) == 0:
                raise DatabaseError(f"Analysis {analysis_id} not found or permission denied.")
            return response.data[0]
        except Exception as exc:
            logger.error("Failed to update analysis history %s: %s", analysis_id, exc)
            raise DatabaseError(f"Could not update analysis history: {str(exc)}")

    def delete_analysis(
        self,
        analysis_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Deletes an analysis history record.

        Linked image_metadata rows are automatically cascade deleted.
        """
        client = self._get_client()
        if user_id == LEGACY_DEMO_ADMIN_ID:
            user_id = DEMO_ADMIN_USER_ID
        try:
            table_obj = client.table("analysis_history") if hasattr(client, "table") else client.from_("analysis_history")
            query = table_obj.delete().eq("id", analysis_id)
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
            table_obj = client.table("image_metadata") if hasattr(client, "table") else client.from_("image_metadata")
            response = table_obj.insert(payload).execute()
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
            table_obj = client.table("image_metadata") if hasattr(client, "table") else client.from_("image_metadata")
            response = (
                table_obj
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

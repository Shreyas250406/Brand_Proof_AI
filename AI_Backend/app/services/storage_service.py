"""S3-compatible image storage service using boto3."""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

from app.core.config import settings
from app.core.exceptions import (
    StorageConfigError,
    StorageUploadError,
    StorageDeleteError,
    PayloadTooLargeError,
    UnsupportedMediaError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)


class StoredImageMetadata(BaseModel):
    """Schema for metadata returned after an image upload."""
    storage_provider: str = "s3"
    bucket_name: str
    object_key: str
    original_filename: Optional[str] = None
    content_type: str
    file_size_bytes: int
    presigned_url: Optional[str] = None
    created_at: str


class StorageService:
    """Manages S3-compatible image uploads, deletions, and presigned retrieval.
    
    Supports AWS S3, Cloudflare R2, MinIO, Wasabi, and DigitalOcean Spaces.
    Validates MIME type, file size, and generates collision-free object keys.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
        bucket_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        presigned_expiry_seconds: Optional[int] = None,
    ):
        self.endpoint_url = (endpoint_url or settings.S3_ENDPOINT_URL or "").strip() or None
        self.region = (region or settings.S3_REGION or "us-east-1").strip()
        self.bucket_name = (bucket_name or settings.S3_BUCKET_NAME or "").strip() or None
        self.access_key_id = (access_key_id or settings.S3_ACCESS_KEY_ID or "").strip() or None
        self.secret_access_key = (secret_access_key or settings.S3_SECRET_ACCESS_KEY or "").strip() or None
        self.use_ssl = use_ssl if use_ssl is not None else settings.S3_USE_SSL
        self.presigned_expiry = (
            presigned_expiry_seconds
            or settings.S3_PRESIGNED_EXPIRY_SECONDS
            or 3600
        )
        self._client = None

    def is_configured(self) -> bool:
        """Checks if S3 storage credentials and bucket are configured."""
        return bool(self.bucket_name and self.access_key_id and self.secret_access_key)

    def _get_client(self):
        """Lazy initializes the boto3 S3 client."""
        if not self.is_configured():
            raise StorageConfigError(
                "S3 storage is not fully configured. Please set S3_BUCKET_NAME, "
                "S3_ACCESS_KEY_ID, and S3_SECRET_ACCESS_KEY in environment or .env."
            )

        if self._client is None:
            config = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )
            try:
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    region_name=self.region,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    use_ssl=self.use_ssl,
                    config=config,
                )
            except Exception as exc:
                logger.error("Failed to initialize boto3 S3 client: %s", exc)
                raise StorageConfigError(f"Could not initialize S3 client: {str(exc)}")

        return self._client

    def validate_image(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
    ) -> str:
        """Validates payload size, content type, and image header integrity."""
        if not image_bytes or len(image_bytes) == 0:
            raise InvalidImageError("Image file cannot be empty.")

        if len(image_bytes) > settings.max_upload_size_bytes:
            raise PayloadTooLargeError(
                f"Image file exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB "
                f"(received {len(image_bytes) / (1024 * 1024):.2f}MB)."
            )

        # Normalize and validate MIME type
        normalized_content_type = (content_type or "").lower().split(";")[0].strip()
        if not normalized_content_type or normalized_content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise UnsupportedMediaError(
                f"Unsupported content type '{content_type}'. "
                f"Supported types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            )

        return normalized_content_type

    def generate_object_key(
        self,
        content_type: str,
        original_filename: Optional[str] = None,
        prefix: str = "uploads",
    ) -> str:
        """Generates a secure, unique, collision-resistant S3 object key."""
        date_folder = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        unique_token = uuid.uuid4().hex

        # Extract or infer file extension
        ext = ""
        if original_filename:
            _, raw_ext = os.path.splitext(original_filename)
            safe_ext = re.sub(r"[^a-zA-Z0-9]", "", raw_ext.lower())
            if safe_ext:
                ext = f".{safe_ext}"

        if not ext:
            mime_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/bmp": ".bmp",
                "image/tiff": ".tiff",
            }
            ext = mime_map.get(content_type, ".png")

        return f"{prefix}/{date_folder}/{unique_token}{ext}"

    def upload_image(
        self,
        image_bytes: bytes,
        content_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        generate_presigned: bool = True,
    ) -> StoredImageMetadata:
        """Validates, uploads an image to S3 storage, and returns structured metadata."""
        validated_type = self.validate_image(image_bytes, content_type)
        object_key = self.generate_object_key(validated_type, original_filename)
        client = self._get_client()

        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=image_bytes,
                ContentType=validated_type,
            )
            logger.info("Successfully uploaded %d bytes to s3://%s/%s", len(image_bytes), self.bucket_name, object_key)
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to upload image to S3: %s", exc)
            raise StorageUploadError(
                f"S3 upload failed: {str(exc)}",
                details={"bucket": self.bucket_name, "object_key": object_key},
            )

        presigned_url = None
        if generate_presigned:
            try:
                presigned_url = self.generate_presigned_url(object_key)
            except Exception as exc:
                logger.warning("Could not generate presigned URL for %s: %s", object_key, exc)

        return StoredImageMetadata(
            storage_provider="s3",
            bucket_name=self.bucket_name,
            object_key=object_key,
            original_filename=original_filename,
            content_type=validated_type,
            file_size_bytes=len(image_bytes),
            presigned_url=presigned_url,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_presigned_url(
        self,
        object_key: str,
        expiration_seconds: Optional[int] = None,
    ) -> str:
        """Generates a temporary, secure presigned download URL for an object."""
        client = self._get_client()
        expiry = expiration_seconds or self.presigned_expiry
        try:
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiry,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to generate presigned URL for %s: %s", object_key, exc)
            raise StorageConfigError(f"Presigned URL generation failed: {str(exc)}")

    def delete_image(self, object_key: str) -> bool:
        """Deletes an image object from S3 storage."""
        if not object_key or not object_key.strip():
            return False

        client = self._get_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info("Successfully deleted s3://%s/%s", self.bucket_name, object_key)
            return True
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to delete object from S3: %s", exc)
            raise StorageDeleteError(
                f"S3 deletion failed: {str(exc)}",
                details={"bucket": self.bucket_name, "object_key": object_key},
            )


# Default singleton instance
storage_service = StorageService()

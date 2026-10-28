"""Unit tests for S3 storage service."""

from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError

from app.services.storage_service import StorageService, StoredImageMetadata
from app.core.exceptions import (
    StorageConfigError,
    StorageUploadError,
    StorageDeleteError,
    PayloadTooLargeError,
    UnsupportedMediaError,
    InvalidImageError,
)


@pytest.fixture
def mock_storage():
    """Returns a StorageService configured with mock S3 credentials."""
    return StorageService(
        endpoint_url="https://s3.example.com",
        region="us-east-1",
        bucket_name="test-bucket",
        access_key_id="test-key-id",
        secret_access_key="test-secret-key",
        use_ssl=True,
    )


def test_storage_unconfigured():
    """Verifies that unconfigured storage raises StorageConfigError on operations."""
    storage = StorageService(bucket_name=None, access_key_id=None, secret_access_key=None)
    assert not storage.is_configured()

    with pytest.raises(StorageConfigError):
        storage.upload_image(b"valid_data", content_type="image/png")


def test_validate_image_size_and_mimes(mock_storage):
    """Tests file size and MIME type validation."""
    # Empty image
    with pytest.raises(InvalidImageError):
        mock_storage.validate_image(b"", content_type="image/png")

    # Unsupported format
    with pytest.raises(UnsupportedMediaError):
        mock_storage.validate_image(b"some content", content_type="application/pdf")

    # Oversized image
    huge_bytes = b"0" * (11 * 1024 * 1024)
    with pytest.raises(PayloadTooLargeError):
        mock_storage.validate_image(huge_bytes, content_type="image/png")

    # Valid PNG
    assert mock_storage.validate_image(b"PNG_DATA", content_type="image/png") == "image/png"


def test_generate_object_key(mock_storage):
    """Verifies that generated keys are unique, dated, and keep valid extensions."""
    key1 = mock_storage.generate_object_key("image/png", original_filename="marketing.PNG")
    key2 = mock_storage.generate_object_key("image/png", original_filename="marketing.PNG")

    assert key1 != key2
    assert key1.endswith(".png")
    assert key1.startswith("uploads/")


def test_upload_image_success(mock_storage):
    """Verifies successful upload to S3 with presigned URL."""
    mock_boto_client = MagicMock()
    mock_boto_client.generate_presigned_url.return_value = "https://s3.example.com/test-bucket/presigned"

    with patch.object(mock_storage, "_get_client", return_value=mock_boto_client):
        result = mock_storage.upload_image(
            image_bytes=b"sample_image_bytes",
            content_type="image/png",
            original_filename="promo.png",
            generate_presigned=True,
        )

        assert isinstance(result, StoredImageMetadata)
        assert result.bucket_name == "test-bucket"
        assert result.storage_provider == "s3"
        assert result.content_type == "image/png"
        assert result.original_filename == "promo.png"
        assert result.file_size_bytes == len(b"sample_image_bytes")
        assert result.presigned_url == "https://s3.example.com/test-bucket/presigned"

        mock_boto_client.put_object.assert_called_once()


def test_upload_image_s3_error(mock_storage):
    """Verifies that S3 upload errors raise StorageUploadError."""
    mock_boto_client = MagicMock()
    mock_boto_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "PutObject"
    )

    with patch.object(mock_storage, "_get_client", return_value=mock_boto_client):
        with pytest.raises(StorageUploadError) as exc_info:
            mock_storage.upload_image(
                image_bytes=b"sample_bytes",
                content_type="image/png",
                original_filename="sample.png",
            )
        assert "access denied" in str(exc_info.value).lower()


def test_delete_image_success(mock_storage):
    """Verifies image deletion from S3."""
    mock_boto_client = MagicMock()

    with patch.object(mock_storage, "_get_client", return_value=mock_boto_client):
        success = mock_storage.delete_image("uploads/2026/10/test.png")
        assert success is True
        mock_boto_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/2026/10/test.png"
        )


def test_delete_image_s3_error(mock_storage):
    """Verifies delete error handling."""
    mock_boto_client = MagicMock()
    mock_boto_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "S3 failure"}}, "DeleteObject"
    )

    with patch.object(mock_storage, "_get_client", return_value=mock_boto_client):
        with pytest.raises(StorageDeleteError):
            mock_storage.delete_image("uploads/2026/10/test.png")

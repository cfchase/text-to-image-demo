"""Unit tests for S3Storage implementation."""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from storage.s3 import S3Storage
from storage.base import StorageError


class TestS3Storage:
    """Test S3Storage implementation."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        mock_client = MagicMock()
        
        # Mock successful responses
        mock_client.put_object.return_value = {"ETag": '"abc123"'}
        mock_client.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"fake image data"))
        }
        mock_client.head_object.return_value = {
            "LastModified": datetime.now(timezone.utc),
            "ETag": '"abc123"',
            "ContentLength": 1000,
        }
        mock_client.delete_objects.return_value = {"Deleted": []}
        mock_client.generate_presigned_url.return_value = "https://example.com/image.png"
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_client.get_paginator.return_value = mock_paginator
        
        return mock_client

    @pytest.fixture
    def storage_config(self) -> Dict[str, Any]:
        """S3Storage configuration for testing."""
        return {
            "bucket": "test-bucket",
            "prefix": "test-prefix/",
            "endpoint_url": "http://localhost:9000",
            "access_key_id": "test-key",
            "secret_access_key": "test-secret",
            "region_name": "us-east-1",
        }

    @pytest.fixture
    def sample_image_data(self) -> bytes:
        """Sample image data for testing."""
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01fake image data"

    @pytest.fixture
    def sample_metadata(self) -> Dict[str, Any]:
        """Sample metadata for testing."""
        return {
            "prompt": "a beautiful sunset",
            "width": 512,
            "height": 512,
            "guidance_scale": 7.5,
            "num_inference_steps": 50,
        }

    @patch("boto3.Session")
    async def test_init_success(self, mock_session, storage_config, mock_s3_client):
        """Test successful S3Storage initialization."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        storage = S3Storage(**storage_config)
        
        assert storage.bucket == "test-bucket"
        assert storage.prefix == "test-prefix/"
        assert storage.presigned_url_ttl == 3600
        
        mock_session.assert_called_once_with(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="us-east-1",
        )

    @patch("boto3.Session")
    async def test_init_no_credentials_error(self, mock_session, storage_config):
        """Test initialization with no credentials."""
        mock_session.side_effect = NoCredentialsError()
        
        with pytest.raises(StorageError, match="S3 credentials not found"):
            S3Storage(**storage_config)

    @patch("boto3.Session")
    async def test_init_empty_prefix(self, mock_session, storage_config, mock_s3_client):
        """Test initialization with empty prefix."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage_config["prefix"] = ""
        
        storage = S3Storage(**storage_config)
        
        assert storage.prefix == ""

    @patch("boto3.Session")
    async def test_init_trailing_slash_removed(self, mock_session, storage_config, mock_s3_client):
        """Test that trailing slash is properly handled in prefix."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage_config["prefix"] = "test-prefix/"
        
        storage = S3Storage(**storage_config)
        
        assert storage.prefix == "test-prefix/"

    @patch("boto3.Session")
    async def test_save_image_success(
        self, mock_session, storage_config, mock_s3_client, sample_image_data, sample_metadata
    ):
        """Test successful image save to S3."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        image_id = "test-123"
        
        key = await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        assert key == "test-prefix/test-123.png"
        
        # Verify put_object calls
        assert mock_s3_client.put_object.call_count == 2
        
        # Check image upload call
        image_call = mock_s3_client.put_object.call_args_list[0]
        assert image_call[1]["Bucket"] == "test-bucket"
        assert image_call[1]["Key"] == "test-prefix/test-123.png"
        assert image_call[1]["Body"] == sample_image_data
        assert image_call[1]["ContentType"] == "image/png"
        
        # Check metadata upload call  
        metadata_call = mock_s3_client.put_object.call_args_list[1]
        assert metadata_call[1]["Bucket"] == "test-bucket"
        assert metadata_call[1]["Key"] == "test-prefix/test-123.json"
        assert metadata_call[1]["ContentType"] == "application/json"

    @patch("boto3.Session")
    async def test_save_image_empty_data(
        self, mock_session, storage_config, mock_s3_client, sample_metadata
    ):
        """Test saving empty image data raises error."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError, match="Image data is empty"):
            await storage.save_image(b"", "test-123", sample_metadata)

    @patch("boto3.Session")
    async def test_save_image_s3_error(
        self, mock_session, storage_config, mock_s3_client, sample_image_data, sample_metadata
    ):
        """Test save_image handles S3 errors."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError):
            await storage.save_image(sample_image_data, "test-123", sample_metadata)

    @patch("boto3.Session")
    async def test_get_image_success(
        self, mock_session, storage_config, mock_s3_client, sample_image_data
    ):
        """Test successful image retrieval from S3."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=sample_image_data))
        }
        
        storage = S3Storage(**storage_config)
        image_id = "test-456"
        
        result = await storage.get_image(image_id)
        
        assert result == sample_image_data
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test-456.png"
        )

    @patch("boto3.Session")
    async def test_get_image_not_found(self, mock_session, storage_config, mock_s3_client):
        """Test getting non-existent image returns None."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        
        storage = S3Storage(**storage_config)
        
        result = await storage.get_image("nonexistent")
        assert result is None

    @patch("boto3.Session")
    async def test_get_image_s3_error(self, mock_session, storage_config, mock_s3_client):
        """Test get_image handles S3 errors."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GetObject"
        )
        
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError):
            await storage.get_image("test-123")

    @patch("boto3.Session")
    async def test_delete_image_success(self, mock_session, storage_config, mock_s3_client):
        """Test successful image deletion from S3."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        image_id = "test-789"
        
        result = await storage.delete_image(image_id)
        
        assert result is True
        
        # Verify head_object call to check existence
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test-789.png"
        )
        
        # Verify delete_objects call
        mock_s3_client.delete_objects.assert_called_once()
        delete_call = mock_s3_client.delete_objects.call_args[1]
        assert delete_call["Bucket"] == "test-bucket"
        objects = delete_call["Delete"]["Objects"]
        assert len(objects) == 2
        assert {"Key": "test-prefix/test-789.png"} in objects
        assert {"Key": "test-prefix/test-789.json"} in objects

    @patch("boto3.Session")
    async def test_delete_image_not_found(self, mock_session, storage_config, mock_s3_client):
        """Test deleting non-existent image returns False."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        
        storage = S3Storage(**storage_config)
        
        result = await storage.delete_image("nonexistent")
        assert result is False

    @patch("boto3.Session")
    async def test_delete_image_s3_error(self, mock_session, storage_config, mock_s3_client):
        """Test delete_image handles S3 errors."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.delete_objects.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "DeleteObjects"
        )
        
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError):
            await storage.delete_image("test-123")

    @patch("boto3.Session")
    async def test_get_image_url_success(self, mock_session, storage_config, mock_s3_client):
        """Test getting presigned URL for existing image."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        image_id = "test-url"
        
        url = await storage.get_image_url(image_id)
        
        assert url == "https://example.com/image.png"
        
        # Verify head_object call to check existence
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test-url.png"
        )
        
        # Verify generate_presigned_url call
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "test-prefix/test-url.png"},
            ExpiresIn=3600,
        )

    @patch("boto3.Session")
    async def test_get_image_url_not_found(self, mock_session, storage_config, mock_s3_client):
        """Test getting URL for non-existent image."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        
        storage = S3Storage(**storage_config)
        
        url = await storage.get_image_url("nonexistent")
        assert url is None

    @patch("boto3.Session")
    async def test_get_image_url_s3_error(self, mock_session, storage_config, mock_s3_client):
        """Test get_image_url handles S3 errors."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GeneratePresignedUrl"
        )
        
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError):
            await storage.get_image_url("test-123")

    @patch("boto3.Session")
    async def test_list_images_empty(self, mock_session, storage_config, mock_s3_client):
        """Test listing images when S3 is empty."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        images = await storage.list_images()
        
        assert images == []

    @patch("boto3.Session")
    async def test_list_images_with_data(self, mock_session, storage_config, mock_s3_client):
        """Test listing images with data."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        # Mock paginator response
        mock_metadata = {
            "image_id": "test-123",
            "prompt": "test prompt",
            "size": 1000,
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "test-prefix/test-123.json"},
                    {"Key": "test-prefix/test-123.png"},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        
        # Mock get_object for metadata
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(mock_metadata).encode()))
        }
        
        storage = S3Storage(**storage_config)
        
        images = await storage.list_images()
        
        assert len(images) == 1
        assert images[0]["image_id"] == "test-123"
        assert images[0]["prompt"] == "test prompt"
        assert "last_modified" in images[0]
        assert "etag" in images[0]

    @patch("boto3.Session")
    async def test_list_images_with_prefix(self, mock_session, storage_config, mock_s3_client):
        """Test listing images with prefix filter."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        await storage.list_images(prefix="user1")
        
        # Verify paginator called with correct prefix
        mock_s3_client.get_paginator.assert_called_once_with("list_objects_v2")
        paginator_call = mock_s3_client.get_paginator.return_value.paginate.call_args[1]
        assert paginator_call["Prefix"] == "test-prefix/user1"

    @patch("boto3.Session")
    async def test_list_images_invalid_metadata(self, mock_session, storage_config, mock_s3_client):
        """Test that invalid metadata files are skipped."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        # Mock paginator response
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "test-prefix/invalid.json"}]}
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        
        # Mock get_object to return invalid JSON
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"invalid json"))
        }
        
        storage = S3Storage(**storage_config)
        
        images = await storage.list_images()
        assert images == []

    @patch("boto3.Session")
    async def test_cleanup_expired_images_none_expired(self, mock_session, storage_config, mock_s3_client):
        """Test cleanup when no images are expired."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        # Mock paginator response with recent objects
        mock_paginator = MagicMock()
        recent_time = datetime.now(timezone.utc)
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "test-prefix/recent.png", "LastModified": recent_time},
                    {"Key": "test-prefix/recent.json", "LastModified": recent_time},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        
        storage = S3Storage(**storage_config)
        
        deleted_count = await storage.cleanup_expired_images(ttl_seconds=3600)
        
        assert deleted_count == 0
        mock_s3_client.delete_objects.assert_not_called()

    @patch("boto3.Session")
    async def test_cleanup_expired_images_with_expired(self, mock_session, storage_config, mock_s3_client):
        """Test cleanup removes expired images."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        # Mock paginator response with old objects
        mock_paginator = MagicMock()
        old_time = datetime.fromtimestamp(time.time() - 7200, tz=timezone.utc)  # 2 hours ago
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "test-prefix/old.png", "LastModified": old_time},
                    {"Key": "test-prefix/old.json", "LastModified": old_time},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        
        storage = S3Storage(**storage_config)
        
        deleted_count = await storage.cleanup_expired_images(ttl_seconds=3600)
        
        assert deleted_count == 1  # Only count .png files
        
        # Verify delete_objects called
        mock_s3_client.delete_objects.assert_called_once()
        delete_call = mock_s3_client.delete_objects.call_args[1]
        objects = delete_call["Delete"]["Objects"]
        assert len(objects) == 2
        assert {"Key": "test-prefix/old.png"} in objects
        assert {"Key": "test-prefix/old.json"} in objects

    @patch("boto3.Session")
    async def test_cleanup_expired_images_s3_error(self, mock_session, storage_config, mock_s3_client):
        """Test cleanup handles S3 errors."""
        mock_session.return_value.client.return_value = mock_s3_client
        mock_s3_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "ListObjectsV2"
        )
        
        storage = S3Storage(**storage_config)
        
        with pytest.raises(StorageError):
            await storage.cleanup_expired_images(ttl_seconds=3600)

    @patch("boto3.Session")
    async def test_get_storage_stats(self, mock_session, storage_config, mock_s3_client):
        """Test getting S3 storage statistics."""
        mock_session.return_value.client.return_value = mock_s3_client
        
        # Mock list_images to return test data
        storage = S3Storage(**storage_config)
        storage.list_images = AsyncMock(return_value=[
            {"image_id": "img1", "actual_size": 1000},
            {"image_id": "img2", "actual_size": 2000},
        ])
        
        stats = await storage.get_storage_stats()
        
        assert stats["total_images"] == 2
        assert stats["total_size_bytes"] == 3000
        assert stats["backend_type"] == "S3Storage"
        assert stats["bucket"] == "test-bucket"
        assert stats["prefix"] == "test-prefix/"

    @patch("boto3.Session")
    async def test_health_check_success(self, mock_session, storage_config, mock_s3_client):
        """Test health check succeeds with working S3."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        # Mock list_images method
        storage.list_images = AsyncMock(return_value=[])
        
        result = await storage.health_check()
        assert result is True

    @patch("boto3.Session")
    async def test_health_check_failure(self, mock_session, storage_config, mock_s3_client):
        """Test health check fails with S3 error."""
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        # Mock list_images to raise error
        storage.list_images = AsyncMock(side_effect=StorageError("S3 error"))
        
        result = await storage.health_check()
        assert result is False

    @patch("boto3.Session")
    async def test_concurrent_operations(self, mock_session, storage_config, mock_s3_client, sample_image_data, sample_metadata):
        """Test concurrent S3 operations."""
        import asyncio
        
        mock_session.return_value.client.return_value = mock_s3_client
        storage = S3Storage(**storage_config)
        
        # Save multiple images concurrently
        tasks = []
        for i in range(3):
            task = storage.save_image(sample_image_data, f"concurrent_{i}", sample_metadata)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result == f"test-prefix/concurrent_{i}.png"

    def test_get_image_key(self):
        """Test _get_image_key method."""
        storage = S3Storage(bucket="test", prefix="prefix/")
        assert storage._get_image_key("test123") == "prefix/test123.png"

    def test_get_metadata_key(self):
        """Test _get_metadata_key method."""
        storage = S3Storage(bucket="test", prefix="prefix/")
        assert storage._get_metadata_key("test123") == "prefix/test123.json"

    def test_get_keys_empty_prefix(self):
        """Test key generation with empty prefix."""
        storage = S3Storage(bucket="test", prefix="")
        assert storage._get_image_key("test123") == "test123.png"
        assert storage._get_metadata_key("test123") == "test123.json"
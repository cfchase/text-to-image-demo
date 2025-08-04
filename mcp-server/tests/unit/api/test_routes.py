"""Tests for HTTP routes and endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from api.routes import (
    delete_image,
    get_image,
    get_image_metadata,
    list_images,
    manual_cleanup,
)
from config.settings import Settings
from storage.base import ImageNotFoundError
from utils.images import ImageFormatError


class TestGetImage:
    """Test get_image endpoint."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock()
        storage.get_image.return_value = b"fake_image_data"
        return storage
    
    @pytest.mark.asyncio
    async def test_get_image_success(self, mock_storage, sample_image_data):
        """Test successful image retrieval."""
        mock_storage.get_image.return_value = sample_image_data
        
        with patch("api.routes.detect_image_format") as mock_detect, \
             patch("api.routes.get_mime_type") as mock_mime:
            
            mock_detect.return_value = "png"
            mock_mime.return_value = "image/png"
            
            response = await get_image("test-id", mock_storage)
            
            assert isinstance(response, StreamingResponse)
            assert response.media_type == "image/png"
            assert response.headers["Content-Length"] == str(len(sample_image_data))
            assert response.headers["Cache-Control"] == "public, max-age=3600"
            assert response.headers["ETag"] == '"test-id"'
            
            mock_storage.get_image.assert_called_once_with("test-id")
    
    @pytest.mark.asyncio
    async def test_get_image_not_found(self, mock_storage):
        """Test image not found."""
        mock_storage.get_image.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image("nonexistent-id", mock_storage)
        
        assert exc_info.value.status_code == 404
        assert "image_not_found" in exc_info.value.detail["error"]
        assert exc_info.value.detail["image_id"] == "nonexistent-id"
    
    @pytest.mark.asyncio
    async def test_get_image_storage_exception(self, mock_storage):
        """Test image retrieval with storage exception."""
        mock_storage.get_image.side_effect = ImageNotFoundError("Image not found in storage")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image("test-id", mock_storage)
        
        assert exc_info.value.status_code == 404
        assert "image_not_found" in exc_info.value.detail["error"]
    
    @pytest.mark.asyncio
    async def test_get_image_general_exception(self, mock_storage):
        """Test image retrieval with general exception."""
        mock_storage.get_image.side_effect = Exception("Storage failure")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image("test-id", mock_storage)
        
        assert exc_info.value.status_code == 500
        assert "storage_error" in exc_info.value.detail["error"]
    
    @pytest.mark.asyncio
    async def test_get_image_format_detection_error(self, mock_storage, sample_image_data):
        """Test image retrieval with format detection error."""
        mock_storage.get_image.return_value = sample_image_data
        
        with patch("api.routes.detect_image_format") as mock_detect:
            mock_detect.side_effect = ImageFormatError("Unknown format")
            
            response = await get_image("test-id", mock_storage)
            
            # Should fallback to default PNG content type
            assert response.media_type == "image/png"
    
    @pytest.mark.asyncio
    async def test_get_image_streaming_response(self, mock_storage, sample_image_data):
        """Test that image is returned as streaming response."""
        mock_storage.get_image.return_value = sample_image_data
        
        with patch("api.routes.detect_image_format") as mock_detect, \
             patch("api.routes.get_mime_type") as mock_mime:
            
            mock_detect.return_value = "jpeg"
            mock_mime.return_value = "image/jpeg"
            
            response = await get_image("test-id", mock_storage)
            
            assert isinstance(response, StreamingResponse)
            assert response.media_type == "image/jpeg"
            
            # Test streaming content
            content = b""
            async for chunk in response.body_iterator:
                content += chunk
            
            assert content == sample_image_data


class TestListImages:
    """Test list_images endpoint."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock()
        return storage
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.get_storage_url.return_value = "http://localhost:8000/images"
        return settings
    
    @pytest.mark.asyncio
    async def test_list_images_success(self, mock_storage, sample_metadata_list):
        """Test successful image listing."""
        mock_storage.list_images.return_value = sample_metadata_list
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await list_images(None, 100, mock_storage)
            
            assert result["count"] == 2
            assert result["truncated"] is False
            assert result["prefix"] is None
            assert result["limit"] == 100
            assert len(result["images"]) == 2
            
            # Check URLs were added
            for image in result["images"]:
                assert "url" in image
                assert image["url"].startswith("http://localhost:8000/images/")
            
            mock_storage.list_images.assert_called_once_with(prefix=None)
    
    @pytest.mark.asyncio
    async def test_list_images_with_prefix(self, mock_storage, sample_metadata_list):
        """Test image listing with prefix filter."""
        mock_storage.list_images.return_value = sample_metadata_list
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await list_images("test_", 100, mock_storage)
            
            assert result["prefix"] == "test_"
            mock_storage.list_images.assert_called_once_with(prefix="test_")
    
    @pytest.mark.asyncio
    async def test_list_images_with_limit(self, mock_storage):
        """Test image listing with limit."""
        # Create more images than limit
        large_metadata_list = [
            {"image_id": f"img_{i:03d}", "prompt": f"prompt {i}"}
            for i in range(150)
        ]
        mock_storage.list_images.return_value = large_metadata_list
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await list_images(None, 50, mock_storage)
            
            assert result["count"] == 50
            assert result["truncated"] is True
            assert result["limit"] == 50
            assert len(result["images"]) == 50
    
    @pytest.mark.asyncio
    async def test_list_images_empty(self, mock_storage):
        """Test image listing with no images."""
        mock_storage.list_images.return_value = []
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await list_images(None, 100, mock_storage)
            
            assert result["count"] == 0
            assert result["truncated"] is False
            assert len(result["images"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_images_no_image_id(self, mock_storage):
        """Test image listing with images missing image_id."""
        metadata_without_id = [
            {"prompt": "test", "width": 512},  # Missing image_id
            {"image_id": "img_002", "prompt": "test2"},
        ]
        mock_storage.list_images.return_value = metadata_without_id
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await list_images(None, 100, mock_storage)
            
            # First image should not have URL, second should
            assert "url" not in result["images"][0]
            assert "url" in result["images"][1]
    
    @pytest.mark.asyncio
    async def test_list_images_storage_error(self, mock_storage):
        """Test image listing with storage error."""
        mock_storage.list_images.side_effect = Exception("Storage failure")
        
        with pytest.raises(HTTPException) as exc_info:
            await list_images(None, 100, mock_storage)
        
        assert exc_info.value.status_code == 500
        assert "storage_error" in exc_info.value.detail["error"]


class TestDeleteImage:
    """Test delete_image endpoint."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock()
        storage.delete_image.return_value = True
        return storage
    
    @pytest.mark.asyncio
    async def test_delete_image_success(self, mock_storage):
        """Test successful image deletion."""
        result = await delete_image("test-id", mock_storage)
        
        assert result["message"] == "Image deleted successfully"
        assert result["image_id"] == "test-id"
        assert result["deleted"] is True
        
        mock_storage.delete_image.assert_called_once_with("test-id")
    
    @pytest.mark.asyncio
    async def test_delete_image_not_found(self, mock_storage):
        """Test deletion of non-existent image."""
        mock_storage.delete_image.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_image("nonexistent-id", mock_storage)
        
        assert exc_info.value.status_code == 404
        assert "image_not_found" in exc_info.value.detail["error"]
        assert exc_info.value.detail["image_id"] == "nonexistent-id"
    
    @pytest.mark.asyncio
    async def test_delete_image_storage_error(self, mock_storage):
        """Test image deletion with storage error."""
        mock_storage.delete_image.side_effect = Exception("Storage failure")
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_image("test-id", mock_storage)
        
        assert exc_info.value.status_code == 500
        assert "storage_error" in exc_info.value.detail["error"]


class TestGetImageMetadata:
    """Test get_image_metadata endpoint."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock()
        return storage
    
    @pytest.mark.asyncio
    async def test_get_image_metadata_success(self, mock_storage, sample_metadata_list):
        """Test successful metadata retrieval."""
        mock_storage.list_images.return_value = sample_metadata_list
        
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            result = await get_image_metadata("img_001", mock_storage)
            
            assert result["image_id"] == "img_001"
            assert result["prompt"] == "sunset"
            assert result["url"] == "http://localhost:8000/images/img_001"
            
            mock_storage.list_images.assert_called_once_with(prefix="img_001")
    
    @pytest.mark.asyncio
    async def test_get_image_metadata_not_found(self, mock_storage):
        """Test metadata retrieval for non-existent image."""
        mock_storage.list_images.return_value = []
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image_metadata("nonexistent-id", mock_storage)
        
        assert exc_info.value.status_code == 404
        assert "image_not_found" in exc_info.value.detail["error"]
        assert exc_info.value.detail["image_id"] == "nonexistent-id"
    
    @pytest.mark.asyncio
    async def test_get_image_metadata_no_exact_match(self, mock_storage):
        """Test metadata retrieval with no exact match."""
        # Return images with similar IDs but no exact match
        similar_metadata = [
            {"image_id": "img_001_backup", "prompt": "test1"},
            {"image_id": "img_001_copy", "prompt": "test2"},
        ]
        mock_storage.list_images.return_value = similar_metadata
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image_metadata("img_001", mock_storage)
        
        assert exc_info.value.status_code == 404
        assert "image_not_found" in exc_info.value.detail["error"]
    
    @pytest.mark.asyncio
    async def test_get_image_metadata_storage_error(self, mock_storage):
        """Test metadata retrieval with storage error."""
        mock_storage.list_images.side_effect = Exception("Storage failure")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_image_metadata("test-id", mock_storage)
        
        assert exc_info.value.status_code == 500
        assert "storage_error" in exc_info.value.detail["error"]


class TestManualCleanup:
    """Test manual_cleanup endpoint."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock()
        storage.cleanup_expired_images.return_value = 5
        return storage
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.image_ttl = 3600
        return settings
    
    @pytest.mark.asyncio
    async def test_manual_cleanup_success(self, mock_storage, mock_settings):
        """Test successful manual cleanup."""
        result = await manual_cleanup(mock_storage, mock_settings)
        
        assert result["message"] == "Cleanup completed successfully"
        assert result["deleted_count"] == 5
        assert result["ttl_seconds"] == 3600
        
        mock_storage.cleanup_expired_images.assert_called_once_with(3600)
    
    @pytest.mark.asyncio
    async def test_manual_cleanup_no_images(self, mock_storage, mock_settings):
        """Test manual cleanup with no images to delete."""
        mock_storage.cleanup_expired_images.return_value = 0
        
        result = await manual_cleanup(mock_storage, mock_settings)
        
        assert result["deleted_count"] == 0
        assert result["message"] == "Cleanup completed successfully"
    
    @pytest.mark.asyncio
    async def test_manual_cleanup_storage_error(self, mock_storage, mock_settings):
        """Test manual cleanup with storage error."""
        mock_storage.cleanup_expired_images.side_effect = Exception("Cleanup failed")
        
        with pytest.raises(HTTPException) as exc_info:
            await manual_cleanup(mock_storage, mock_settings)
        
        assert exc_info.value.status_code == 500
        assert "cleanup_error" in exc_info.value.detail["error"]


@pytest.mark.integration
class TestRouteIntegration:
    """Integration tests for route functionality."""
    
    @pytest.mark.asyncio
    async def test_full_image_lifecycle(self, sample_image_data, sample_image_metadata):
        """Test full image lifecycle through routes."""
        # Create mock storage
        mock_storage = AsyncMock()
        
        # Mock image exists
        image_id = "lifecycle-test-id"
        metadata_with_id = sample_image_metadata.copy()
        metadata_with_id["image_id"] = image_id
        
        mock_storage.get_image.return_value = sample_image_data
        mock_storage.list_images.return_value = [metadata_with_id]
        mock_storage.delete_image.return_value = True
        
        # Test image retrieval
        with patch("api.routes.detect_image_format") as mock_detect, \
             patch("api.routes.get_mime_type") as mock_mime:
            
            mock_detect.return_value = "png"
            mock_mime.return_value = "image/png"
            
            response = await get_image(image_id, mock_storage)
            assert isinstance(response, StreamingResponse)
        
        # Test metadata retrieval
        with patch("api.routes.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_storage_url.return_value = "http://localhost:8000/images"
            mock_get_settings.return_value = mock_settings
            
            metadata = await get_image_metadata(image_id, mock_storage)
            assert metadata["image_id"] == image_id
            assert "url" in metadata
        
        # Test image deletion
        result = await delete_image(image_id, mock_storage)
        assert result["deleted"] is True
        assert result["image_id"] == image_id
        
        # Verify all operations called storage correctly
        mock_storage.get_image.assert_called_with(image_id)
        mock_storage.list_images.assert_called_with(prefix=image_id)
        mock_storage.delete_image.assert_called_with(image_id)
    
    @pytest.mark.asyncio
    async def test_route_error_handling_consistency(self):
        """Test that all routes handle errors consistently."""
        mock_storage = AsyncMock()
        mock_storage.get_image.side_effect = Exception("Storage error")
        mock_storage.list_images.side_effect = Exception("Storage error")
        mock_storage.delete_image.side_effect = Exception("Storage error")
        mock_storage.cleanup_expired_images.side_effect = Exception("Storage error")
        
        mock_settings = MagicMock()
        mock_settings.image_ttl = 3600
        
        # Test all routes return 500 for storage errors
        routes_to_test = [
            (get_image, ("test-id", mock_storage)),
            (list_images, (None, 100, mock_storage)),  
            (delete_image, ("test-id", mock_storage)),
            (get_image_metadata, ("test-id", mock_storage)),
            (manual_cleanup, (mock_storage, mock_settings)),
        ]
        
        for route_func, args in routes_to_test:
            with pytest.raises(HTTPException) as exc_info:
                await route_func(*args)
            
            assert exc_info.value.status_code == 500
            assert "error" in exc_info.value.detail
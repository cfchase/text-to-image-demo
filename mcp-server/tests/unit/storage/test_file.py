"""Unit tests for FileStorage implementation."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from storage.file import FileStorage
from storage.base import StorageError


class TestFileStorage:
    """Test FileStorage implementation."""

    @pytest.fixture
    async def storage(self, tmp_path: Path) -> FileStorage:
        """Create FileStorage instance for testing."""
        return FileStorage(
            base_path=str(tmp_path),
            base_url="http://localhost:8000/images"
        )

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

    async def test_init_creates_directory(self, tmp_path: Path):
        """Test that FileStorage creates base directory."""
        base_path = tmp_path / "images"
        assert not base_path.exists()

        storage = FileStorage(
            base_path=str(base_path),
            base_url="http://localhost:8000/images"
        )

        assert base_path.exists()
        assert base_path.is_dir()
        assert storage.base_path == base_path
        assert storage.base_url == "http://localhost:8000/images"

    async def test_init_with_trailing_slash_in_url(self, tmp_path: Path):
        """Test that trailing slash is removed from base_url."""
        storage = FileStorage(
            base_path=str(tmp_path),
            base_url="http://localhost:8000/images/"
        )
        assert storage.base_url == "http://localhost:8000/images"

    async def test_save_image_success(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test successful image save."""
        image_id = "test-123"
        
        path = await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Check return value
        assert path.endswith(f"{image_id}.png")
        
        # Check files exist
        image_path = storage.base_path / f"{image_id}.png"
        metadata_path = storage.base_path / f"{image_id}.json"
        
        assert image_path.exists()
        assert metadata_path.exists()
        
        # Check image content
        with open(image_path, "rb") as f:
            saved_data = f.read()
        assert saved_data == sample_image_data
        
        # Check metadata content
        with open(metadata_path, "r", encoding="utf-8") as f:
            saved_metadata = json.load(f)
        
        assert saved_metadata["image_id"] == image_id
        assert saved_metadata["prompt"] == sample_metadata["prompt"]
        assert saved_metadata["size"] == len(sample_image_data)
        assert saved_metadata["format"] == "png"
        assert "created_at" in saved_metadata

    async def test_save_image_empty_data(
        self, storage: FileStorage, sample_metadata: Dict[str, Any]
    ):
        """Test saving empty image data raises error."""
        with pytest.raises(StorageError, match="Image data is empty"):
            await storage.save_image(b"", "test-123", sample_metadata)

    async def test_get_image_success(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test successful image retrieval."""
        image_id = "test-456"
        
        # Save image first
        await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Retrieve image
        retrieved_data = await storage.get_image(image_id)
        
        assert retrieved_data == sample_image_data

    async def test_get_image_not_found(self, storage: FileStorage):
        """Test getting non-existent image returns None."""
        result = await storage.get_image("nonexistent")
        assert result is None

    async def test_delete_image_success(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test successful image deletion."""
        image_id = "test-789"
        
        # Save image first
        await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Verify files exist
        image_path = storage.base_path / f"{image_id}.png"
        metadata_path = storage.base_path / f"{image_id}.json"
        assert image_path.exists()
        assert metadata_path.exists()
        
        # Delete image
        result = await storage.delete_image(image_id)
        
        assert result is True
        assert not image_path.exists()
        assert not metadata_path.exists()

    async def test_delete_image_not_found(self, storage: FileStorage):
        """Test deleting non-existent image returns False."""
        result = await storage.delete_image("nonexistent")
        assert result is False

    async def test_delete_image_partial_files(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test deleting when only one file exists."""
        image_id = "test-partial"
        
        # Create only image file (no metadata)
        image_path = storage.base_path / f"{image_id}.png"
        with open(image_path, "wb") as f:
            f.write(sample_image_data)
        
        # Delete should still work
        result = await storage.delete_image(image_id)
        assert result is True
        assert not image_path.exists()

    async def test_get_image_url_success(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test getting image URL for existing image."""
        image_id = "test-url"
        
        # Save image first
        await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Get URL
        url = await storage.get_image_url(image_id)
        
        assert url == f"http://localhost:8000/images/{image_id}.png"

    async def test_get_image_url_not_found(self, storage: FileStorage):
        """Test getting URL for non-existent image."""
        url = await storage.get_image_url("nonexistent")
        assert url is None

    async def test_list_images_empty(self, storage: FileStorage):
        """Test listing images when storage is empty."""
        images = await storage.list_images()
        assert images == []

    async def test_list_images_with_data(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test listing images with data."""
        # Save multiple images
        image_ids = ["img1", "img2", "img3"]
        for image_id in image_ids:
            await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # List images
        images = await storage.list_images()
        
        assert len(images) == 3
        
        # Check each image metadata
        found_ids = {img["image_id"] for img in images}
        assert found_ids == set(image_ids)
        
        for img in images:
            assert img["prompt"] == sample_metadata["prompt"]
            assert img["size"] == len(sample_image_data)
            assert "created_at" in img
            assert "modified_at" in img
            assert "actual_size" in img

    async def test_list_images_with_prefix(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test listing images with prefix filter."""
        # Save images with different prefixes
        await storage.save_image(sample_image_data, "user1_img1", sample_metadata)
        await storage.save_image(sample_image_data, "user1_img2", sample_metadata)
        await storage.save_image(sample_image_data, "user2_img1", sample_metadata)
        
        # List with prefix
        images = await storage.list_images(prefix="user1")
        
        assert len(images) == 2
        for img in images:
            assert img["image_id"].startswith("user1")

    async def test_list_images_orphaned_metadata(
        self, storage: FileStorage, sample_metadata: Dict[str, Any]
    ):
        """Test that orphaned metadata files are ignored."""
        # Create metadata file without corresponding image
        metadata_path = storage.base_path / "orphan.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(sample_metadata, f)
        
        # List should be empty
        images = await storage.list_images()
        assert images == []

    async def test_list_images_invalid_metadata(
        self, storage: FileStorage, sample_image_data: bytes
    ):
        """Test that invalid metadata files are skipped."""
        image_id = "invalid_meta"
        
        # Create image file
        image_path = storage.base_path / f"{image_id}.png"
        with open(image_path, "wb") as f:
            f.write(sample_image_data)
        
        # Create invalid metadata file
        metadata_path = storage.base_path / f"{image_id}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")
        
        # List should be empty (invalid metadata skipped)
        images = await storage.list_images()
        assert images == []

    async def test_cleanup_expired_images_none_expired(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test cleanup when no images are expired."""
        # Save a fresh image
        await storage.save_image(sample_image_data, "fresh", sample_metadata)
        
        # Cleanup with very short TTL should not delete fresh image
        deleted_count = await storage.cleanup_expired_images(ttl_seconds=1)
        
        assert deleted_count == 0
        
        # Image should still exist
        result = await storage.get_image("fresh")
        assert result is not None

    async def test_cleanup_expired_images_with_expired(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test cleanup removes expired images."""
        image_id = "old_image"
        
        # Save image
        await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Manually set old modification time
        image_path = storage.base_path / f"{image_id}.png"
        old_time = time.time() - 3600  # 1 hour ago
        os.utime(image_path, (old_time, old_time))
        
        # Cleanup with 30 minute TTL should delete the image
        deleted_count = await storage.cleanup_expired_images(ttl_seconds=1800)
        
        assert deleted_count == 1
        
        # Image should be gone
        assert not image_path.exists()
        result = await storage.get_image(image_id)
        assert result is None

    async def test_cleanup_expired_images_mixed(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test cleanup with mix of fresh and expired images."""
        # Save fresh image
        await storage.save_image(sample_image_data, "fresh", sample_metadata)
        
        # Save old image
        await storage.save_image(sample_image_data, "old", sample_metadata)
        old_image_path = storage.base_path / "old.png"
        old_time = time.time() - 3600  # 1 hour ago
        os.utime(old_image_path, (old_time, old_time))
        
        # Cleanup should only delete old image
        deleted_count = await storage.cleanup_expired_images(ttl_seconds=1800)
        
        assert deleted_count == 1
        
        # Check results
        fresh_result = await storage.get_image("fresh")
        old_result = await storage.get_image("old")
        
        assert fresh_result is not None
        assert old_result is None

    async def test_health_check_success(self, storage: FileStorage):
        """Test health check succeeds with working storage."""
        result = await storage.health_check()
        assert result is True

    async def test_get_storage_stats(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test getting storage statistics."""
        # Initially empty
        stats = await storage.get_storage_stats()
        assert stats["total_images"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["backend_type"] == "FileStorage"
        assert stats["base_path"] == str(storage.base_path)
        assert stats["base_url"] == storage.base_url
        assert stats["path_exists"] is True
        
        # Add some images
        await storage.save_image(sample_image_data, "img1", sample_metadata)
        await storage.save_image(sample_image_data, "img2", sample_metadata)
        
        # Check updated stats
        stats = await storage.get_storage_stats()
        assert stats["total_images"] == 2
        assert stats["total_size_bytes"] == len(sample_image_data) * 2

    async def test_concurrent_operations(
        self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]
    ):
        """Test concurrent save operations."""
        import asyncio
        
        # Save multiple images concurrently
        tasks = []
        for i in range(5):
            task = storage.save_image(sample_image_data, f"concurrent_{i}", sample_metadata)
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        
        # Verify all images were saved
        images = await storage.list_images()
        assert len(images) == 5
        
        # Check all images can be retrieved
        for i in range(5):
            result = await storage.get_image(f"concurrent_{i}")
            assert result == sample_image_data

    async def test_save_image_io_error(self, tmp_path: Path, sample_image_data: bytes, sample_metadata: Dict[str, Any]):
        """Test save_image handles IO errors gracefully."""
        # Create storage with read-only directory
        readonly_path = tmp_path / "readonly"
        readonly_path.mkdir()
        readonly_path.chmod(0o444)  # Read-only
        
        storage = FileStorage(str(readonly_path), "http://localhost/images")
        
        with pytest.raises(StorageError):
            await storage.save_image(sample_image_data, "test", sample_metadata)

    async def test_get_image_io_error(self, storage: FileStorage):
        """Test get_image handles IO errors gracefully."""
        # Create a file that will cause read error
        bad_path = storage.base_path / "bad.png"
        bad_path.touch()
        bad_path.chmod(0o000)  # No permissions
        
        with pytest.raises(StorageError):
            await storage.get_image("bad")

    async def test_delete_image_io_error(self, storage: FileStorage, sample_image_data: bytes, sample_metadata: Dict[str, Any]):
        """Test delete_image handles IO errors gracefully."""
        image_id = "protected"
        
        # Save image
        await storage.save_image(sample_image_data, image_id, sample_metadata)
        
        # Make file read-only
        image_path = storage.base_path / f"{image_id}.png"
        storage.base_path.chmod(0o444)  # Read-only directory
        
        with pytest.raises(StorageError):
            await storage.delete_image(image_id)
        
        # Restore permissions for cleanup
        storage.base_path.chmod(0o755)
"""Abstract base class for storage backends."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class ImageNotFoundError(StorageError):
    """Image was not found in storage."""

    pass


class StorageFullError(StorageError):
    """Storage is full or quota exceeded."""

    pass


class AbstractStorage(ABC):
    """Abstract base class for storage backends."""

    def __init__(self) -> None:
        """Initialize storage backend."""
        self._lock = asyncio.Lock()

    @abstractmethod
    async def save_image(
        self, image_data: bytes, image_id: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Save an image to storage.

        Args:
            image_data: Raw image bytes
            image_id: Unique identifier for the image
            metadata: Image generation metadata

        Returns:
            Storage path or key where image was saved

        Raises:
            StorageError: If save operation fails
            StorageFullError: If storage is full
        """
        pass

    @abstractmethod
    async def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve an image from storage.

        Args:
            image_id: Unique identifier for the image

        Returns:
            Image data bytes or None if not found

        Raises:
            StorageError: If retrieval operation fails
        """
        pass

    @abstractmethod
    async def delete_image(self, image_id: str) -> bool:
        """
        Delete an image from storage.

        Args:
            image_id: Unique identifier for the image

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        pass

    @abstractmethod
    async def get_image_url(self, image_id: str) -> Optional[str]:
        """
        Get a URL for accessing the image.

        Args:
            image_id: Unique identifier for the image

        Returns:
            URL string or None if not available

        Raises:
            StorageError: If URL generation fails
        """
        pass

    @abstractmethod
    async def list_images(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List images in storage.

        Args:
            prefix: Optional prefix to filter results

        Returns:
            List of image metadata dictionaries

        Raises:
            StorageError: If listing operation fails
        """
        pass

    @abstractmethod
    async def cleanup_expired_images(self, ttl_seconds: int) -> int:
        """
        Remove images older than TTL.

        Args:
            ttl_seconds: Time to live in seconds

        Returns:
            Number of images deleted

        Raises:
            StorageError: If cleanup operation fails
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if storage backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Basic health check - try to list images
            await self.list_images()
            return True
        except Exception as e:
            logger.error("Storage health check failed", error=str(e))
            return False

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics

        Raises:
            StorageError: If stats retrieval fails
        """
        try:
            images = await self.list_images()
            total_images = len(images)
            
            total_size = 0
            for image_meta in images:
                if "size" in image_meta:
                    total_size += image_meta["size"]

            return {
                "total_images": total_images,
                "total_size_bytes": total_size,
                "backend_type": self.__class__.__name__,
            }
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            raise StorageError(f"Failed to get storage stats: {str(e)}") from e
"""File-based storage implementation for local and PVC volumes."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiofiles
except ImportError:
    aiofiles = None
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .base import AbstractStorage, ImageNotFoundError, StorageError


class FileStorage(AbstractStorage):
    """File-based storage implementation for local and PVC volumes."""

    def __init__(self, base_path: str, base_url: str) -> None:
        """
        Initialize file storage.

        Args:
            base_path: Base directory for storing images
            base_url: Base URL for serving images
        """
        if aiofiles is None:
            raise StorageError("aiofiles package is required for FileStorage")
            
        super().__init__()
        self.base_path = Path(base_path)
        self.base_url = base_url.rstrip("/")
        
        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "FileStorage initialized",
            base_path=str(self.base_path),
            base_url=self.base_url,
        )

    async def save_image(
        self, image_data: bytes, image_id: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Save an image to the filesystem.

        Args:
            image_data: Raw image bytes
            image_id: Unique identifier for the image
            metadata: Image generation metadata

        Returns:
            File path where image was saved

        Raises:
            StorageError: If save operation fails
        """
        if not image_data:
            raise StorageError(f"Image data is empty for image_id={image_id}")

        async with self._lock:
            try:
                # Create image file path
                image_path = self.base_path / f"{image_id}.png"
                metadata_path = self.base_path / f"{image_id}.json"

                # Prepare metadata with additional info
                full_metadata = {
                    **metadata,
                    "image_id": image_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "size": len(image_data),
                    "format": "png",
                }

                # Save image file
                async with aiofiles.open(image_path, "wb") as f:
                    await f.write(image_data)

                # Save metadata file
                async with aiofiles.open(metadata_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(full_metadata, indent=2))

                logger.info(
                    "Image saved successfully",
                    image_id=image_id,
                    path=str(image_path),
                    size=len(image_data),
                )

                return str(image_path)

            except OSError as e:
                logger.error(
                    "Failed to save image",
                    image_id=image_id,
                    error=str(e),
                )
                raise StorageError(f"Failed to save image {image_id}: {str(e)}") from e

    async def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve an image from the filesystem.

        Args:
            image_id: Unique identifier for the image

        Returns:
            Image data bytes or None if not found

        Raises:
            StorageError: If retrieval operation fails
        """
        try:
            image_path = self.base_path / f"{image_id}.png"

            if not image_path.exists():
                logger.debug("Image not found", image_id=image_id, path=str(image_path))
                return None

            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()

            logger.debug(
                "Image retrieved successfully",
                image_id=image_id,
                size=len(image_data),
            )

            return image_data

        except OSError as e:
            logger.error(
                "Failed to retrieve image",
                image_id=image_id,
                error=str(e),
            )
            raise StorageError(f"Failed to retrieve image {image_id}: {str(e)}") from e

    async def delete_image(self, image_id: str) -> bool:
        """
        Delete an image from the filesystem.

        Args:
            image_id: Unique identifier for the image

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        async with self._lock:
            try:
                image_path = self.base_path / f"{image_id}.png"
                metadata_path = self.base_path / f"{image_id}.json"

                deleted = False

                # Delete image file
                if image_path.exists():
                    image_path.unlink()
                    deleted = True

                # Delete metadata file
                if metadata_path.exists():
                    metadata_path.unlink()
                    deleted = True

                if deleted:
                    logger.info("Image deleted successfully", image_id=image_id)
                else:
                    logger.debug("Image not found for deletion", image_id=image_id)

                return deleted

            except OSError as e:
                logger.error(
                    "Failed to delete image",
                    image_id=image_id,
                    error=str(e),
                )
                raise StorageError(f"Failed to delete image {image_id}: {str(e)}") from e

    async def get_image_url(self, image_id: str) -> Optional[str]:
        """
        Get a URL for accessing the image.

        Args:
            image_id: Unique identifier for the image

        Returns:
            URL string or None if not available
        """
        image_path = self.base_path / f"{image_id}.png"

        if not image_path.exists():
            return None

        url = f"{self.base_url}/{image_id}.png"
        logger.debug("Generated image URL", image_id=image_id, url=url)
        return url

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
        try:
            images = []

            # Find all JSON metadata files
            pattern = f"{prefix}*.json" if prefix else "*.json"
            
            for metadata_path in self.base_path.glob(pattern):
                try:
                    # Load metadata
                    async with aiofiles.open(metadata_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                        metadata = json.loads(content)

                    # Verify corresponding image file exists
                    image_id = metadata_path.stem
                    image_path = self.base_path / f"{image_id}.png"
                    
                    if image_path.exists():
                        # Update metadata with current file stats
                        stat = image_path.stat()
                        metadata.update({
                            "path": str(image_path),
                            "modified_at": datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ).isoformat(),
                            "actual_size": stat.st_size,
                        })
                        images.append(metadata)

                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(
                        "Failed to load metadata",
                        path=str(metadata_path),
                        error=str(e),
                    )
                    continue

            logger.debug("Listed images", count=len(images), prefix=prefix)
            return images

        except OSError as e:
            logger.error("Failed to list images", error=str(e))
            raise StorageError(f"Failed to list images: {str(e)}") from e

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
        async with self._lock:
            try:
                current_time = time.time()
                cutoff_time = current_time - ttl_seconds
                deleted_count = 0

                # Find all image files
                for image_path in self.base_path.glob("*.png"):
                    try:
                        # Check file modification time
                        stat = image_path.stat()
                        if stat.st_mtime < cutoff_time:
                            image_id = image_path.stem
                            
                            # Delete both image and metadata files
                            metadata_path = self.base_path / f"{image_id}.json"
                            
                            image_path.unlink()
                            if metadata_path.exists():
                                metadata_path.unlink()
                            
                            deleted_count += 1
                            logger.debug(
                                "Expired image deleted",
                                image_id=image_id,
                                age_seconds=int(current_time - stat.st_mtime),
                            )

                    except OSError as e:
                        logger.warning(
                            "Failed to delete expired image",
                            path=str(image_path),
                            error=str(e),
                        )
                        continue

                logger.info(
                    "Cleanup completed",
                    deleted_count=deleted_count,
                    ttl_seconds=ttl_seconds,
                )

                return deleted_count

            except OSError as e:
                logger.error("Failed to cleanup expired images", error=str(e))
                raise StorageError(f"Failed to cleanup expired images: {str(e)}") from e

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            images = await self.list_images()
            total_images = len(images)
            total_size = sum(img.get("actual_size", 0) for img in images)

            # Get filesystem stats
            base_stat = self.base_path.stat() if self.base_path.exists() else None
            
            return {
                "total_images": total_images,
                "total_size_bytes": total_size,
                "backend_type": "FileStorage",
                "base_path": str(self.base_path),
                "base_url": self.base_url,
                "path_exists": self.base_path.exists(),
                "path_writable": self.base_path.exists() and 
                               (self.base_path / ".write_test").parent.exists(),
            }

        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            raise StorageError(f"Failed to get storage stats: {str(e)}") from e
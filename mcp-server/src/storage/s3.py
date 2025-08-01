"""S3-compatible storage implementation."""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .base import AbstractStorage, ImageNotFoundError, StorageError


class S3Storage(AbstractStorage):
    """S3-compatible storage implementation."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        presigned_url_ttl: int = 3600,
    ) -> None:
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix for all objects
            endpoint_url: Custom S3 endpoint (for MinIO, etc.)
            access_key_id: AWS access key
            secret_access_key: AWS secret key
            region_name: AWS region
            presigned_url_ttl: TTL for presigned URLs in seconds
        """
        super().__init__()
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        if self.prefix:
            self.prefix += "/"
        self.presigned_url_ttl = presigned_url_ttl

        if boto3 is None:
            raise StorageError("boto3 package is required for S3Storage")
            
        # Configure S3 client
        try:
            session = boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region_name,
            )

            self.client = session.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region_name,
            )

            logger.info(
                "S3Storage initialized",
                bucket=self.bucket,
                prefix=self.prefix,
                endpoint_url=endpoint_url,
                region=region_name,
            )

        except NoCredentialsError as e:
            logger.error("S3 credentials not found", error=str(e))
            raise StorageError(f"S3 credentials not found: {str(e)}") from e
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            raise StorageError(f"Failed to initialize S3 client: {str(e)}") from e

    def _get_image_key(self, image_id: str) -> str:
        """Get S3 key for image."""
        return f"{self.prefix}{image_id}.png"

    def _get_metadata_key(self, image_id: str) -> str:
        """Get S3 key for metadata."""
        return f"{self.prefix}{image_id}.json"

    async def save_image(
        self, image_data: bytes, image_id: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Save an image to S3.

        Args:
            image_data: Raw image bytes
            image_id: Unique identifier for the image
            metadata: Image generation metadata

        Returns:
            S3 key where image was saved

        Raises:
            StorageError: If save operation fails
        """
        if not image_data:
            raise StorageError(f"Image data is empty for image_id={image_id}")

        async with self._lock:
            try:
                image_key = self._get_image_key(image_id)
                metadata_key = self._get_metadata_key(image_id)

                # Prepare metadata with additional info
                full_metadata = {
                    **metadata,
                    "image_id": image_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "size": len(image_data),
                    "format": "png",
                    "s3_key": image_key,
                }

                # Upload image
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=image_key,
                    Body=image_data,
                    ContentType="image/png",
                    Metadata={
                        "image-id": image_id,
                        "created-at": full_metadata["created_at"],
                    },
                )

                # Upload metadata
                metadata_json = json.dumps(full_metadata, indent=2)
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=metadata_key,
                    Body=metadata_json.encode("utf-8"),
                    ContentType="application/json",
                )

                logger.info(
                    "Image saved to S3",
                    image_id=image_id,
                    bucket=self.bucket,
                    key=image_key,
                    size=len(image_data),
                )

                return image_key

            except ClientError as e:
                logger.error(
                    "Failed to save image to S3",
                    image_id=image_id,
                    bucket=self.bucket,
                    error=str(e),
                )
                raise StorageError(f"Failed to save image {image_id}: {str(e)}") from e

    async def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve an image from S3.

        Args:
            image_id: Unique identifier for the image

        Returns:
            Image data bytes or None if not found

        Raises:
            StorageError: If retrieval operation fails
        """
        try:
            image_key = self._get_image_key(image_id)

            response = self.client.get_object(Bucket=self.bucket, Key=image_key)
            image_data = response["Body"].read()

            logger.debug(
                "Image retrieved from S3",
                image_id=image_id,
                bucket=self.bucket,
                key=image_key,
                size=len(image_data),
            )

            return image_data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.debug(
                    "Image not found in S3", image_id=image_id, bucket=self.bucket
                )
                return None
            else:
                logger.error(
                    "Failed to retrieve image from S3",
                    image_id=image_id,
                    bucket=self.bucket,
                    error=str(e),
                )
                raise StorageError(f"Failed to retrieve image {image_id}: {str(e)}") from e

    async def delete_image(self, image_id: str) -> bool:
        """
        Delete an image from S3.

        Args:
            image_id: Unique identifier for the image

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        async with self._lock:
            try:
                image_key = self._get_image_key(image_id)
                metadata_key = self._get_metadata_key(image_id)

                # Check if image exists first
                try:
                    self.client.head_object(Bucket=self.bucket, Key=image_key)
                except ClientError as e:
                    if e.response.get("Error", {}).get("Code") == "404":
                        logger.debug("Image not found for deletion", image_id=image_id)
                        return False
                    raise

                # Delete both image and metadata
                objects_to_delete = [
                    {"Key": image_key},
                    {"Key": metadata_key},
                ]

                self.client.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": objects_to_delete}
                )

                logger.info(
                    "Image deleted from S3",
                    image_id=image_id,
                    bucket=self.bucket,
                    key=image_key,
                )

                return True

            except ClientError as e:
                logger.error(
                    "Failed to delete image from S3",
                    image_id=image_id,
                    bucket=self.bucket,
                    error=str(e),
                )
                raise StorageError(f"Failed to delete image {image_id}: {str(e)}") from e

    async def get_image_url(self, image_id: str) -> Optional[str]:
        """
        Get a presigned URL for accessing the image.

        Args:
            image_id: Unique identifier for the image

        Returns:
            Presigned URL string or None if not available

        Raises:
            StorageError: If URL generation fails
        """
        try:
            image_key = self._get_image_key(image_id)

            # Check if image exists
            try:
                self.client.head_object(Bucket=self.bucket, Key=image_key)
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "404":
                    logger.debug("Image not found for URL generation", image_id=image_id)
                    return None
                raise

            # Generate presigned URL
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": image_key},
                ExpiresIn=self.presigned_url_ttl,
            )

            logger.debug(
                "Generated presigned URL",
                image_id=image_id,
                bucket=self.bucket,
                key=image_key,
                ttl=self.presigned_url_ttl,
            )

            return url

        except ClientError as e:
            logger.error(
                "Failed to generate presigned URL",
                image_id=image_id,
                bucket=self.bucket,
                error=str(e),
            )
            raise StorageError(f"Failed to generate URL for image {image_id}: {str(e)}") from e

    async def list_images(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List images in S3.

        Args:
            prefix: Optional prefix to filter results

        Returns:
            List of image metadata dictionaries

        Raises:
            StorageError: If listing operation fails
        """
        try:
            search_prefix = self.prefix
            if prefix:
                search_prefix += prefix

            # List all metadata files
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket, Prefix=search_prefix, Delimiter=""
            )

            images = []
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    
                    # Only process JSON metadata files
                    if not key.endswith(".json"):
                        continue

                    try:
                        # Get metadata object
                        response = self.client.get_object(Bucket=self.bucket, Key=key)
                        content = response["Body"].read().decode("utf-8")
                        metadata = json.loads(content)

                        # Verify corresponding image exists
                        image_id = key.replace(self.prefix, "").replace(".json", "")
                        image_key = self._get_image_key(image_id)

                        try:
                            img_response = self.client.head_object(
                                Bucket=self.bucket, Key=image_key
                            )
                            
                            # Update metadata with S3 object info
                            metadata.update({
                                "s3_key": image_key,
                                "bucket": self.bucket,
                                "last_modified": img_response["LastModified"].isoformat(),
                                "etag": img_response["ETag"].strip('"'),
                                "actual_size": img_response["ContentLength"],
                            })
                            
                            images.append(metadata)

                        except ClientError as e:
                            if e.response.get("Error", {}).get("Code") != "404":
                                logger.warning(
                                    "Failed to get image object info",
                                    key=image_key,
                                    error=str(e),
                                )

                    except (json.JSONDecodeError, ClientError) as e:
                        logger.warning(
                            "Failed to load metadata from S3",
                            key=key,
                            error=str(e),
                        )
                        continue

            logger.debug("Listed images from S3", count=len(images), prefix=prefix)
            return images

        except ClientError as e:
            logger.error("Failed to list images from S3", error=str(e))
            raise StorageError(f"Failed to list images: {str(e)}") from e

    async def cleanup_expired_images(self, ttl_seconds: int) -> int:
        """
        Remove images older than TTL from S3.

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

                # List all objects
                paginator = self.client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)

                objects_to_delete = []

                for page in pages:
                    for obj in page.get("Contents", []):
                        # Check if object is older than TTL
                        last_modified = obj["LastModified"].timestamp()
                        if last_modified < cutoff_time:
                            objects_to_delete.append({"Key": obj["Key"]})

                # Delete expired objects in batches
                batch_size = 1000  # S3 limit
                for i in range(0, len(objects_to_delete), batch_size):
                    batch = objects_to_delete[i : i + batch_size]
                    if batch:
                        self.client.delete_objects(
                            Bucket=self.bucket, Delete={"Objects": batch}
                        )
                        deleted_count += len(batch)

                # Count only image files (not metadata)
                image_deleted_count = sum(
                    1 for obj in objects_to_delete if obj["Key"].endswith(".png")
                )

                logger.info(
                    "S3 cleanup completed",
                    deleted_objects=deleted_count,
                    deleted_images=image_deleted_count,
                    ttl_seconds=ttl_seconds,
                    bucket=self.bucket,
                )

                return image_deleted_count

            except ClientError as e:
                logger.error("Failed to cleanup expired images from S3", error=str(e))
                raise StorageError(f"Failed to cleanup expired images: {str(e)}") from e

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get S3 storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            images = await self.list_images()
            total_images = len(images)
            total_size = sum(img.get("actual_size", 0) for img in images)

            return {
                "total_images": total_images,
                "total_size_bytes": total_size,
                "backend_type": "S3Storage",
                "bucket": self.bucket,
                "prefix": self.prefix,
                "presigned_url_ttl": self.presigned_url_ttl,
            }

        except Exception as e:
            logger.error("Failed to get S3 storage stats", error=str(e))
            raise StorageError(f"Failed to get storage stats: {str(e)}") from e
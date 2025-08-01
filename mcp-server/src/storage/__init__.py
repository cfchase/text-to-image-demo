"""Storage backend implementations and factory."""

from typing import Dict, Type

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .base import AbstractStorage, ImageNotFoundError, StorageError, StorageFullError
from .file import FileStorage
from .s3 import S3Storage

# Registry of available storage backends
STORAGE_BACKENDS: Dict[str, Type[AbstractStorage]] = {
    "file": FileStorage,
    "s3": S3Storage,
}


def create_storage(backend_type: str, **kwargs) -> AbstractStorage:
    """
    Create a storage backend instance.

    Args:
        backend_type: Type of storage backend ("file" or "s3")
        **kwargs: Backend-specific configuration parameters

    Returns:
        Configured storage backend instance

    Raises:
        ValueError: If backend_type is not supported
        StorageError: If backend configuration fails

    Example:
        Create file storage:
        >>> storage = create_storage(
        ...     "file",
        ...     base_path="/data/images",
        ...     base_url="http://localhost:8000/images"
        ... )

        Create S3 storage:
        >>> storage = create_storage(
        ...     "s3",
        ...     bucket="my-images",
        ...     prefix="mcp/",
        ...     endpoint_url="http://minio:9000"
        ... )
    """
    if backend_type not in STORAGE_BACKENDS:
        supported = ", ".join(STORAGE_BACKENDS.keys())
        raise ValueError(
            f"Unsupported storage backend '{backend_type}'. "
            f"Supported backends: {supported}"
        )

    try:
        backend_class = STORAGE_BACKENDS[backend_type]
        storage = backend_class(**kwargs)
        
        logger.info(
            "Storage backend created",
            backend_type=backend_type,
            backend_class=backend_class.__name__,
        )
        
        return storage

    except Exception as e:
        logger.error(
            "Failed to create storage backend",
            backend_type=backend_type,
            error=str(e),
        )
        raise StorageError(f"Failed to create {backend_type} storage: {str(e)}") from e


def create_file_storage(base_path: str, base_url: str) -> FileStorage:
    """
    Create a file storage instance.

    Args:
        base_path: Base directory for storing images
        base_url: Base URL for serving images

    Returns:
        Configured FileStorage instance
    """
    return FileStorage(base_path=base_path, base_url=base_url)


def create_s3_storage(
    bucket: str,
    prefix: str = "",
    endpoint_url: str = None,
    **kwargs
) -> S3Storage:
    """
    Create an S3 storage instance.

    Args:
        bucket: S3 bucket name
        prefix: Key prefix for all objects
        endpoint_url: Custom S3 endpoint (for MinIO, etc.)
        **kwargs: Additional S3Storage parameters

    Returns:
        Configured S3Storage instance
    """
    return S3Storage(
        bucket=bucket,
        prefix=prefix,
        endpoint_url=endpoint_url,
        **kwargs
    )


# Export all public classes and functions
__all__ = [
    # Base classes and exceptions
    "AbstractStorage",
    "StorageError",
    "ImageNotFoundError", 
    "StorageFullError",
    
    # Concrete implementations
    "FileStorage",
    "S3Storage",
    
    # Factory functions
    "create_storage",
    "create_file_storage",
    "create_s3_storage",
    
    # Registry
    "STORAGE_BACKENDS",
]
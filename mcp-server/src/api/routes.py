"""HTTP endpoints for image serving."""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from config.settings import Settings
from storage.base import AbstractStorage, ImageNotFoundError
from utils.images import get_mime_type, detect_image_format

# Get logger
logger = structlog.get_logger(__name__)

# Create router
router = APIRouter()


async def get_storage() -> AbstractStorage:
    """Get storage backend dependency."""
    # Import here to avoid circular imports
    from api.app import get_storage as _get_storage
    return _get_storage()


async def get_settings() -> Settings:
    """Get settings dependency."""
    # Import here to avoid circular imports
    from api.app import get_settings as _get_settings
    return _get_settings()


@router.get("/{image_id}")
async def get_image(
    image_id: str,
    storage: AbstractStorage = Depends(get_storage),
) -> Response:
    """
    Retrieve a generated image.
    
    Args:
        image_id: Unique image identifier
        storage: Storage backend
        
    Returns:
        Image file response
        
    Raises:
        404: Image not found
        500: Storage error
    """
    logger.info(
        "Image requested",
        image_id=image_id,
    )
    
    try:
        # Get image data from storage
        image_data = await storage.get_image(image_id)
        
        if image_data is None:
            logger.warning(
                "Image not found",
                image_id=image_id,
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "image_not_found",
                    "message": f"Image with ID '{image_id}' not found",
                    "image_id": image_id,
                }
            )
        
        # Detect content type
        try:
            image_format = detect_image_format(image_data)
            content_type = get_mime_type(image_format)
        except Exception as e:
            logger.warning(
                "Failed to detect image format, using default",
                image_id=image_id,
                error=str(e),
            )
            content_type = "image/png"  # Default fallback
        
        logger.info(
            "Image served successfully",
            image_id=image_id,
            content_type=content_type,
            size=len(image_data),
        )
        
        # Create streaming response for efficient memory usage
        def generate():
            yield image_data
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={
                "Content-Length": str(len(image_data)),
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "ETag": f'"{image_id}"',
            }
        )
        
    except ImageNotFoundError:
        logger.warning(
            "Image not found in storage",
            image_id=image_id,
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "image_not_found",
                "message": f"Image with ID '{image_id}' not found",
                "image_id": image_id,
            }
        )
        
    except Exception as e:
        logger.error(
            "Failed to retrieve image",
            image_id=image_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "storage_error",
                "message": "Failed to retrieve image",
                "image_id": image_id,
            }
        )


@router.get("/")
async def list_images(
    prefix: Optional[str] = Query(None, description="Filter images by prefix"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of images to return"),
    storage: AbstractStorage = Depends(get_storage),
) -> Dict[str, Any]:
    """
    List generated images.
    
    Args:
        prefix: Optional prefix filter
        limit: Maximum results to return
        storage: Storage backend
        
    Returns:
        List of image metadata
    """
    logger.info(
        "Images list requested",
        prefix=prefix,
        limit=limit,
    )
    
    try:
        # Get images from storage
        images = await storage.list_images(prefix=prefix)
        
        # Limit results
        if len(images) > limit:
            images = images[:limit]
            truncated = True
        else:
            truncated = False
        
        # Add URLs to each image
        settings = await get_settings()
        base_url = settings.get_storage_url()
        
        for image in images:
            image_id = image.get("image_id")
            if image_id:
                image["url"] = f"{base_url}/{image_id}"
        
        logger.info(
            "Images listed successfully",
            count=len(images),
            truncated=truncated,
            prefix=prefix,
        )
        
        return {
            "images": images,
            "count": len(images),
            "truncated": truncated,
            "prefix": prefix,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(
            "Failed to list images",
            prefix=prefix,
            limit=limit,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "storage_error",
                "message": "Failed to list images",
            }
        )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    storage: AbstractStorage = Depends(get_storage),
) -> Dict[str, Any]:
    """
    Delete a generated image.
    
    Args:
        image_id: Unique image identifier
        storage: Storage backend
        
    Returns:
        Deletion status
        
    Raises:
        404: Image not found
        500: Storage error
    """
    logger.info(
        "Image deletion requested",
        image_id=image_id,
    )
    
    try:
        # Delete image from storage
        deleted = await storage.delete_image(image_id)
        
        if not deleted:
            logger.warning(
                "Image not found for deletion",
                image_id=image_id,
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "image_not_found",
                    "message": f"Image with ID '{image_id}' not found",
                    "image_id": image_id,
                }
            )
        
        logger.info(
            "Image deleted successfully",
            image_id=image_id,
        )
        
        return {
            "message": "Image deleted successfully",
            "image_id": image_id,
            "deleted": True,
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(
            "Failed to delete image",
            image_id=image_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "storage_error",
                "message": "Failed to delete image",
                "image_id": image_id,
            }
        )


@router.get("/{image_id}/metadata")
async def get_image_metadata(
    image_id: str,
    storage: AbstractStorage = Depends(get_storage),
) -> Dict[str, Any]:
    """
    Get metadata for a generated image.
    
    Args:
        image_id: Unique image identifier
        storage: Storage backend
        
    Returns:
        Image metadata
        
    Raises:
        404: Image not found
        500: Storage error
    """
    logger.info(
        "Image metadata requested",
        image_id=image_id,
    )
    
    try:
        # Get image list with this specific ID as prefix
        images = await storage.list_images(prefix=image_id)
        
        # Find exact match
        image_metadata = None
        for image in images:
            if image.get("image_id") == image_id:
                image_metadata = image
                break
        
        if image_metadata is None:
            logger.warning(
                "Image metadata not found",
                image_id=image_id,
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "image_not_found",
                    "message": f"Image with ID '{image_id}' not found",
                    "image_id": image_id,
                }
            )
        
        # Add URL to metadata
        settings = await get_settings()
        base_url = settings.get_storage_url()
        image_metadata["url"] = f"{base_url}/{image_id}"
        
        logger.info(
            "Image metadata retrieved successfully",
            image_id=image_id,
        )
        
        return image_metadata
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(
            "Failed to get image metadata",
            image_id=image_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "storage_error",
                "message": "Failed to get image metadata",
                "image_id": image_id,
            }
        )


@router.post("/cleanup")
async def manual_cleanup(
    storage: AbstractStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Manually trigger image cleanup.
    
    Args:
        storage: Storage backend
        settings: Application settings
        
    Returns:
        Cleanup results
    """
    logger.info("Manual cleanup requested")
    
    try:
        # Run cleanup
        deleted_count = await storage.cleanup_expired_images(settings.image_ttl)
        
        logger.info(
            "Manual cleanup completed",
            deleted_count=deleted_count,
            ttl=settings.image_ttl,
        )
        
        return {
            "message": "Cleanup completed successfully",
            "deleted_count": deleted_count,
            "ttl_seconds": settings.image_ttl,
        }
        
    except Exception as e:
        logger.error(
            "Manual cleanup failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cleanup_error",
                "message": "Failed to run cleanup",
            }
        )
"""FastMCP-based MCP server for image generation."""

import base64
from typing import Any, Dict, Optional

import structlog
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from mcp_server.config.settings import Settings
from mcp_server.kserve.client import KServeClient
from mcp_server.kserve.exceptions import KServeError
from mcp_server.storage.base import AbstractStorage
from mcp_server.utils.ids import generate_image_id
from mcp_server.utils.images import (
    decode_image_base64,
    validate_image,
    ImageValidationError,
)

# Get logger
logger = structlog.get_logger(__name__)


class GenerateImageParams(BaseModel):
    """Parameters for image generation."""
    
    prompt: str = Field(..., description="Text prompt for image generation", min_length=1, max_length=1000)
    negative_prompt: Optional[str] = Field(None, description="Negative prompt to avoid features", max_length=1000)
    width: int = Field(512, ge=64, le=2048, description="Image width in pixels")
    height: int = Field(512, ge=64, le=2048, description="Image height in pixels")
    num_inference_steps: int = Field(50, ge=1, le=200, description="Number of denoising steps")
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0, description="Guidance scale")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class GenerateImageResponse(BaseModel):
    """Response from image generation."""
    
    url: str = Field(..., description="URL to access the generated image")
    image_id: str = Field(..., description="Unique identifier for the image")
    metadata: Dict[str, Any] = Field(..., description="Generation metadata")


class MCPImageError(Exception):
    """Base exception for MCP image server."""
    pass


class ValidationError(MCPImageError):
    """Input validation failed."""
    pass


class ImageGenerationError(MCPImageError):
    """Image generation failed."""
    pass


class StorageError(MCPImageError):
    """Storage operation failed."""
    pass


class MCPImageServer:
    """MCP server for image generation using KServe."""
    
    def __init__(
        self,
        settings: Settings,
        kserve_client: KServeClient,
        storage: AbstractStorage,
    ):
        """
        Initialize MCP image server.
        
        Args:
            settings: Application settings
            kserve_client: KServe client for image generation
            storage: Storage backend for images
        """
        self.settings = settings
        self.kserve_client = kserve_client
        self.storage = storage
        
        # Create FastMCP app
        self.app = FastMCP("MCP Image Generation Server")
        
        # Register the generate_image tool
        self.app.add_tool(
            self.generate_image,
            name="generate_image",
            description="Generate an image from a text prompt using Stable Diffusion"
        )
        
        logger.info(
            "MCP image server initialized",
            service_name=settings.service_name,
            kserve_endpoint=settings.kserve_endpoint,
            storage_backend=settings.storage_backend,
        )
    
    async def generate_image(self, params: GenerateImageParams) -> GenerateImageResponse:
        """
        Generate an image from a text prompt.
        
        Args:
            params: Image generation parameters
            
        Returns:
            Image generation response with URL and metadata
            
        Raises:
            ValidationError: If parameters are invalid
            ImageGenerationError: If generation fails
            StorageError: If storage fails
        """
        request_id = generate_image_id()
        
        logger.info(
            "Starting image generation",
            request_id=request_id,
            prompt=params.prompt[:100] + "..." if len(params.prompt) > 100 else params.prompt,
            width=params.width,
            height=params.height,
            steps=params.num_inference_steps,
            guidance_scale=params.guidance_scale,
            seed=params.seed,
        )
        
        try:
            # Validate parameters
            self._validate_parameters(params)
            
            # Generate image via KServe
            kserve_response = await self.kserve_client.generate_image(
                prompt=params.prompt,
                negative_prompt=params.negative_prompt,
                width=params.width,
                height=params.height,
                num_inference_steps=params.num_inference_steps,
                guidance_scale=params.guidance_scale,
                seed=params.seed,
            )
            
            logger.info(
                "Image generated successfully",
                request_id=request_id,
                generation_time=kserve_response.generation_time,
                image_size=len(kserve_response.image_data),
            )
            
            # Validate generated image
            try:
                validate_image(
                    kserve_response.image_data,
                    max_size=self.settings.max_image_size
                )
            except ImageValidationError as e:
                logger.error(
                    "Generated image validation failed",
                    request_id=request_id,
                    error=str(e),
                )
                raise ValidationError(f"Generated image validation failed: {str(e)}")
            
            # Store image
            try:
                storage_path = await self.storage.save_image(
                    image_data=kserve_response.image_data,
                    image_id=request_id,
                    metadata=kserve_response.metadata,
                )
                
                # Get image URL
                image_url = await self.storage.get_image_url(request_id)
                if not image_url:
                    # Fallback to constructing URL
                    image_url = f"{self.settings.get_storage_url()}/{request_id}"
                
                logger.info(
                    "Image stored successfully",
                    request_id=request_id,
                    storage_path=storage_path,
                    image_url=image_url,
                )
                
            except Exception as e:
                logger.error(
                    "Failed to store image",
                    request_id=request_id,
                    error=str(e),
                )
                raise StorageError(f"Failed to store image: {str(e)}")
            
            # Prepare response metadata
            response_metadata = kserve_response.metadata.copy()
            response_metadata.update({
                "image_id": request_id,
                "storage_path": storage_path,
                "created_at": response_metadata.get("created_at"),
                "file_size": len(kserve_response.image_data),
            })
            
            return GenerateImageResponse(
                url=image_url,
                image_id=request_id,
                metadata=response_metadata,
            )
            
        except KServeError as e:
            logger.error(
                "KServe image generation failed",
                request_id=request_id,
                error=str(e),
            )
            raise ImageGenerationError(f"Image generation failed: {str(e)}")
        
        except (ValidationError, ImageGenerationError, StorageError):
            # Re-raise our custom exceptions
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during image generation",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ImageGenerationError(f"Unexpected error: {str(e)}")
    
    def _validate_parameters(self, params: GenerateImageParams) -> None:
        """
        Validate image generation parameters.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValidationError: If parameters are invalid
        """
        # Additional validation beyond Pydantic
        if not params.prompt.strip():
            raise ValidationError("Prompt cannot be empty or whitespace only")
        
        # Check for reasonable dimensions
        total_pixels = params.width * params.height
        if total_pixels > 4194304:  # 2048x2048
            raise ValidationError(
                f"Image dimensions too large: {params.width}x{params.height} "
                f"({total_pixels} pixels). Maximum: 4,194,304 pixels"
            )
        
        # Validate guidance scale for specific ranges
        if params.guidance_scale < 1.0:
            raise ValidationError("Guidance scale must be at least 1.0")
        
        # Validate seed if provided
        if params.seed is not None:
            if params.seed < 0 or params.seed > 2**32 - 1:
                raise ValidationError("Seed must be between 0 and 2^32-1")
        
        logger.debug(
            "Parameters validated successfully",
            prompt_length=len(params.prompt),
            dimensions=f"{params.width}x{params.height}",
            total_pixels=total_pixels,
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of MCP server components.
        
        Returns:
            Health status information
        """
        logger.debug("Performing health check")
        
        health_status = {
            "service": "healthy",
            "kserve": "unknown",
            "storage": "unknown",
            "timestamp": "unknown",
        }
        
        try:
            # Check KServe health
            kserve_healthy = await self.kserve_client.health_check()
            health_status["kserve"] = "healthy" if kserve_healthy else "unhealthy"
        except Exception as e:
            logger.warning("KServe health check failed", error=str(e))
            health_status["kserve"] = "unhealthy"
        
        try:
            # Basic storage check - try to list images (should not fail)
            await self.storage.list_images(prefix="health_check_")
            health_status["storage"] = "healthy"
        except Exception as e:
            logger.warning("Storage health check failed", error=str(e))
            health_status["storage"] = "unhealthy"
        
        # Overall status
        if health_status["kserve"] == "healthy" and health_status["storage"] == "healthy":
            health_status["service"] = "healthy"
        else:
            health_status["service"] = "degraded"
        
        from datetime import datetime, timezone
        health_status["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            "Health check completed",
            status=health_status["service"],
            kserve_status=health_status["kserve"],
            storage_status=health_status["storage"],
        )
        
        return health_status
    
    async def close(self) -> None:
        """Close MCP server and cleanup resources."""
        logger.info("Shutting down MCP server")
        
        try:
            await self.kserve_client.close()
            logger.info("KServe client closed")
        except Exception as e:
            logger.warning("Error closing KServe client", error=str(e))
        
        logger.info("MCP server shutdown complete")
    
    def get_app(self) -> FastMCP:
        """Get the FastMCP app instance."""
        return self.app


def create_mcp_server(
    settings: Settings,
    kserve_client: KServeClient,
    storage: AbstractStorage,
) -> MCPImageServer:
    """
    Create and configure MCP image server.
    
    Args:
        settings: Application settings
        kserve_client: KServe client for image generation
        storage: Storage backend for images
        
    Returns:
        Configured MCP image server
    """
    return MCPImageServer(
        settings=settings,
        kserve_client=kserve_client,
        storage=storage,
    )
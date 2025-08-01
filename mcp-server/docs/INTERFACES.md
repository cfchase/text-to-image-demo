# Component Interface Specifications

## Storage System Interfaces

### AbstractStorage (Base Class)
```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

class AbstractStorage(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def save_image(self, image_data: bytes, image_id: str, metadata: Dict[str, Any]) -> str:
        """
        Save an image to storage.
        
        Args:
            image_data: Raw image bytes
            image_id: Unique identifier for the image
            metadata: Image generation metadata
            
        Returns:
            Storage path or key where image was saved
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
        """
        pass
```

### FileStorage Implementation
```python
class FileStorage(AbstractStorage):
    """File-based storage implementation for local and PVC volumes."""
    
    def __init__(self, base_path: str, base_url: str):
        """
        Initialize file storage.
        
        Args:
            base_path: Base directory for storing images
            base_url: Base URL for serving images
        """
        self.base_path = Path(base_path)
        self.base_url = base_url
        self.base_path.mkdir(parents=True, exist_ok=True)
```

### S3Storage Implementation
```python
class S3Storage(AbstractStorage):
    """S3-compatible storage implementation."""
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialize S3 storage.
        
        Args:
            bucket: S3 bucket name
            prefix: Key prefix for all objects
            endpoint_url: Custom S3 endpoint (for MinIO, etc.)
            access_key_id: AWS access key
            secret_access_key: AWS secret key
            region_name: AWS region
        """
```

## KServe Client Interface

### KServeClient
```python
from typing import Dict, Any, Optional
import httpx

class KServeClient:
    """Client for interacting with KServe inference endpoints."""
    
    def __init__(
        self,
        endpoint: str,
        model_name: str,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        """
        Initialize KServe client.
        
        Args:
            endpoint: Base URL for KServe endpoint
            model_name: Name of the model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint = endpoint
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an image using the diffusers runtime.
        
        Args:
            prompt: Text prompt for generation
            negative_prompt: Negative prompt to avoid features
            width: Image width in pixels
            height: Image height in pixels
            num_inference_steps: Number of denoising steps
            guidance_scale: Guidance scale for generation
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary containing:
                - image_data: Base64 encoded image
                - metadata: Generation parameters
                
        Raises:
            KServeError: If generation fails
        """
    
    async def health_check(self) -> bool:
        """
        Check if the KServe endpoint is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
```

## MCP Tool Interface

### GenerateImageTool
```python
from fastmcp import Tool
from pydantic import BaseModel, Field
from typing import Optional

class GenerateImageParams(BaseModel):
    """Parameters for image generation."""
    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt to avoid features")
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

class GenerateImageTool(Tool):
    """MCP tool for generating images."""
    
    name = "generate_image"
    description = "Generate an image from a text prompt using Stable Diffusion"
    parameters = GenerateImageParams
    response = GenerateImageResponse
    
    async def execute(self, params: GenerateImageParams) -> GenerateImageResponse:
        """Execute image generation."""
```

## Configuration Interface

### Settings
```python
from pydantic import BaseSettings, Field
from typing import Optional, Literal

class Settings(BaseSettings):
    """Application settings."""
    
    # Service Configuration
    service_name: str = Field("mcp-image-server", env="SERVICE_NAME")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    workers: int = Field(4, env="WORKERS")
    
    # Storage Configuration
    storage_backend: Literal["file", "s3"] = Field("file", env="STORAGE_BACKEND")
    storage_path: str = Field("/tmp/mcp-images", env="STORAGE_PATH")
    
    # S3 Configuration
    s3_bucket: Optional[str] = Field(None, env="S3_BUCKET")
    s3_prefix: str = Field("mcp-images/", env="S3_PREFIX")
    s3_endpoint_url: Optional[str] = Field(None, env="S3_ENDPOINT_URL")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    
    # KServe Configuration
    kserve_endpoint: str = Field(..., env="KSERVE_ENDPOINT")
    kserve_model_name: str = Field("stable-diffusion", env="KSERVE_MODEL_NAME")
    kserve_timeout: float = Field(60.0, env="KSERVE_TIMEOUT")
    kserve_max_retries: int = Field(3, env="KSERVE_MAX_RETRIES")
    
    # Image Management
    image_cleanup_interval: int = Field(300, env="IMAGE_CLEANUP_INTERVAL")
    image_ttl: int = Field(3600, env="IMAGE_TTL")
    max_image_size: int = Field(10485760, env="MAX_IMAGE_SIZE")  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## HTTP API Interface

### File Server Endpoints
```python
from fastapi import APIRouter, Response, HTTPException
from typing import Optional

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/{image_id}")
async def get_image(
    image_id: str,
    storage: AbstractStorage = Depends(get_storage)
) -> Response:
    """
    Retrieve a generated image.
    
    Args:
        image_id: Unique image identifier
        
    Returns:
        Image file response
        
    Raises:
        404: Image not found
    """

@router.get("/")
async def list_images(
    prefix: Optional[str] = None,
    limit: int = 100,
    storage: AbstractStorage = Depends(get_storage)
) -> List[Dict[str, Any]]:
    """
    List generated images.
    
    Args:
        prefix: Optional prefix filter
        limit: Maximum results to return
        
    Returns:
        List of image metadata
    """
```

## Error Handling Interface

### Custom Exceptions
```python
class MCPImageError(Exception):
    """Base exception for MCP image server."""
    pass

class StorageError(MCPImageError):
    """Storage operation failed."""
    pass

class KServeError(MCPImageError):
    """KServe request failed."""
    pass

class ValidationError(MCPImageError):
    """Input validation failed."""
    pass

class ConfigurationError(MCPImageError):
    """Configuration is invalid."""
    pass
```

## Background Tasks Interface

### CleanupTask
```python
import asyncio
from datetime import datetime, timedelta

class CleanupTask:
    """Background task for cleaning up expired images."""
    
    def __init__(
        self,
        storage: AbstractStorage,
        interval: int,
        ttl: int
    ):
        """
        Initialize cleanup task.
        
        Args:
            storage: Storage backend to clean
            interval: Cleanup interval in seconds
            ttl: Image time-to-live in seconds
        """
        self.storage = storage
        self.interval = interval
        self.ttl = ttl
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the cleanup task."""
    
    async def stop(self) -> None:
        """Stop the cleanup task."""
    
    async def run_cleanup(self) -> None:
        """Run a single cleanup cycle."""
```

## Testing Interface

### Mock Implementations
```python
class MockStorage(AbstractStorage):
    """In-memory storage for testing."""
    
    def __init__(self):
        self.images: Dict[str, bytes] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

class MockKServeClient(KServeClient):
    """Mock KServe client for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_image_calls = []
        self.mock_response = None
        self.should_fail = False
```

## Logging Interface

### Structured Logging
```python
import structlog

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name).bind(
        service="mcp-image-server",
        component=name
    )

# Usage example
logger = get_logger("storage")
logger.info("image_saved", image_id=image_id, size=len(image_data))
```
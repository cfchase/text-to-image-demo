# Coding Standards and Patterns

## Overview

This document defines the coding standards and patterns for the MCP Image Generation Server project. All workers should follow these guidelines to ensure consistency and maintainability.

## Python Style Guide

### General Rules
- Follow PEP 8 with line length of 88 characters (Black default)
- Use Python 3.9+ features where appropriate
- Prefer type hints for all function signatures
- Use docstrings for all public functions and classes

### Code Formatting
```bash
# Use these tools for automatic formatting
black src/ tests/
isort src/ tests/
```

### Import Organization
```python
# Standard library imports
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local imports
from mcp_server.storage.base import AbstractStorage
from mcp_server.utils.logging import get_logger
```

## Async/Await Patterns

### Always Use Async
All I/O operations should be async:
```python
# Good
async def read_file(path: Path) -> bytes:
    async with aiofiles.open(path, 'rb') as f:
        return await f.read()

# Bad
def read_file(path: Path) -> bytes:
    with open(path, 'rb') as f:
        return f.read()
```

### Concurrent Operations
Use asyncio.gather for parallel operations:
```python
# Good
results = await asyncio.gather(
    storage.save_image(data1, id1, meta1),
    storage.save_image(data2, id2, meta2),
    return_exceptions=True
)

# Handle exceptions
for result in results:
    if isinstance(result, Exception):
        logger.error("Operation failed", error=str(result))
```

## Error Handling

### Custom Exceptions
Always use custom exceptions:
```python
# Good
class StorageError(MCPImageError):
    """Storage operation failed."""
    pass

try:
    await storage.save_image(data, image_id, metadata)
except StorageError as e:
    logger.error("Failed to save image", error=str(e))
    raise

# Bad
try:
    await storage.save_image(data, image_id, metadata)
except Exception as e:  # Too broad
    print(f"Error: {e}")  # Don't use print
```

### Error Context
Provide meaningful error messages:
```python
# Good
if not image_data:
    raise ValidationError(
        f"Image data is empty for image_id={image_id}"
    )

# Bad
if not image_data:
    raise ValueError("Invalid data")
```

## Logging

### Structured Logging
Always use structured logging:
```python
# Good
logger.info(
    "image_generated",
    image_id=image_id,
    prompt=prompt,
    duration_ms=int(duration * 1000)
)

# Bad
logger.info(f"Generated image {image_id} in {duration}s")
```

### Log Levels
- DEBUG: Detailed diagnostic information
- INFO: General informational messages
- WARNING: Warning messages for recoverable issues
- ERROR: Error messages for failures
- CRITICAL: Critical failures requiring immediate attention

## Testing

### Test Structure
```python
# tests/unit/test_storage.py
import pytest
from unittest.mock import AsyncMock

from mcp_server.storage.file import FileStorage

class TestFileStorage:
    """Test file storage implementation."""
    
    @pytest.fixture
    async def storage(self, tmp_path):
        """Create storage instance for testing."""
        return FileStorage(
            base_path=str(tmp_path),
            base_url="http://localhost/images"
        )
    
    async def test_save_image_success(self, storage):
        """Test successful image save."""
        # Arrange
        image_data = b"fake image data"
        image_id = "test-123"
        metadata = {"prompt": "test prompt"}
        
        # Act
        path = await storage.save_image(image_data, image_id, metadata)
        
        # Assert
        assert path.endswith(f"{image_id}.png")
        assert (Path(storage.base_path) / f"{image_id}.png").exists()
```

### Mock Usage
```python
# Good - Use AsyncMock for async functions
mock_client = AsyncMock()
mock_client.generate_image.return_value = {"image": "data"}

# Bad - Don't use regular Mock for async
mock_client = Mock()  # Will fail with async calls
```

## Configuration

### Environment Variables
All configuration through environment:
```python
# Good
class Settings(BaseSettings):
    storage_backend: str = Field("file", env="STORAGE_BACKEND")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Bad
STORAGE_BACKEND = "file"  # Hardcoded
```

### Validation
Always validate configuration:
```python
# Good
@validator("s3_bucket")
def validate_s3_bucket(cls, v, values):
    if values.get("storage_backend") == "s3" and not v:
        raise ValueError("S3 bucket required for S3 backend")
    return v
```

## Documentation

### Docstring Format
Use Google-style docstrings:
```python
async def generate_image(
    self,
    prompt: str,
    width: int = 512,
    height: int = 512
) -> Dict[str, Any]:
    """
    Generate an image from a text prompt.
    
    Args:
        prompt: Text description of the image
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Dictionary containing:
            - image_id: Unique identifier
            - url: URL to access the image
            
    Raises:
        ValidationError: If parameters are invalid
        KServeError: If generation fails
    """
```

### Type Hints
Always use type hints:
```python
# Good
from typing import Dict, List, Optional, Union

async def process_images(
    image_ids: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Union[str, int]]:
    ...

# Bad
async def process_images(image_ids, options=None):
    ...
```

## Security

### Input Validation
Always validate user input:
```python
# Good
class GenerateImageParams(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    width: int = Field(512, ge=64, le=2048)
    height: int = Field(512, ge=64, le=2048)

# Bad
def generate_image(prompt, width, height):
    # No validation!
    pass
```

### Secrets Management
Never hardcode secrets:
```python
# Good
aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")

# Bad
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"  # NEVER DO THIS
```

## Performance

### Connection Pooling
Reuse connections:
```python
# Good
class KServeClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=10)
        )
    
    async def close(self):
        await self.client.aclose()

# Bad
async def make_request():
    async with httpx.AsyncClient() as client:  # Creates new client each time
        return await client.get(url)
```

### Resource Cleanup
Always clean up resources:
```python
# Good
class Server:
    async def start(self):
        self.cleanup_task = asyncio.create_task(self.run_cleanup())
    
    async def stop(self):
        self.cleanup_task.cancel()
        try:
            await self.cleanup_task
        except asyncio.CancelledError:
            pass
```

## Code Review Checklist

Before submitting code:
- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] No linting errors (`flake8`)
- [ ] Type hints added (`mypy`)
- [ ] Documentation updated
- [ ] Error handling implemented
- [ ] Logging added for key operations
- [ ] Security considerations addressed
- [ ] Performance impact considered

## Common Patterns

### Factory Pattern
```python
def create_storage(settings: Settings) -> AbstractStorage:
    """Create storage backend based on settings."""
    if settings.storage_backend == "file":
        return FileStorage(
            base_path=settings.storage_path,
            base_url=f"http://{settings.host}:{settings.port}/images"
        )
    elif settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            endpoint_url=settings.s3_endpoint_url
        )
    else:
        raise ConfigurationError(f"Unknown storage backend: {settings.storage_backend}")
```

### Dependency Injection
```python
# Good - Use FastAPI's dependency injection
async def get_storage() -> AbstractStorage:
    return current_app.storage

@router.post("/generate")
async def generate_image(
    params: GenerateImageParams,
    storage: AbstractStorage = Depends(get_storage)
):
    ...
```

### Context Managers
```python
# Good - Use async context managers
class TempImageFile:
    async def __aenter__(self):
        self.path = Path(f"/tmp/{uuid.uuid4()}.png")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.path.exists():
            self.path.unlink()
```

## Conclusion

Following these standards ensures:
- Consistent, readable code
- Easier maintenance and debugging
- Better collaboration between workers
- Higher quality deliverables

All workers should refer to this document and the interface specifications when implementing their components.
"""API module for MCP image generation server."""

from .app import create_app, get_kserve_client, get_mcp_server, get_settings, get_storage
from .background import BackgroundTaskManager, CleanupTask, HealthCheckTask
from .mcp_server import (
    GenerateImageParams,
    GenerateImageResponse,
    ImageGenerationError,
    MCPImageError,
    MCPImageServer,
    StorageError,
    ValidationError,
    create_mcp_server,
)
from .routes import router as images_router

__all__ = [
    # FastAPI app
    "create_app",
    # Dependency functions
    "get_settings",
    "get_kserve_client", 
    "get_storage",
    "get_mcp_server",
    # MCP server
    "MCPImageServer",
    "create_mcp_server",
    "GenerateImageParams",
    "GenerateImageResponse",
    # Exceptions
    "MCPImageError",
    "ValidationError",
    "ImageGenerationError",
    "StorageError",
    # Background tasks
    "CleanupTask",
    "HealthCheckTask",
    "BackgroundTaskManager",
    # Routers
    "images_router",
]
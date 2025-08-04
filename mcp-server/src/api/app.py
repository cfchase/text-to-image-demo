"""FastAPI application setup for MCP image generation server."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.background import CleanupTask
from api.mcp_server import MCPImageServer, create_mcp_server
from api.routes import router as images_router
from config.settings import Settings
from kserve.client import KServeClient
from storage import create_storage
from utils.logging import RequestLoggingMiddleware, configure_logging

# Get logger
logger = structlog.get_logger(__name__)

# Global application state
app_state = {
    "settings": None,
    "kserve_client": None,
    "storage": None,
    "mcp_server": None,
    "cleanup_task": None,
}


async def startup() -> None:
    """Application startup handler."""
    logger.info("Starting MCP image generation server")
    
    try:
        # Load settings
        settings = Settings()
        app_state["settings"] = settings
        
        # Configure logging
        configure_logging(
            level=settings.log_level,
            service_name=settings.service_name,
        )
        
        logger.info(
            "Settings loaded",
            service_name=settings.service_name,
            log_level=settings.log_level,
            storage_backend=settings.storage_backend,
            kserve_endpoint=settings.kserve_endpoint,
        )
        
        # Create KServe client
        kserve_client = KServeClient(
            endpoint=settings.kserve_endpoint,
            model_name=settings.kserve_model_name,
            timeout=settings.kserve_timeout,
            max_retries=settings.kserve_max_retries,
        )
        app_state["kserve_client"] = kserve_client
        
        logger.info(
            "KServe client created",
            endpoint=settings.kserve_endpoint,
            model_name=settings.kserve_model_name,
            timeout=settings.kserve_timeout,
        )
        
        # Create storage backend
        if settings.storage_backend == "file":
            storage = create_storage(
                "file",
                base_path=settings.storage_path,
                base_url=settings.get_storage_url(),
            )
        elif settings.storage_backend == "s3":
            storage = create_storage(
                "s3",
                bucket=settings.s3_bucket,
                prefix=settings.s3_prefix,
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.aws_access_key_id,
                secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        else:
            raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
        
        app_state["storage"] = storage
        
        logger.info(
            "Storage backend created",
            backend=settings.storage_backend,
            path=settings.storage_path if settings.storage_backend == "file" else settings.s3_bucket,
        )
        
        # Create MCP server
        mcp_server = create_mcp_server(
            settings=settings,
            kserve_client=kserve_client,
            storage=storage,
        )
        app_state["mcp_server"] = mcp_server
        
        logger.info("MCP server created")
        
        # Start cleanup task
        cleanup_task = CleanupTask(
            storage=storage,
            interval=settings.image_cleanup_interval,
            ttl=settings.image_ttl,
        )
        await cleanup_task.start()
        app_state["cleanup_task"] = cleanup_task
        
        logger.info(
            "Cleanup task started",
            interval=settings.image_cleanup_interval,
            ttl=settings.image_ttl,
        )
        
        # Verify health
        health_status = await mcp_server.health_check()
        if health_status["service"] != "healthy":
            logger.warning(
                "Service started but not fully healthy",
                health_status=health_status,
            )
        else:
            logger.info("Service started and healthy")
        
        logger.info("MCP image generation server startup complete")
        
    except Exception as e:
        logger.error(
            "Failed to start MCP image generation server",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def shutdown() -> None:
    """Application shutdown handler."""
    logger.info("Shutting down MCP image generation server")
    
    # Stop cleanup task
    if app_state.get("cleanup_task"):
        try:
            await app_state["cleanup_task"].stop()
            logger.info("Cleanup task stopped")
        except Exception as e:
            logger.warning("Error stopping cleanup task", error=str(e))
    
    # Close MCP server
    if app_state.get("mcp_server"):
        try:
            await app_state["mcp_server"].close()
            logger.info("MCP server closed")
        except Exception as e:
            logger.warning("Error closing MCP server", error=str(e))
    
    # Close KServe client
    if app_state.get("kserve_client"):
        try:
            await app_state["kserve_client"].close()
            logger.info("KServe client closed")
        except Exception as e:
            logger.warning("Error closing KServe client", error=str(e))
    
    logger.info("MCP image generation server shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await startup()
    
    yield
    
    # Shutdown
    await shutdown()


def get_settings() -> Settings:
    """Get application settings."""
    if not app_state.get("settings"):
        raise RuntimeError("Application not initialized")
    return app_state["settings"]


def get_kserve_client() -> KServeClient:
    """Get KServe client."""
    if not app_state.get("kserve_client"):
        raise RuntimeError("Application not initialized")
    return app_state["kserve_client"]


def get_storage():
    """Get storage backend."""
    if not app_state.get("storage"):
        raise RuntimeError("Application not initialized")
    return app_state["storage"]


def get_mcp_server() -> MCPImageServer:
    """Get MCP server."""
    if not app_state.get("mcp_server"):
        raise RuntimeError("Application not initialized")
    return app_state["mcp_server"]


async def custom_exception_handler(request, exc):
    """Custom exception handler for better error responses."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "type": "server_error",
        },
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="MCP Image Generation Server",
        description="MCP server for generating images using KServe diffusers runtime",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add custom exception handler
    app.add_exception_handler(Exception, custom_exception_handler)
    
    # Include routers
    app.include_router(images_router, prefix="/images", tags=["images"])
    
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        mcp_server = get_mcp_server()
        return await mcp_server.health_check()
    
    @app.get("/")
    async def root() -> Dict[str, str]:
        """Root endpoint."""
        return {
            "message": "MCP Image Generation Server",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }
    
    @app.get("/metrics")
    async def metrics() -> Dict[str, Any]:
        """Basic metrics endpoint."""
        settings = get_settings()
        
        # Get basic runtime metrics
        metrics = {
            "service": {
                "name": settings.service_name,
                "version": "0.1.0",
                "uptime_seconds": 0,  # Would need to track startup time
            },
            "storage": {
                "backend": settings.storage_backend,
            },
            "kserve": {
                "endpoint": settings.kserve_endpoint,
                "model_name": settings.kserve_model_name,
            },
        }
        
        # Add storage metrics if available
        try:
            storage = get_storage()
            images = await storage.list_images()
            metrics["storage"]["total_images"] = len(images)
        except Exception:
            metrics["storage"]["total_images"] = "unknown"
        
        return metrics
    
    @app.post("/mcp/v1/tools/generate_image")
    async def mcp_generate_image(
        params: dict,
        mcp_server: MCPImageServer = Depends(get_mcp_server),
    ) -> Dict[str, Any]:
        """MCP tool endpoint for image generation."""
        from api.mcp_server import GenerateImageParams
        
        try:
            # Parse and validate parameters
            validated_params = GenerateImageParams(**params)
            
            # Generate image
            result = await mcp_server.generate_image(validated_params)
            
            return {
                "result": result.dict(),
                "error": None,
            }
            
        except Exception as e:
            logger.error(
                "MCP tool execution failed",
                tool="generate_image",
                error=str(e),
                error_type=type(e).__name__,
            )
            
            return {
                "result": None,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            }
    
    return app


# Create the application instance
app = create_app()
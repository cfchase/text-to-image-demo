"""Application entry point for MCP image generation server."""

import os
import signal
import sys
from typing import Optional

import structlog
import uvicorn
from fastapi import FastAPI

from api.app import create_app
from config.settings import Settings
from utils.logging import configure_logging

# Get logger
logger = structlog.get_logger(__name__)

# Global app instance
app: Optional[FastAPI] = None


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    
    # The FastAPI lifespan will handle cleanup
    sys.exit(0)


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def create_application() -> FastAPI:
    """Create the FastAPI application."""
    global app
    
    if app is None:
        app = create_app()
    
    return app


def main() -> None:
    """Main entry point for the application."""
    try:
        # Load settings early to configure logging
        settings = Settings()
        
        # Configure logging
        configure_logging(
            log_level=settings.log_level,
            service_name=settings.service_name,
        )
        
        logger.info(
            "Starting MCP image generation server",
            service_name=settings.service_name,
            version="0.1.0",
            host=settings.host,
            port=settings.port,
            workers=settings.workers,
            log_level=settings.log_level,
        )
        
        # Set up signal handlers
        setup_signal_handlers()
        
        # Create application
        app = create_application()
        
        # Configure uvicorn based on environment
        is_development = os.getenv("ENVIRONMENT", "production").lower() in ("dev", "development")
        
        uvicorn_config = {
            "app": "main:app" if is_development else app,
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.log_level.lower(),
            "access_log": True,
            "server_header": False,
            "date_header": False,
        }
        
        if is_development:
            # Development settings
            uvicorn_config.update({
                "reload": True,
                "reload_dirs": ["src"],
                "workers": 1,  # Use 1 worker for development with reload
            })
            logger.info("Running in development mode with auto-reload")
        else:
            # Production settings
            uvicorn_config.update({
                "workers": settings.workers,
                "loop": "uvloop",  # Use uvloop for better performance
                "http": "httptools",  # Use httptools for better performance
            })
            logger.info(f"Running in production mode with {settings.workers} workers")
        
        # Log configuration (excluding sensitive values)
        config_dict = settings.to_dict()
        logger.info(
            "Server configuration loaded",
            storage_backend=config_dict["storage_backend"],
            kserve_endpoint=config_dict["kserve_endpoint"],
            image_ttl=config_dict["image_ttl"],
            cleanup_interval=config_dict["image_cleanup_interval"],
        )
        
        # Start the server
        uvicorn.run(**uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(
            "Failed to start server",
            error=str(e),
            error_type=type(e).__name__,
        )
        sys.exit(1)


def run_development() -> None:
    """Run the server in development mode."""
    os.environ["ENVIRONMENT"] = "development"
    main()


def run_production() -> None:
    """Run the server in production mode."""
    os.environ["ENVIRONMENT"] = "production"
    main()


def health_check() -> None:
    """Perform a health check against the running server."""
    import httpx
    import asyncio
    
    async def check_health():
        settings = Settings()
        url = f"http://{settings.host}:{settings.port}/health"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    print(f"Service Status: {health_data.get('service', 'unknown')}")
                    print(f"KServe Status: {health_data.get('kserve', 'unknown')}")
                    print(f"Storage Status: {health_data.get('storage', 'unknown')}")
                    print(f"Timestamp: {health_data.get('timestamp', 'unknown')}")
                    
                    if health_data.get('service') == 'healthy':
                        print("✅ Server is healthy")
                        sys.exit(0)
                    else:
                        print("⚠️ Server is not fully healthy")
                        sys.exit(1)
                else:
                    print(f"❌ Health check failed: HTTP {response.status_code}")
                    sys.exit(1)
                    
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            sys.exit(1)
    
    asyncio.run(check_health())


def cleanup_images() -> None:
    """Manually trigger image cleanup."""
    import httpx
    import asyncio
    
    async def trigger_cleanup():
        settings = Settings()
        url = f"http://{settings.host}:{settings.port}/images/cleanup"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, timeout=30.0)
                
                if response.status_code == 200:
                    cleanup_data = response.json()
                    
                    print(f"Cleanup completed successfully")
                    print(f"Images deleted: {cleanup_data.get('deleted_count', 0)}")
                    print(f"TTL: {cleanup_data.get('ttl_seconds', 0)} seconds")
                    
                    sys.exit(0)
                else:
                    print(f"❌ Cleanup failed: HTTP {response.status_code}")
                    if response.headers.get("content-type", "").startswith("application/json"):
                        error_data = response.json()
                        print(f"Error: {error_data.get('detail', {}).get('message', 'Unknown error')}")
                    sys.exit(1)
                    
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            sys.exit(1)
    
    asyncio.run(trigger_cleanup())


if __name__ == "__main__":
    # Support command line arguments for different modes
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "dev":
            run_development()
        elif command == "prod":
            run_production()
        elif command == "health":
            health_check()
        elif command == "cleanup":
            cleanup_images()
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  dev      - Run in development mode")
            print("  prod     - Run in production mode")
            print("  health   - Check server health")
            print("  cleanup  - Trigger manual cleanup")
            sys.exit(1)
    else:
        # Default to production mode
        main()


# Export the app for ASGI servers
app = create_application()
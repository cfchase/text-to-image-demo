"""Background tasks for image cleanup and maintenance."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import structlog

from storage.base import AbstractStorage

# Get logger
logger = structlog.get_logger(__name__)


class CleanupTask:
    """Background task for cleaning up expired images."""
    
    def __init__(
        self,
        storage: AbstractStorage,
        interval: int,
        ttl: int,
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
        
        logger.info(
            "Cleanup task initialized",
            interval=interval,
            ttl=ttl,
        )
    
    async def start(self) -> None:
        """Start the cleanup task."""
        if self.running:
            logger.warning("Cleanup task already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(
            "Cleanup task started",
            interval=self.interval,
            ttl=self.ttl,
        )
    
    async def stop(self) -> None:
        """Stop the cleanup task."""
        if not self.running:
            logger.info("Cleanup task not running")
            return
        
        self.running = False
        
        if self.task:
            logger.info("Stopping cleanup task")
            self.task.cancel()
            
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
            except Exception as e:
                logger.error(
                    "Error during cleanup task shutdown",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            
            self.task = None
        
        logger.info("Cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        logger.info("Cleanup loop started")
        
        try:
            while self.running:
                try:
                    # Run cleanup
                    await self.run_cleanup()
                    
                    # Wait for next interval
                    await asyncio.sleep(self.interval)
                    
                except asyncio.CancelledError:
                    logger.info("Cleanup loop cancelled")
                    break
                    
                except Exception as e:
                    logger.error(
                        "Error in cleanup loop",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    
                    # Wait before retrying on error
                    await asyncio.sleep(min(self.interval, 60))
        
        finally:
            logger.info("Cleanup loop finished")
    
    async def run_cleanup(self) -> int:
        """
        Run a single cleanup cycle.
        
        Returns:
            Number of images deleted
        """
        start_time = datetime.now(timezone.utc)
        
        logger.debug(
            "Starting cleanup cycle",
            ttl=self.ttl,
        )
        
        try:
            # Run cleanup on storage backend
            deleted_count = await self.storage.cleanup_expired_images(self.ttl)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            if deleted_count > 0:
                logger.info(
                    "Cleanup cycle completed",
                    deleted_count=deleted_count,
                    duration_seconds=duration,
                    ttl=self.ttl,
                )
            else:
                logger.debug(
                    "Cleanup cycle completed - no images to delete",
                    duration_seconds=duration,
                    ttl=self.ttl,
                )
            
            return deleted_count
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.error(
                "Cleanup cycle failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                ttl=self.ttl,
            )
            
            # Re-raise so the loop can handle it
            raise
    
    def is_running(self) -> bool:
        """Check if cleanup task is running."""
        return self.running and self.task is not None and not self.task.done()
    
    def get_status(self) -> dict:
        """Get cleanup task status."""
        return {
            "running": self.running,
            "interval": self.interval,
            "ttl": self.ttl,
            "task_active": self.task is not None and not self.task.done(),
        }


class HealthCheckTask:
    """Background task for periodic health checks."""
    
    def __init__(
        self,
        health_check_func,
        interval: int = 60,
        failure_threshold: int = 3,
    ):
        """
        Initialize health check task.
        
        Args:
            health_check_func: Async function to call for health checks
            interval: Health check interval in seconds
            failure_threshold: Number of failures before marking unhealthy
        """
        self.health_check_func = health_check_func
        self.interval = interval
        self.failure_threshold = failure_threshold
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.consecutive_failures = 0
        self.last_check_time = None
        self.last_status = None
        
        logger.info(
            "Health check task initialized",
            interval=interval,
            failure_threshold=failure_threshold,
        )
    
    async def start(self) -> None:
        """Start the health check task."""
        if self.running:
            logger.warning("Health check task already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Health check task started")
    
    async def stop(self) -> None:
        """Stop the health check task."""
        if not self.running:
            logger.info("Health check task not running")
            return
        
        self.running = False
        
        if self.task:
            logger.info("Stopping health check task")
            self.task.cancel()
            
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
            except Exception as e:
                logger.error(
                    "Error during health check task shutdown",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            
            self.task = None
        
        logger.info("Health check task stopped")
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        logger.info("Health check loop started")
        
        try:
            while self.running:
                try:
                    # Run health check
                    await self._run_health_check() 
                    
                    # Wait for next interval
                    await asyncio.sleep(self.interval)
                    
                except asyncio.CancelledError:
                    logger.info("Health check loop cancelled")
                    break
                    
                except Exception as e:
                    logger.error(
                        "Error in health check loop",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    
                    # Wait before retrying on error
                    await asyncio.sleep(min(self.interval, 30))
        
        finally:
            logger.info("Health check loop finished")
    
    async def _run_health_check(self) -> None:
        """Run a single health check."""
        self.last_check_time = datetime.now(timezone.utc)
        
        try:
            # Run the health check function
            status = await self.health_check_func()
            
            # Check if healthy
            is_healthy = status.get("service") == "healthy"
            
            if is_healthy:
                if self.consecutive_failures > 0:
                    logger.info(
                        "Service recovered",
                        consecutive_failures=self.consecutive_failures,
                    )
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                
                if self.consecutive_failures >= self.failure_threshold:
                    logger.error(
                        "Service unhealthy",
                        consecutive_failures=self.consecutive_failures,
                        threshold=self.failure_threshold,
                        status=status,
                    )
                else:
                    logger.warning(
                        "Health check failed",
                        consecutive_failures=self.consecutive_failures,
                        threshold=self.failure_threshold,
                        status=status,
                    )
            
            self.last_status = status
            
        except Exception as e:
            self.consecutive_failures += 1
            
            logger.error(
                "Health check execution failed",
                error=str(e),
                error_type=type(e).__name__,
                consecutive_failures=self.consecutive_failures,
            )
            
            self.last_status = {
                "service": "unhealthy",
                "error": str(e),
                "timestamp": self.last_check_time.isoformat(),
            }
    
    def get_status(self) -> dict:
        """Get health check task status."""
        return {
            "running": self.running,
            "interval": self.interval,
            "failure_threshold": self.failure_threshold,
            "consecutive_failures": self.consecutive_failures,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_status": self.last_status,
            "task_active": self.task is not None and not self.task.done(),
        }


class BackgroundTaskManager:
    """Manager for all background tasks."""
    
    def __init__(self):
        """Initialize background task manager."""
        self.tasks = {}
        self.running = False
        
        logger.info("Background task manager initialized")
    
    def add_task(self, name: str, task) -> None:
        """Add a background task."""
        if name in self.tasks:
            logger.warning(f"Task '{name}' already exists, replacing")
        
        self.tasks[name] = task
        logger.info(f"Added background task '{name}'")
    
    async def start_all(self) -> None:
        """Start all background tasks."""
        if self.running:
            logger.warning("Background tasks already running")
            return
        
        self.running = True
        
        logger.info(f"Starting {len(self.tasks)} background tasks")
        
        for name, task in self.tasks.items():
            try:
                await task.start()
                logger.info(f"Started background task '{name}'")
            except Exception as e:
                logger.error(
                    f"Failed to start background task '{name}'",
                    error=str(e),
                    error_type=type(e).__name__,
                )
        
        logger.info("All background tasks started")
    
    async def stop_all(self) -> None:
        """Stop all background tasks."""
        if not self.running:
            logger.info("Background tasks not running")
            return
        
        self.running = False
        
        logger.info(f"Stopping {len(self.tasks)} background tasks")
        
        # Stop all tasks concurrently
        stop_tasks = []
        for name, task in self.tasks.items():
            stop_tasks.append(self._stop_task(name, task))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        logger.info("All background tasks stopped")
    
    async def _stop_task(self, name: str, task) -> None:
        """Stop a single background task."""
        try:
            await task.stop()
            logger.info(f"Stopped background task '{name}'")
        except Exception as e:
            logger.error(
                f"Failed to stop background task '{name}'",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    def get_status(self) -> dict:
        """Get status of all background tasks."""
        status = {
            "manager_running": self.running,
            "task_count": len(self.tasks),
            "tasks": {},
        }
        
        for name, task in self.tasks.items():
            try:
                if hasattr(task, "get_status"):
                    status["tasks"][name] = task.get_status()
                else:
                    status["tasks"][name] = {
                        "running": hasattr(task, "running") and task.running,
                        "type": type(task).__name__,
                    }
            except Exception as e:
                status["tasks"][name] = {
                    "error": str(e),
                    "type": type(task).__name__,
                }
        
        return status
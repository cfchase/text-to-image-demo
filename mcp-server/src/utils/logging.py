"""Structured logging utilities with structlog."""

import logging
import sys
from typing import Any, Dict, Optional

try:
    import structlog
    
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def configure_logging(
    level: str = "INFO",
    service_name: str = "mcp-image-server",
    development: bool = False,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log context
        development: Whether to use development-friendly formatting
    """
    log_level = getattr(logging, level.upper())
    
    if STRUCTLOG_AVAILABLE:
        # Configure structlog with fallback to standard logging
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        if development:
            # Pretty printing for development
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            # JSON output for production
            processors.append(structlog.processors.JSONRenderer())
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(log_level)
        
        # Add service context to all logs
        structlog.contextvars.bind_contextvars(service=service_name)
    else:
        # Fallback to standard logging if structlog is not available
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )


def get_logger(name: str, **context: Any) -> Any:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically module name)
        **context: Additional context to bind to all log messages
        
    Returns:
        Logger instance (structlog BoundLogger or standard Logger)
    """
    if STRUCTLOG_AVAILABLE:
        logger = structlog.get_logger(name)
        if context:
            logger = logger.bind(**context)
        return logger
    else:
        # Fallback to standard logging
        return logging.getLogger(name)


def bind_context(**context: Any) -> None:
    """
    Bind context variables that will be included in all subsequent log messages.
    
    Args:
        **context: Key-value pairs to bind to logging context
    """
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.bind_contextvars(**context)


def clear_context() -> None:
    """Clear all bound context variables."""
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.clear_contextvars()


def with_request_id(request_id: str) -> Any:
    """
    Create a logger context manager that adds request ID to all log messages.
    
    Args:
        request_id: Unique request identifier
        
    Returns:
        Context manager that binds request_id to logging context
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.contextvars.bound_contextvars(request_id=request_id)
    else:
        # For standard logging, we'll use a simple context manager
        class LogContextManager:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return LogContextManager()


class RequestLoggingMiddleware:
    """ASGI middleware to add request ID correlation to logs."""
    
    def __init__(self, app, generate_request_id=None):
        """
        Initialize request logging middleware.
        
        Args:
            app: The ASGI application to wrap
            generate_request_id: Function to generate request IDs (optional)
        """
        self.app = app
        self.generate_request_id = generate_request_id or self._default_request_id
    
    def _default_request_id(self) -> str:
        """Generate a default request ID."""
        from .ids import generate_id
        return generate_id("req")
    
    async def __call__(self, scope, receive, send):
        """Process request with logging context."""
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request_id = self.generate_request_id()
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        
        with with_request_id(request_id):
            logger = get_logger("request")
            logger.info(
                "request_started",
                method=method,
                path=path,
                request_id=request_id,
            )
            
            # Track response status
            status_code = None
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 200)
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
                logger.info(
                    "request_completed",
                    status_code=status_code,
                    request_id=request_id,
                )
            except Exception as e:
                logger.error(
                    "request_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    request_id=request_id,
                )
                raise


def log_function_call(logger_name: Optional[str] = None):
    """
    Decorator to log function calls with parameters and duration.
    
    Args:
        logger_name: Name for the logger (defaults to function module)
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()
            
            logger.debug(
                "function_called",
                function=func.__name__,
                args=str(args)[:100],  # Truncate for readability
                kwargs={k: str(v)[:50] for k, v in kwargs.items()}
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(
                    "function_completed",
                    function=func.__name__,
                    duration_ms=int(duration * 1000)
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=int(duration * 1000)
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()
            
            logger.debug(
                "function_called",
                function=func.__name__,
                args=str(args)[:100],
                kwargs={k: str(v)[:50] for k, v in kwargs.items()}
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(
                    "function_completed",
                    function=func.__name__,
                    duration_ms=int(duration * 1000)
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=int(duration * 1000)
                )
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
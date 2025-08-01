"""Tests for logging utilities."""

import logging
import sys
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from mcp_server.utils.logging import (
    STRUCTLOG_AVAILABLE,
    RequestLoggingMiddleware,
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    log_function_call,
    with_request_id,
)


class TestLogging:
    """Test logging configuration and utilities."""

    def setup_method(self):
        """Set up test environment."""
        # Capture log output
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        
        # Reset logging configuration
        logging.getLogger().handlers.clear()
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def teardown_method(self):
        """Clean up test environment."""
        logging.getLogger().handlers.clear()
        if STRUCTLOG_AVAILABLE:
            clear_context()

    def test_configure_logging_info_level(self):
        """Test logging configuration with INFO level."""
        configure_logging(level="INFO", service_name="test-service", development=True)
        
        logger = get_logger("test")
        logger.info("test message")
        
        output = self.log_capture.getvalue()
        assert "test message" in output

    def test_configure_logging_debug_level(self):
        """Test logging configuration with DEBUG level."""
        configure_logging(level="DEBUG", service_name="test-service", development=True)
        
        logger = get_logger("test")
        logger.debug("debug message")
        
        output = self.log_capture.getvalue()
        assert "debug message" in output

    def test_configure_logging_production_mode(self):
        """Test logging configuration in production mode."""
        configure_logging(level="INFO", service_name="test-service", development=False)
        
        logger = get_logger("test")
        logger.info("production message", key="value")
        
        # In production mode, output should be structured (JSON-like)
        output = self.log_capture.getvalue()
        assert "production message" in output

    def test_get_logger_with_context(self):
        """Test getting logger with bound context."""
        configure_logging(development=True)
        
        logger = get_logger("test", component="storage", version="1.0")
        logger.info("contextual message")
        
        output = self.log_capture.getvalue()
        assert "contextual message" in output

    @pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="structlog not available")
    def test_bind_context(self):
        """Test binding context variables."""
        configure_logging(development=True)
        
        bind_context(user_id="123", session_id="abc")
        
        logger = get_logger("test")
        logger.info("message with context")
        
        output = self.log_capture.getvalue()
        assert "message with context" in output

    @pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="structlog not available")
    def test_clear_context(self):
        """Test clearing context variables."""
        configure_logging(development=True)
        
        bind_context(user_id="123")
        clear_context()
        
        logger = get_logger("test")
        logger.info("message after clear")
        
        output = self.log_capture.getvalue()
        assert "message after clear" in output

    @pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="structlog not available")
    def test_with_request_id_context_manager(self):
        """Test request ID context manager."""
        configure_logging(development=True)
        
        with with_request_id("req-123"):
            logger = get_logger("test")
            logger.info("request message")
        
        output = self.log_capture.getvalue()
        assert "request message" in output

    def test_with_request_id_fallback(self):
        """Test request ID context manager fallback."""
        # This should not raise an error even without structlog
        with with_request_id("req-123"):
            logger = get_logger("test")
            logger.info("fallback message")
        
        output = self.log_capture.getvalue()
        assert "fallback message" in output

    def test_log_function_call_decorator_sync(self):
        """Test function call logging decorator for sync functions."""
        configure_logging(level="DEBUG", development=True)
        
        @log_function_call("test.module")
        def test_function(arg1, arg2="default"):
            return f"{arg1}-{arg2}"
        
        result = test_function("hello", arg2="world")
        
        assert result == "hello-world"
        output = self.log_capture.getvalue()
        assert "function_called" in output
        assert "function_completed" in output
        assert "test_function" in output

    @pytest.mark.asyncio
    async def test_log_function_call_decorator_async(self):
        """Test function call logging decorator for async functions."""
        configure_logging(level="DEBUG", development=True)
        
        @log_function_call("test.module")
        async def async_test_function(arg1):
            return f"async-{arg1}"
        
        result = await async_test_function("hello")
        
        assert result == "async-hello"
        output = self.log_capture.getvalue()
        assert "function_called" in output
        assert "function_completed" in output
        assert "async_test_function" in output

    @pytest.mark.asyncio
    async def test_log_function_call_decorator_exception(self):
        """Test function call logging decorator with exceptions."""
        configure_logging(level="DEBUG", development=True)
        
        @log_function_call("test.module")
        async def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await failing_function()
        
        output = self.log_capture.getvalue()
        assert "function_called" in output
        assert "function_failed" in output
        assert "failing_function" in output
        assert "ValueError" in output

    def test_request_logging_middleware_init(self):
        """Test RequestLoggingMiddleware initialization."""
        middleware = RequestLoggingMiddleware()
        assert middleware.generate_request_id is not None
        
        # Test with custom request ID generator
        def custom_id_gen():
            return "custom-123"
        
        middleware = RequestLoggingMiddleware(generate_request_id=custom_id_gen)
        assert middleware.generate_request_id() == "custom-123"

    @pytest.mark.asyncio
    async def test_request_logging_middleware_success(self):
        """Test RequestLoggingMiddleware with successful request."""
        configure_logging(development=True)
        
        middleware = RequestLoggingMiddleware()
        
        # Mock request and response
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        async def mock_call_next(request):
            return mock_response
        
        response = await middleware(mock_request, mock_call_next)
        
        assert response == mock_response
        output = self.log_capture.getvalue()
        assert "request_started" in output
        assert "request_completed" in output
        assert "GET" in output
        assert "/test" in output

    @pytest.mark.asyncio
    async def test_request_logging_middleware_exception(self):
        """Test RequestLoggingMiddleware with exception."""
        configure_logging(development=True)
        
        middleware = RequestLoggingMiddleware()
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/error"
        
        async def mock_call_next(request):
            raise RuntimeError("Request failed")
        
        with pytest.raises(RuntimeError, match="Request failed"):
            await middleware(mock_request, mock_call_next)
        
        output = self.log_capture.getvalue()
        assert "request_started" in output
        assert "request_failed" in output
        assert "POST" in output
        assert "/error" in output
        assert "RuntimeError" in output

    def test_logger_fallback_without_structlog(self):
        """Test logger fallback when structlog is not available."""
        with patch('mcp_server.utils.logging.STRUCTLOG_AVAILABLE', False):
            configure_logging(development=True)
            
            logger = get_logger("test")
            logger.info("fallback message")
            
            output = self.log_capture.getvalue()
            assert "fallback message" in output

    def test_multiple_loggers(self):
        """Test multiple logger instances."""
        configure_logging(development=True)
        
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        logger1.info("message from module1")
        logger2.info("message from module2")
        
        output = self.log_capture.getvalue()
        assert "message from module1" in output
        assert "message from module2" in output

    def test_log_levels(self):
        """Test different log levels."""
        configure_logging(level="DEBUG", development=True)
        
        logger = get_logger("test")
        
        logger.debug("debug message")
        logger.info("info message") 
        logger.warning("warning message")
        logger.error("error message")
        
        output = self.log_capture.getvalue()
        assert "debug message" in output
        assert "info message" in output
        assert "warning message" in output
        assert "error message" in output

    def test_log_level_filtering(self):
        """Test log level filtering."""
        configure_logging(level="WARNING", development=True)
        
        logger = get_logger("test")
        
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        
        output = self.log_capture.getvalue()
        assert "debug message" not in output
        assert "info message" not in output
        assert "warning message" in output
        assert "error message" in output

    def test_logger_with_structured_data(self):
        """Test logger with structured key-value data."""
        configure_logging(development=True)
        
        logger = get_logger("test")
        logger.info(
            "structured message",
            user_id="123",
            action="login",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        output = self.log_capture.getvalue()
        assert "structured message" in output
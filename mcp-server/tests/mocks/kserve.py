"""Mock KServe client implementation for testing."""

import asyncio
import base64
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

from mcp_server.kserve.exceptions import (
    KServeConnectionError,
    KServeError,
    KServeInferenceError,
    KServeInvalidResponseError,
    KServeModelNotReadyError,
    KServeRateLimitError,
    KServeTimeoutError,
    KServeValidationError,
)
from mcp_server.kserve.models import (
    InternalImageRequest,
    InternalImageResponse,
    KServeModelMetadata,
    KServeModelStatus,
)


class MockKServeClient:
    """Mock KServe client for testing."""

    def __init__(
        self,
        endpoint: str,
        model_name: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize mock KServe client."""
        self.endpoint = endpoint
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Mock state
        self.call_log: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_exception = KServeError("Mock KServe failure")
        self.failure_methods: List[str] = []
        self.response_delay = 0.0
        self.is_healthy = True
        self.is_ready = True
        self.generation_time = 2.5
        
        # Mock responses
        self.mock_image_data = self._create_default_image_data()
        self.mock_metadata = self._create_default_metadata()
        self.mock_model_metadata = self._create_default_model_metadata()
        
        # Request tracking
        self.request_count = 0
        self.max_requests = None
        self.rate_limit_count = 0
        self.rate_limit_threshold = None

    def reset(self):
        """Reset mock client to initial state."""
        self.call_log.clear()
        self.should_fail = False
        self.failure_exception = KServeError("Mock KServe failure")
        self.failure_methods.clear()
        self.response_delay = 0.0
        self.is_healthy = True
        self.is_ready = True
        self.generation_time = 2.5
        self.request_count = 0
        self.rate_limit_count = 0

    def set_failure_mode(
        self,
        should_fail: bool = True,
        exception: Exception = None,
        methods: Optional[List[str]] = None,
    ):
        """Configure failure mode for testing error conditions."""
        self.should_fail = should_fail
        if exception:
            self.failure_exception = exception
        self.failure_methods = methods or []

    def set_response_delay(self, seconds: float):
        """Set artificial delay for responses."""
        self.response_delay = seconds

    def set_health_status(self, healthy: bool, ready: bool = None):
        """Set health and ready status."""
        self.is_healthy = healthy
        if ready is not None:
            self.is_ready = ready

    def set_mock_response(self, image_data: bytes = None, metadata: Dict[str, Any] = None):
        """Set custom mock response data."""
        if image_data:
            self.mock_image_data = image_data
        if metadata:
            self.mock_metadata = metadata

    def set_rate_limit(self, threshold: int):
        """Set rate limiting for testing."""
        self.rate_limit_threshold = threshold
        self.rate_limit_count = 0

    def set_request_limit(self, max_requests: int):
        """Set maximum number of requests before failing."""
        self.max_requests = max_requests

    def _create_default_image_data(self) -> bytes:
        """Create default mock image data."""
        # Simple PNG-like data
        return (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x02\x00"  # Width: 512
            b"\x00\x00\x02\x00"  # Height: 512
            b"\x08\x02\x00\x00\x00"
            b"mock_image_data_for_testing"
        )

    def _create_default_metadata(self) -> Dict[str, Any]:
        """Create default mock metadata."""
        return {
            "prompt": "mock generated prompt",
            "negative_prompt": "",
            "width": 512,
            "height": 512,
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
            "seed": 42,
            "model_name": self.model_name,
            "generation_time": self.generation_time,
        }

    def _create_default_model_metadata(self) -> KServeModelMetadata:
        """Create default model metadata."""
        return KServeModelMetadata(
            name=self.model_name,
            platform="pytorch",
            versions=["v1.0"],
            inputs=[
                {
                    "name": "prompt",
                    "datatype": "BYTES",
                    "shape": [-1],
                }
            ],
            outputs=[
                {
                    "name": "image",
                    "datatype": "BYTES", 
                    "shape": [-1],
                }
            ],
        )

    def _log_call(self, method: str, **kwargs):
        """Log method call for testing."""
        self.call_log.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args": kwargs,
        })

    async def _maybe_fail(self, method: str):
        """Check if method should fail based on configuration."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

        self.request_count += 1

        # Check request limit
        if self.max_requests and self.request_count > self.max_requests:
            raise KServeError("Request limit exceeded")

        # Check rate limit
        if self.rate_limit_threshold:
            self.rate_limit_count += 1
            if self.rate_limit_count > self.rate_limit_threshold:
                raise KServeRateLimitError("Rate limit exceeded")

        # Check if should fail
        if self.should_fail:
            if not self.failure_methods or method in self.failure_methods:
                raise self.failure_exception

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> InternalImageResponse:
        """Generate a mock image response."""
        self._log_call(
            "generate_image",
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        
        await self._maybe_fail("generate_image")

        # Create response metadata
        response_metadata = self.mock_metadata.copy()
        response_metadata.update({
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
        })

        return InternalImageResponse(
            image_data=self.mock_image_data,
            metadata=response_metadata,
            generation_time=self.generation_time,
        )

    async def health_check(self) -> bool:
        """Mock health check."""
        self._log_call("health_check")
        await self._maybe_fail("health_check")
        return self.is_healthy

    async def get_model_metadata(self) -> Optional[KServeModelMetadata]:
        """Mock model metadata retrieval."""
        self._log_call("get_model_metadata")
        await self._maybe_fail("get_model_metadata")
        return self.mock_model_metadata

    async def close(self):
        """Mock client close."""
        self._log_call("close")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Testing helper methods
    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called."""
        return len([call for call in self.call_log if call["method"] == method])

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get call log, optionally filtered by method."""
        if method:
            return [call for call in self.call_log if call["method"] == method]
        return self.call_log.copy()

    def get_last_call(self, method: str = None) -> Optional[Dict[str, Any]]:
        """Get the last call, optionally filtered by method."""
        calls = self.get_calls(method)
        return calls[-1] if calls else None

    def get_generate_image_calls(self) -> List[Dict[str, Any]]:
        """Get all generate_image calls with their parameters."""
        return self.get_calls("generate_image")

    def was_called_with(self, method: str, **kwargs) -> bool:
        """Check if method was called with specific arguments."""
        calls = self.get_calls(method)
        for call in calls:
            call_args = call.get("args", {})
            if all(call_args.get(key) == value for key, value in kwargs.items()):
                return True
        return False


class FailingMockKServeClient(MockKServeClient):
    """Mock KServe client that always fails."""

    def __init__(self, exception: Exception = None, **kwargs):
        """Initialize failing client."""
        super().__init__(**kwargs)
        self.set_failure_mode(True, exception or KServeError("Mock client always fails"))


class SlowMockKServeClient(MockKServeClient):
    """Mock KServe client with configurable delays."""

    def __init__(self, delay_seconds: float = 1.0, **kwargs):
        """Initialize slow client."""
        super().__init__(**kwargs)
        self.set_response_delay(delay_seconds)


class UnhealthyMockKServeClient(MockKServeClient):
    """Mock KServe client that reports as unhealthy."""

    def __init__(self, **kwargs):
        """Initialize unhealthy client."""
        super().__init__(**kwargs)
        self.set_health_status(False, False)


class RateLimitedMockKServeClient(MockKServeClient):
    """Mock KServe client with rate limiting."""

    def __init__(self, rate_limit: int = 5, **kwargs):
        """Initialize rate limited client."""
        super().__init__(**kwargs)
        self.set_rate_limit(rate_limit)


class TimeoutMockKServeClient(MockKServeClient):
    """Mock KServe client that simulates timeouts."""

    def __init__(self, **kwargs):
        """Initialize timeout client."""
        super().__init__(**kwargs)
        self.set_failure_mode(True, KServeTimeoutError("Request timed out"))


class ConnectionErrorMockKServeClient(MockKServeClient):
    """Mock KServe client that simulates connection errors."""

    def __init__(self, **kwargs):
        """Initialize connection error client."""
        super().__init__(**kwargs)
        self.set_failure_mode(True, KServeConnectionError("Connection failed"))


class ValidationErrorMockKServeClient(MockKServeClient):
    """Mock KServe client that validates inputs strictly."""

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> InternalImageResponse:
        """Generate image with strict validation."""
        # Perform validation
        if not prompt or len(prompt.strip()) == 0:
            raise KServeValidationError("Prompt cannot be empty")
        
        if width < 64 or width > 2048:
            raise KServeValidationError("Width must be between 64 and 2048")
            
        if height < 64 or height > 2048:
            raise KServeValidationError("Height must be between 64 and 2048")
            
        if num_inference_steps < 1 or num_inference_steps > 200:
            raise KServeValidationError("Steps must be between 1 and 200")
            
        if guidance_scale < 1.0 or guidance_scale > 20.0:
            raise KServeValidationError("Guidance scale must be between 1.0 and 20.0")

        return await super().generate_image(
            prompt, negative_prompt, width, height, 
            num_inference_steps, guidance_scale, seed
        )


class RealisticMockKServeClient(MockKServeClient):
    """Mock KServe client with realistic behavior and data."""

    def __init__(self, **kwargs):
        """Initialize realistic client."""
        super().__init__(**kwargs)
        self.generation_time = 3.2  # More realistic generation time
        
        # Set more realistic image data
        self.mock_image_data = self._create_realistic_image_data()

    def _create_realistic_image_data(self) -> bytes:
        """Create more realistic image data."""
        # Create a larger, more PNG-like structure
        header = b"\x89PNG\r\n\x1a\n"
        ihdr = b"\x00\x00\x00\rIHDR\x00\x00\x02\x00\x00\x00\x02\x00\x08\x06\x00\x00\x00"
        # Add some realistic-sized fake image data
        fake_image_content = b"fake_png_data" * 100  # Simulate realistic file size
        iend = b"\x00\x00\x00\x00IEND\xaeB`\x82"
        
        return header + ihdr + fake_image_content + iend

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> InternalImageResponse:
        """Generate image with realistic timing."""
        # Simulate realistic generation time based on parameters
        base_time = 2.0
        step_factor = num_inference_steps / 50.0
        size_factor = (width * height) / (512 * 512)
        self.generation_time = base_time * step_factor * size_factor
        
        # Add some randomness
        import random
        self.generation_time += random.uniform(-0.5, 0.5)
        self.generation_time = max(0.5, self.generation_time)
        
        return await super().generate_image(
            prompt, negative_prompt, width, height,
            num_inference_steps, guidance_scale, seed
        )


# Factory functions for common test scenarios
def create_mock_client_scenarios() -> Dict[str, MockKServeClient]:
    """Create various mock clients for different test scenarios."""
    base_kwargs = {
        "endpoint": "http://mock-kserve:8080",
        "model_name": "test-model",
        "timeout": 30.0,
        "max_retries": 2,
    }
    
    return {
        "normal": MockKServeClient(**base_kwargs),
        "failing": FailingMockKServeClient(**base_kwargs),
        "slow": SlowMockKServeClient(delay_seconds=0.1, **base_kwargs),
        "unhealthy": UnhealthyMockKServeClient(**base_kwargs),
        "rate_limited": RateLimitedMockKServeClient(rate_limit=3, **base_kwargs),
        "timeout": TimeoutMockKServeClient(**base_kwargs),
        "connection_error": ConnectionErrorMockKServeClient(**base_kwargs),
        "validation_error": ValidationErrorMockKServeClient(**base_kwargs),
        "realistic": RealisticMockKServeClient(**base_kwargs),
    }


# Mock client factory for dependency injection
class MockKServeClientFactory:
    """Factory for creating mock KServe clients."""
    
    def __init__(self):
        self.instances: Dict[str, MockKServeClient] = {}
        self.default_type = "normal"
    
    def create_client(
        self, 
        client_type: str = None,
        endpoint: str = "http://mock-kserve:8080",
        model_name: str = "test-model",
        **kwargs
    ) -> MockKServeClient:
        """Create mock client instance."""
        client_type = client_type or self.default_type
        
        base_kwargs = {
            "endpoint": endpoint,
            "model_name": model_name,
            **kwargs
        }
        
        if client_type == "failing":
            return FailingMockKServeClient(**base_kwargs)
        elif client_type == "slow":
            return SlowMockKServeClient(**base_kwargs)
        elif client_type == "unhealthy":
            return UnhealthyMockKServeClient(**base_kwargs)
        elif client_type == "rate_limited":
            return RateLimitedMockKServeClient(**base_kwargs)
        elif client_type == "timeout":
            return TimeoutMockKServeClient(**base_kwargs)
        elif client_type == "connection_error":
            return ConnectionErrorMockKServeClient(**base_kwargs)
        elif client_type == "validation_error":
            return ValidationErrorMockKServeClient(**base_kwargs)
        elif client_type == "realistic":
            return RealisticMockKServeClient(**base_kwargs)
        else:
            return MockKServeClient(**base_kwargs)
    
    def get_or_create(self, name: str, client_type: str = None, **kwargs) -> MockKServeClient:
        """Get existing instance or create new one."""
        if name not in self.instances:
            self.instances[name] = self.create_client(client_type, **kwargs)
        return self.instances[name]
    
    def reset_all(self):
        """Reset all managed client instances."""
        for client in self.instances.values():
            client.reset()
    
    def clear_all(self):
        """Clear all managed client instances."""
        self.instances.clear()


# Test utilities for mocking HTTP responses
class MockHttpResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status_code: int = 200, json_data: Dict = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._text = text
    
    def json(self):
        """Return JSON data."""
        return self._json_data
    
    @property
    def text(self):
        """Return text content."""
        return self._text


class MockHttpClient:
    """Mock HTTP client for testing KServe requests."""
    
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.responses: List[MockHttpResponse] = []
        self.default_response = MockHttpResponse()
    
    def add_response(self, response: MockHttpResponse):
        """Add response to queue."""
        self.responses.append(response)
    
    def set_default_response(self, response: MockHttpResponse):
        """Set default response."""
        self.default_response = response
    
    async def request(self, method: str, url: str, **kwargs):
        """Mock request method."""
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        if self.responses:
            return self.responses.pop(0)
        return self.default_response
    
    async def aclose(self):
        """Mock close method."""
        pass
    
    def get_requests(self) -> List[Dict[str, Any]]:
        """Get all recorded requests."""
        return self.requests.copy()
    
    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get last recorded request."""
        return self.requests[-1] if self.requests else None
    
    def clear_requests(self):
        """Clear recorded requests."""
        self.requests.clear()
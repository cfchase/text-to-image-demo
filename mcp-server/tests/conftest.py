"""Pytest configuration and fixtures for MCP image generation server tests."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from config.settings import Settings
from storage.base import AbstractStorage
from kserve.client import KServeClient
from kserve.models import (
    InternalImageRequest,
    InternalImageResponse,
    KServeInferenceResponse,
    KServePrediction,
)
from utils.ids import generate_image_id


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "storage: marks tests related to storage")
    config.addinivalue_line("markers", "kserve: marks tests related to KServe")
    config.addinivalue_line("markers", "api: marks tests related to API endpoints")


# Async event loop fixture
@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an async event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Temporary directory fixtures
@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Create a temporary file for testing."""
    temp_file = temp_dir / "test_file.tmp"
    temp_file.touch()
    return temp_file


# Sample data fixtures
@pytest.fixture
def sample_image_data() -> bytes:
    """Sample PNG image data for testing."""
    # Valid PNG header + minimal data
    return (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk
        b"\x00\x00\x00\x01"  # Width: 1
        b"\x00\x00\x00\x01"  # Height: 1
        b"\x08\x02\x00\x00\x00\x90wS\xde"  # Rest of IHDR
        b"\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb"  # IDAT chunk
        b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND chunk
    )


@pytest.fixture
def sample_jpeg_data() -> bytes:
    """Sample JPEG image data for testing."""
    # Valid JPEG header + minimal data
    return (
        b"\xff\xd8\xff\xe0"  # JPEG SOI + APP0
        b"\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"  # JFIF header
        b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01"  # SOF0
        b"\xff\xd9"  # EOI
    )


@pytest.fixture
def sample_webp_data() -> bytes:
    """Sample WebP image data for testing."""
    # Valid WebP header + minimal data
    return (
        b"RIFF"  # RIFF header
        b"\x1a\x00\x00\x00"  # File size
        b"WEBP"  # WebP signature
        b"VP8 "  # VP8 format
        b"\x0e\x00\x00\x00"  # VP8 chunk size
        b"\x10\x00\x00\x9d\x01*\x01\x00\x01\x00\x01\x00"  # VP8 data
    )


@pytest.fixture
def sample_image_metadata() -> Dict[str, Any]:
    """Sample image generation metadata for testing."""
    return {
        "prompt": "a beautiful sunset over mountains",
        "negative_prompt": "blurry, low quality",
        "width": 512,
        "height": 512,
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
        "seed": 42,
        "model_name": "stable-diffusion-v1-5",
        "generation_time": 2.5,
    }


@pytest.fixture
def sample_metadata_list() -> List[Dict[str, Any]]:
    """Sample list of image metadata for testing."""
    return [
        {
            "image_id": "img_001",
            "prompt": "sunset",
            "width": 512,
            "height": 512,
            "size": 1024,
            "created_at": "2024-01-01T12:00:00Z",
        },
        {
            "image_id": "img_002", 
            "prompt": "mountain",
            "width": 1024,
            "height": 1024,
            "size": 2048,
            "created_at": "2024-01-01T13:00:00Z",
        },
    ]


# Configuration fixtures
@pytest.fixture
def test_settings() -> Settings:
    """Test settings with safe defaults."""
    return Settings(
        service_name="test-mcp-server",
        log_level="DEBUG",
        host="127.0.0.1",
        port=18000,
        workers=1,
        storage_backend="file",
        storage_path="/tmp/test-mcp-images",
        kserve_endpoint="http://localhost:8080",
        kserve_model_name="test-model",
        kserve_timeout=30.0,
        kserve_max_retries=1,
        image_cleanup_interval=60,
        image_ttl=300,
        max_image_size=5242880,  # 5MB
    )


@pytest.fixture
def s3_test_settings() -> Settings:
    """Test settings configured for S3 storage."""
    return Settings(
        service_name="test-mcp-server",
        log_level="DEBUG",
        host="127.0.0.1",
        port=18000,
        workers=1,
        storage_backend="s3",
        storage_path="/tmp/test-mcp-images",
        s3_bucket="test-bucket",
        s3_prefix="test-images/",
        s3_endpoint_url="http://localhost:9000",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
        aws_region="us-test-1",
        kserve_endpoint="http://localhost:8080",
        kserve_model_name="test-model",
        kserve_timeout=30.0,
        kserve_max_retries=1,
        image_cleanup_interval=60,
        image_ttl=300,
        max_image_size=5242880,
    )


# HTTP client fixtures
@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for testing API endpoints."""
    async with AsyncClient() as client:
        yield client


# Request/Response fixtures
@pytest.fixture
def sample_image_request() -> InternalImageRequest:
    """Sample internal image generation request."""
    return InternalImageRequest(
        prompt="a beautiful sunset",
        negative_prompt="blurry",
        width=512,
        height=512,
        num_inference_steps=20,
        guidance_scale=7.5,
        seed=42,
    )


@pytest.fixture
def sample_image_response(sample_image_data: bytes, sample_image_metadata: Dict[str, Any]) -> InternalImageResponse:
    """Sample internal image generation response."""
    return InternalImageResponse(
        image_data=sample_image_data,
        metadata=sample_image_metadata,
        generation_time=2.5,
    )


@pytest.fixture
def sample_kserve_response(sample_image_data: bytes, sample_image_metadata: Dict[str, Any]) -> KServeInferenceResponse:
    """Sample KServe inference response."""
    import base64
    
    prediction = KServePrediction(
        image_data=base64.b64encode(sample_image_data).decode("utf-8"),
        metadata=sample_image_metadata,
    )
    
    return KServeInferenceResponse(
        model_name="stable-diffusion",
        model_version="v1.5",
        predictions=[prediction],
    )


# ID generation fixtures
@pytest.fixture
def sample_image_id() -> str:
    """Generate a sample image ID for testing."""
    return generate_image_id()


@pytest.fixture
def sample_image_ids() -> List[str]:
    """Generate multiple sample image IDs for testing."""
    return [generate_image_id() for _ in range(5)]


# File path fixtures
@pytest.fixture
def sample_image_files(temp_dir: Path, sample_image_data: bytes, sample_image_ids: List[str]) -> List[Path]:
    """Create sample image files for testing."""
    files = []
    for image_id in sample_image_ids:
        file_path = temp_dir / f"{image_id}.png"
        file_path.write_bytes(sample_image_data)
        files.append(file_path)
    return files


@pytest.fixture
def sample_metadata_files(
    temp_dir: Path, 
    sample_image_metadata: Dict[str, Any], 
    sample_image_ids: List[str]
) -> List[Path]:
    """Create sample metadata files for testing."""
    files = []
    for image_id in sample_image_ids:
        file_path = temp_dir / f"{image_id}.json"
        metadata = sample_image_metadata.copy()
        metadata["image_id"] = image_id
        file_path.write_text(json.dumps(metadata, indent=2))
        files.append(file_path)
    return files


# Mock factories for dependency injection
@pytest.fixture
def mock_storage() -> Mock:
    """Create a mock storage backend."""
    from tests.mocks.storage import MockStorage
    return MockStorage()


@pytest.fixture
def mock_kserve_client() -> Mock:
    """Create a mock KServe client."""
    from tests.mocks.kserve import MockKServeClient
    return MockKServeClient(
        endpoint="http://localhost:8080",
        model_name="test-model"
    )


# Environment variable override fixtures
@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    env_vars_to_clear = [
        "SERVICE_NAME",
        "LOG_LEVEL", 
        "HOST",
        "PORT",
        "WORKERS",
        "STORAGE_BACKEND",
        "STORAGE_PATH",
        "S3_BUCKET",
        "S3_PREFIX",
        "S3_ENDPOINT_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "KSERVE_ENDPOINT",
        "KSERVE_MODEL_NAME",
        "KSERVE_TIMEOUT",
        "KSERVE_MAX_RETRIES",
        "IMAGE_CLEANUP_INTERVAL",
        "IMAGE_TTL",
        "MAX_IMAGE_SIZE",
    ]
    
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def override_env(monkeypatch):
    """Override environment variables for testing."""
    test_env = {
        "SERVICE_NAME": "test-service",
        "LOG_LEVEL": "DEBUG",
        "HOST": "127.0.0.1",
        "PORT": "18000",
        "STORAGE_BACKEND": "file",
        "STORAGE_PATH": "/tmp/test-storage",
        "KSERVE_ENDPOINT": "http://localhost:8080",
        "KSERVE_MODEL_NAME": "test-model",
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


# Performance measurement fixtures
@pytest.fixture
def perf_counter():
    """Performance counter for timing tests."""
    import time
    
    class PerfCounter:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
            return self
        
        def stop(self):
            self.end_time = time.perf_counter()
            return self
        
        @property
        def elapsed(self) -> float:
            if self.start_time is None or self.end_time is None:
                raise ValueError("Timer not properly started/stopped")
            return self.end_time - self.start_time
    
    return PerfCounter()


# Error injection fixtures
@pytest.fixture
def error_injector():
    """Helper for injecting errors in tests."""
    class ErrorInjector:
        def __init__(self):
            self.should_fail = False
            self.exception_type = Exception
            self.exception_message = "Injected error"
        
        def enable(self, exception_type: type = Exception, message: str = "Injected error"):
            self.should_fail = True
            self.exception_type = exception_type
            self.exception_message = message
        
        def disable(self):
            self.should_fail = False
        
        def maybe_raise(self):
            if self.should_fail:
                raise self.exception_type(self.exception_message)
    
    return ErrorInjector()


# Concurrency testing fixtures
@pytest.fixture
def concurrent_executor():
    """Executor for running concurrent operations in tests."""
    import asyncio
    from typing import Awaitable, List, TypeVar
    
    T = TypeVar('T')
    
    class ConcurrentExecutor:
        async def run_concurrent(self, operations: List[Awaitable[T]], max_concurrent: int = 10) -> List[T]:
            """Run operations concurrently with a limit."""
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def run_with_semaphore(operation: Awaitable[T]) -> T:
                async with semaphore:
                    return await operation
            
            tasks = [run_with_semaphore(op) for op in operations]
            return await asyncio.gather(*tasks)
        
        async def run_with_delays(self, operations: List[Awaitable[T]], delay: float = 0.1) -> List[T]:
            """Run operations with delays between them."""
            results = []
            for operation in operations:
                result = await operation
                results.append(result)
                if delay > 0:
                    await asyncio.sleep(delay)
            return results
    
    return ConcurrentExecutor()


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_temp_files(temp_dir: Path):
    """Auto-cleanup temporary files after each test."""
    yield
    # Cleanup is handled by tempfile.TemporaryDirectory context manager


# Logging fixtures
@pytest.fixture
def capture_logs(caplog):
    """Capture logs for testing."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


# Database/State fixtures for stateful tests
@pytest.fixture
def test_state():
    """Shared test state for stateful tests."""
    class TestState:
        def __init__(self):
            self.data = {}
            self.counters = {}
        
        def set(self, key: str, value: Any):
            self.data[key] = value
        
        def get(self, key: str, default: Any = None):
            return self.data.get(key, default)
        
        def increment(self, counter: str) -> int:
            self.counters[counter] = self.counters.get(counter, 0) + 1
            return self.counters[counter]
        
        def reset(self):
            self.data.clear()
            self.counters.clear()
    
    return TestState()


# Assertion helpers
@pytest.fixture
def assert_helpers():
    """Helper functions for common assertions."""
    class AssertHelpers:
        @staticmethod
        def assert_image_data_valid(image_data: bytes):
            """Assert that image data is valid."""
            assert isinstance(image_data, bytes)
            assert len(image_data) > 0
            # Check for common image format signatures
            assert (
                image_data.startswith(b"\x89PNG") or  # PNG
                image_data.startswith(b"\xff\xd8\xff") or  # JPEG
                (len(image_data) >= 12 and image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP")  # WebP
            ), "Image data doesn't appear to be a valid image format"
        
        @staticmethod
        def assert_metadata_valid(metadata: Dict[str, Any], required_fields: Optional[List[str]] = None):
            """Assert that metadata is valid."""
            assert isinstance(metadata, dict)
            if required_fields:
                for field in required_fields:
                    assert field in metadata, f"Required field '{field}' missing from metadata"
        
        @staticmethod
        def assert_response_time_acceptable(duration: float, max_duration: float = 5.0):
            """Assert that response time is acceptable."""
            assert duration <= max_duration, f"Response time {duration}s exceeds maximum {max_duration}s"
    
    return AssertHelpers()
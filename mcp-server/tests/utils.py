"""Test utilities and helper functions for MCP image generation server tests."""

import asyncio
import base64
import hashlib
import json
import random
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import patch

import pytest

from utils.ids import generate_image_id
from utils.images import SUPPORTED_FORMATS, validate_image


class TestImageGenerator:
    """Utility class for generating test image data."""
    
    @staticmethod
    def create_png_data(width: int = 1, height: int = 1) -> bytes:
        """Create minimal valid PNG data."""
        # PNG signature
        png_signature = b"\x89PNG\r\n\x1a\n"
        
        # IHDR chunk
        ihdr_data = (
            width.to_bytes(4, "big") +
            height.to_bytes(4, "big") +
            b"\x08\x02\x00\x00\x00"  # bit depth, color type, compression, filter, interlace
        )
        ihdr_crc = TestImageGenerator._calculate_crc(b"IHDR" + ihdr_data)
        ihdr_chunk = (
            len(ihdr_data).to_bytes(4, "big") +
            b"IHDR" +
            ihdr_data +
            ihdr_crc.to_bytes(4, "big")
        )
        
        # IDAT chunk (minimal data)
        idat_data = b"\x78\x9c\x62\x00\x00\x00\x02\x00\x01"
        idat_crc = TestImageGenerator._calculate_crc(b"IDAT" + idat_data)
        idat_chunk = (
            len(idat_data).to_bytes(4, "big") +
            b"IDAT" +
            idat_data +
            idat_crc.to_bytes(4, "big")
        )
        
        # IEND chunk
        iend_crc = TestImageGenerator._calculate_crc(b"IEND")
        iend_chunk = (
            b"\x00\x00\x00\x00" +  # length
            b"IEND" +
            iend_crc.to_bytes(4, "big")
        )
        
        return png_signature + ihdr_chunk + idat_chunk + iend_chunk
    
    @staticmethod
    def create_jpeg_data() -> bytes:
        """Create minimal valid JPEG data."""
        return (
            b"\xff\xd8"  # SOI
            b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"  # APP0
            b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01"  # SOF0
            b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08"  # DHT
            b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"  # SOS
            b"\x00"  # Minimal image data
            b"\xff\xd9"  # EOI
        )
    
    @staticmethod
    def create_webp_data() -> bytes:
        """Create minimal valid WebP data."""
        return (
            b"RIFF"  # RIFF header
            b"\x1a\x00\x00\x00"  # File size
            b"WEBP"  # WebP signature
            b"VP8 "  # VP8 format
            b"\x0e\x00\x00\x00"  # VP8 chunk size
            b"\x10\x00\x00\x9d\x01*\x01\x00\x01\x00\x01\x00"  # VP8 data
        )
    
    @staticmethod
    def create_random_image_data(format_type: str = "PNG", size: int = None) -> bytes:
        """Create random image data of specified format and approximate size."""
        if format_type.upper() == "PNG":
            base_data = TestImageGenerator.create_png_data()
        elif format_type.upper() == "JPEG":
            base_data = TestImageGenerator.create_jpeg_data()
        elif format_type.upper() == "WEBP":
            base_data = TestImageGenerator.create_webp_data()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        if size and size > len(base_data):
            # Pad with random data to reach desired size
            padding_size = size - len(base_data)
            padding = bytes(random.randint(0, 255) for _ in range(padding_size))
            return base_data + padding
        
        return base_data
    
    @staticmethod
    def _calculate_crc(data: bytes) -> int:
        """Calculate CRC32 for PNG chunks."""
        import zlib
        return zlib.crc32(data) & 0xffffffff


class TestDataGenerator:
    """Utility class for generating test data and metadata."""
    
    @staticmethod
    def create_image_metadata(
        image_id: str = None,
        prompt: str = None,
        **overrides
    ) -> Dict[str, Any]:
        """Create realistic image metadata."""
        base_metadata = {
            "image_id": image_id or generate_image_id(),
            "prompt": prompt or "a beautiful landscape with mountains and lakes",
            "negative_prompt": "blurry, low quality, distorted",
            "width": 512,
            "height": 512,
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
            "seed": random.randint(1, 1000000),
            "model_name": "stable-diffusion-v1-5",
            "generation_time": round(random.uniform(2.0, 5.0), 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "format": "png",
            "size": random.randint(1024, 10240),
        }
        
        base_metadata.update(overrides)
        return base_metadata
    
    @staticmethod
    def create_multiple_metadata(count: int, prefix: str = "test_img") -> List[Dict[str, Any]]:
        """Create multiple image metadata entries."""
        return [
            TestDataGenerator.create_image_metadata(
                image_id=f"{prefix}_{i:03d}",
                prompt=f"test prompt {i}",
                seed=i * 42,
            )
            for i in range(count)
        ]
    
    @staticmethod
    def create_request_data(**overrides) -> Dict[str, Any]:
        """Create realistic request data."""
        base_request = {
            "prompt": "a beautiful sunset over mountains",
            "negative_prompt": "blurry, low quality",
            "width": 512,
            "height": 512,
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
            "seed": 42,
        }
        
        base_request.update(overrides)
        return base_request
    
    @staticmethod
    def create_batch_requests(count: int) -> List[Dict[str, Any]]:
        """Create multiple request data entries."""
        prompts = [
            "a beautiful sunset",
            "a mountain landscape", 
            "a forest in autumn",
            "a city skyline",
            "an abstract painting",
            "a flower garden",
            "a snow-covered mountain",
            "a tropical beach",
        ]
        
        return [
            TestDataGenerator.create_request_data(
                prompt=prompts[i % len(prompts)],
                seed=i * 123,
                guidance_scale=round(random.uniform(5.0, 10.0), 1),
            )
            for i in range(count)
        ]


class AsyncTestHelper:
    """Helper class for async testing utilities."""
    
    @staticmethod
    async def run_concurrent_operations(
        operations: List,
        max_concurrent: int = 10,
        return_exceptions: bool = True
    ) -> List[Any]:
        """Run multiple async operations concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(op):
            async with semaphore:
                return await op
        
        tasks = [run_with_semaphore(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
    
    @staticmethod
    async def measure_execution_time(coroutine) -> Tuple[Any, float]:
        """Measure execution time of a coroutine."""
        start_time = time.perf_counter()
        result = await coroutine
        end_time = time.perf_counter()
        return result, end_time - start_time
    
    @staticmethod
    async def retry_with_backoff(
        operation,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        backoff_factor: float = 2.0
    ):
        """Retry an async operation with exponential backoff."""
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        
        raise last_exception
    
    @staticmethod
    def create_timeout_task(delay: float):
        """Create a task that times out after specified delay."""
        async def timeout_operation():
            await asyncio.sleep(delay)
            raise TimeoutError(f"Operation timed out after {delay}s")
        
        return asyncio.create_task(timeout_operation())


class FileTestHelper:
    """Helper class for file-based testing utilities."""
    
    @staticmethod
    def create_temp_directory() -> Path:
        """Create a temporary directory for testing."""
        return Path(tempfile.mkdtemp())
    
    @staticmethod
    def create_test_files(
        directory: Path,
        file_specs: List[Dict[str, Any]]
    ) -> List[Path]:
        """Create test files based on specifications."""
        created_files = []
        
        for spec in file_specs:
            filename = spec["name"]
            content = spec.get("content", b"")
            
            file_path = directory / filename
            
            if isinstance(content, str):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_bytes(content)
            
            created_files.append(file_path)
        
        return created_files
    
    @staticmethod
    def create_image_files(
        directory: Path,
        count: int = 5,
        prefix: str = "test_img"
    ) -> List[Path]:
        """Create test image files."""
        created_files = []
        
        for i in range(count):
            filename = f"{prefix}_{i:03d}.png"
            image_data = TestImageGenerator.create_png_data()
            
            file_path = directory / filename
            file_path.write_bytes(image_data)
            created_files.append(file_path)
        
        return created_files
    
    @staticmethod
    def create_metadata_files(
        directory: Path,
        metadata_list: List[Dict[str, Any]]
    ) -> List[Path]:
        """Create metadata JSON files."""
        created_files = []
        
        for metadata in metadata_list:
            image_id = metadata.get("image_id", generate_image_id())
            filename = f"{image_id}.json"
            
            file_path = directory / filename
            file_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            created_files.append(file_path)
        
        return created_files


class AssertionHelper:
    """Helper class for common test assertions."""
    
    @staticmethod
    def assert_image_data_valid(image_data: bytes, expected_format: str = None):
        """Assert that image data is valid."""
        assert isinstance(image_data, bytes), "Image data must be bytes"
        assert len(image_data) > 0, "Image data cannot be empty"
        
        # Validate image format if specified
        if expected_format:
            try:
                result = validate_image(image_data, allowed_formats=[expected_format.upper()])
                assert result["format"] == expected_format.upper()
            except Exception as e:
                pytest.fail(f"Image validation failed: {e}")
    
    @staticmethod
    def assert_metadata_complete(metadata: Dict[str, Any], required_fields: List[str] = None):
        """Assert that metadata contains required fields."""
        if required_fields is None:
            required_fields = ["image_id", "prompt", "width", "height", "created_at"]
        
        for field in required_fields:
            assert field in metadata, f"Required field '{field}' missing from metadata"
            assert metadata[field] is not None, f"Field '{field}' cannot be None"
    
    @staticmethod
    def assert_response_time_acceptable(duration: float, max_duration: float = 10.0):
        """Assert that response time is within acceptable limits."""
        assert duration >= 0, "Duration cannot be negative"
        assert duration <= max_duration, f"Response time {duration:.2f}s exceeds maximum {max_duration}s"
    
    @staticmethod
    def assert_images_equal(image1: bytes, image2: bytes):
        """Assert that two image byte arrays are identical."""
        assert isinstance(image1, bytes) and isinstance(image2, bytes)
        assert len(image1) == len(image2), f"Image sizes differ: {len(image1)} vs {len(image2)}"
        assert image1 == image2, "Image data differs"
    
    @staticmethod
    def assert_similar_metadata(metadata1: Dict[str, Any], metadata2: Dict[str, Any], ignore_fields: List[str] = None):
        """Assert that two metadata dictionaries are similar (ignoring specified fields)."""
        ignore_fields = ignore_fields or ["created_at", "modified_at", "generation_time"]
        
        for key, value in metadata1.items():
            if key not in ignore_fields:
                assert key in metadata2, f"Key '{key}' missing from metadata2"
                assert metadata2[key] == value, f"Value mismatch for key '{key}': {value} vs {metadata2[key]}"


class MockDataHelper:
    """Helper class for creating mock data."""
    
    @staticmethod
    def create_base64_image(image_data: bytes) -> str:
        """Create base64 encoded image data."""
        return base64.b64encode(image_data).decode("utf-8")
    
    @staticmethod
    def create_mock_kserve_response(
        image_data: bytes,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create mock KServe inference response."""
        if metadata is None:
            metadata = TestDataGenerator.create_image_metadata()
        
        return {
            "model_name": "stable-diffusion",
            "model_version": "v1.5",
            "predictions": [
                {
                    "image_data": MockDataHelper.create_base64_image(image_data),
                    "metadata": metadata,
                }
            ]
        }
    
    @staticmethod
    def create_error_response(error_message: str, error_code: str = "INFERENCE_ERROR") -> Dict[str, Any]:
        """Create mock error response."""
        return {
            "error": error_message,
            "code": error_code,
            "details": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": generate_image_id(),
            }
        }


class TestStateManager:
    """Helper class for managing test state across test runs."""
    
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, float] = {}
    
    def set_value(self, key: str, value: Any):
        """Set a state value."""
        self.state[key] = value
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)
    
    def increment_counter(self, name: str) -> int:
        """Increment a counter and return new value."""
        self.counters[name] = self.counters.get(name, 0) + 1
        return self.counters[name]
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)
    
    def start_timer(self, name: str):
        """Start a timer."""
        self.timers[name] = time.perf_counter()
    
    def stop_timer(self, name: str) -> float:
        """Stop a timer and return elapsed time."""
        if name not in self.timers:
            raise ValueError(f"Timer '{name}' was not started")
        
        elapsed = time.perf_counter() - self.timers[name]
        del self.timers[name]
        return elapsed
    
    def reset(self):
        """Reset all state."""
        self.state.clear()
        self.counters.clear()
        self.timers.clear()


class EnvironmentHelper:
    """Helper class for managing test environment."""
    
    @staticmethod
    def patch_environment_variables(env_vars: Dict[str, str]):
        """Context manager to patch environment variables."""
        return patch.dict("os.environ", env_vars)
    
    @staticmethod
    def create_test_settings_dict(**overrides) -> Dict[str, Any]:
        """Create test settings dictionary."""
        default_settings = {
            "service_name": "test-mcp-server",
            "log_level": "DEBUG",
            "host": "127.0.0.1",
            "port": 18000,
            "workers": 1,
            "storage_backend": "file",
            "storage_path": "/tmp/test-mcp-images",
            "kserve_endpoint": "http://localhost:8080",
            "kserve_model_name": "test-model",
            "kserve_timeout": 30.0,
            "kserve_max_retries": 2,
            "image_cleanup_interval": 60,
            "image_ttl": 300,
            "max_image_size": 5242880,
        }
        
        default_settings.update(overrides)
        return default_settings


# Global test state manager instance
test_state = TestStateManager()


# Convenience functions
def create_test_image(format_type: str = "PNG", size: Optional[int] = None) -> bytes:
    """Create a test image of specified format and size."""
    return TestImageGenerator.create_random_image_data(format_type, size)


def create_test_metadata(**overrides) -> Dict[str, Any]:
    """Create test metadata with optional overrides."""
    return TestDataGenerator.create_image_metadata(**overrides)


def hash_image_data(image_data: bytes) -> str:
    """Calculate hash of image data for comparison."""
    return hashlib.sha256(image_data).hexdigest()


def assert_valid_uuid(uuid_string: str):
    """Assert that string is a valid UUID."""
    import uuid
    try:
        uuid.UUID(uuid_string)
    except (ValueError, AttributeError):
        pytest.fail(f"'{uuid_string}' is not a valid UUID")


def assert_valid_timestamp(timestamp_string: str):
    """Assert that string is a valid ISO timestamp."""
    try:
        datetime.fromisoformat(timestamp_string.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"'{timestamp_string}' is not a valid ISO timestamp")


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true."""
    async def _wait():
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)
        return False
    
    return _wait()
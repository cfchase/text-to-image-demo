"""Mock storage implementations for testing."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

from mcp_server.storage.base import AbstractStorage, ImageNotFoundError, StorageError


class MockStorage(AbstractStorage):
    """In-memory storage implementation for testing."""

    def __init__(self):
        """Initialize mock storage."""
        super().__init__()
        self.images: Dict[str, bytes] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.urls: Dict[str, str] = {}
        self.call_log: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_exception = StorageError("Mock storage failure")
        self.failure_methods: List[str] = []
        self.delay_seconds = 0.0
        self.max_operations = None
        self.operation_count = 0

    def reset(self):
        """Reset mock storage to initial state."""
        self.images.clear()
        self.metadata.clear()
        self.urls.clear()
        self.call_log.clear()
        self.should_fail = False
        self.failure_exception = StorageError("Mock storage failure")
        self.failure_methods.clear()
        self.delay_seconds = 0.0
        self.max_operations = None
        self.operation_count = 0

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

    def set_delay(self, seconds: float):
        """Set artificial delay for testing timing behavior."""
        self.delay_seconds = seconds

    def set_operation_limit(self, max_operations: int):
        """Set maximum number of operations before failing."""
        self.max_operations = max_operations

    def _log_call(self, method: str, **kwargs):
        """Log method call for testing."""
        self.call_log.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args": kwargs,
        })

    async def _maybe_fail(self, method: str):
        """Check if method should fail based on configuration."""
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        self.operation_count += 1
        
        if self.max_operations and self.operation_count > self.max_operations:
            raise StorageError("Operation limit exceeded")

        if self.should_fail:
            if not self.failure_methods or method in self.failure_methods:
                raise self.failure_exception

    async def save_image(
        self, image_data: bytes, image_id: str, metadata: Dict[str, Any]
    ) -> str:
        """Save an image to mock storage."""
        self._log_call("save_image", image_id=image_id, size=len(image_data))
        await self._maybe_fail("save_image")

        if not image_data:
            raise StorageError("Image data is empty")

        # Store image and metadata
        self.images[image_id] = image_data
        
        # Enhance metadata with storage information
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update({
            "image_id": image_id,
            "size": len(image_data),
            "format": "png",  # Mock assumes PNG for simplicity
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_at": datetime.now(timezone.utc).isoformat(),
        })
        self.metadata[image_id] = enhanced_metadata

        # Generate mock URL
        self.urls[image_id] = f"http://mock-storage/images/{image_id}.png"

        return f"mock://{image_id}.png"

    async def get_image(self, image_id: str) -> Optional[bytes]:
        """Retrieve an image from mock storage."""
        self._log_call("get_image", image_id=image_id)
        await self._maybe_fail("get_image")

        return self.images.get(image_id)

    async def delete_image(self, image_id: str) -> bool:
        """Delete an image from mock storage."""
        self._log_call("delete_image", image_id=image_id)
        await self._maybe_fail("delete_image")

        if image_id in self.images:
            del self.images[image_id]
            self.metadata.pop(image_id, None)
            self.urls.pop(image_id, None)
            return True
        return False

    async def get_image_url(self, image_id: str) -> Optional[str]:
        """Get a URL for accessing the image."""
        self._log_call("get_image_url", image_id=image_id)
        await self._maybe_fail("get_image_url")

        if image_id in self.images:
            return self.urls.get(image_id)
        return None

    async def list_images(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List images in mock storage."""
        self._log_call("list_images", prefix=prefix)
        await self._maybe_fail("list_images")

        results = []
        for image_id, metadata in self.metadata.items():
            if prefix is None or image_id.startswith(prefix):
                # Add actual size information
                enhanced_metadata = metadata.copy()
                if image_id in self.images:
                    enhanced_metadata["actual_size"] = len(self.images[image_id])
                results.append(enhanced_metadata)

        # Sort by creation time for consistent ordering
        results.sort(key=lambda x: x.get("created_at", ""))
        return results

    async def cleanup_expired_images(self, ttl_seconds: int) -> int:
        """Remove images older than TTL from mock storage."""
        self._log_call("cleanup_expired_images", ttl_seconds=ttl_seconds)
        await self._maybe_fail("cleanup_expired_images")

        current_time = time.time()
        expired_ids = []

        for image_id, metadata in self.metadata.items():
            created_at = metadata.get("created_at")
            if created_at:
                try:
                    # Parse ISO timestamp
                    created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_seconds = current_time - created_time.timestamp()
                    if age_seconds > ttl_seconds:
                        expired_ids.append(image_id)
                except (ValueError, AttributeError):
                    # If we can't parse the timestamp, consider it expired
                    expired_ids.append(image_id)

        # Delete expired images
        for image_id in expired_ids:
            await self.delete_image(image_id)

        return len(expired_ids)

    # Additional helper methods for testing
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

    def has_image(self, image_id: str) -> bool:
        """Check if image exists in storage."""
        return image_id in self.images

    def get_image_count(self) -> int:
        """Get total number of images in storage."""
        return len(self.images)

    def get_total_size(self) -> int:
        """Get total size of all images in bytes."""
        return sum(len(data) for data in self.images.values())

    def set_image_url(self, image_id: str, url: str):
        """Set custom URL for an image (for testing URL generation)."""
        self.urls[image_id] = url


class FailingMockStorage(MockStorage):
    """Mock storage that always fails - useful for error testing."""

    def __init__(self, exception: Exception = None):
        """Initialize failing storage."""
        super().__init__()
        self.set_failure_mode(True, exception or StorageError("Mock storage always fails"))


class SlowMockStorage(MockStorage):
    """Mock storage with configurable delays - useful for timeout testing."""

    def __init__(self, delay_seconds: float = 1.0):
        """Initialize slow storage."""
        super().__init__()
        self.set_delay(delay_seconds)


class LimitedMockStorage(MockStorage):
    """Mock storage with operation limits - useful for quota testing."""

    def __init__(self, max_operations: int = 10):
        """Initialize limited storage."""
        super().__init__()
        self.set_operation_limit(max_operations)


class PartiallyFailingMockStorage(MockStorage):
    """Mock storage that fails for specific methods."""

    def __init__(self, failing_methods: List[str], exception: Exception = None):
        """Initialize partially failing storage."""
        super().__init__()
        self.set_failure_mode(
            True, 
            exception or StorageError("Mock partial failure"),
            failing_methods
        )


class StatefulMockStorage(MockStorage):
    """Mock storage that tracks state changes for testing."""

    def __init__(self):
        """Initialize stateful storage."""
        super().__init__()
        self.state_history: List[Dict[str, Any]] = []

    def _record_state(self, operation: str):
        """Record current state after operation."""
        self.state_history.append({
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image_count": len(self.images),
            "total_size": sum(len(data) for data in self.images.values()),
            "image_ids": list(self.images.keys()),
        })

    async def save_image(
        self, image_data: bytes, image_id: str, metadata: Dict[str, Any]
    ) -> str:
        """Save image and record state."""
        result = await super().save_image(image_data, image_id, metadata)
        self._record_state(f"save_image:{image_id}")
        return result

    async def delete_image(self, image_id: str) -> bool:
        """Delete image and record state."""
        result = await super().delete_image(image_id)
        self._record_state(f"delete_image:{image_id}")
        return result

    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get complete state history."""
        return self.state_history.copy()

    def get_state_at_operation(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get state after specific operation."""
        for state in reversed(self.state_history):
            if state["operation"] == operation:
                return state
        return None


# Factory functions for common test scenarios
def create_populated_mock_storage(
    image_count: int = 5,
    image_size: int = 1024,
    prefix: str = "test_img"
) -> MockStorage:
    """Create mock storage pre-populated with test data."""
    storage = MockStorage()
    
    # Add test images
    for i in range(image_count):
        image_id = f"{prefix}_{i:03d}"
        image_data = b"fake_image_data" + bytes([i] * (image_size - 15))
        metadata = {
            "prompt": f"test prompt {i}",
            "width": 512,
            "height": 512,
            "guidance_scale": 7.5,
            "num_inference_steps": 20,
        }
        
        # Use synchronous method for setup
        storage.images[image_id] = image_data
        storage.metadata[image_id] = {
            **metadata,
            "image_id": image_id,
            "size": len(image_data),
            "format": "png",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_at": datetime.now(timezone.utc).isoformat(),
        }
        storage.urls[image_id] = f"http://mock-storage/images/{image_id}.png"
    
    return storage


def create_mock_storage_with_scenarios() -> Dict[str, MockStorage]:
    """Create various mock storage instances for different test scenarios."""
    return {
        "empty": MockStorage(),
        "populated": create_populated_mock_storage(),
        "failing": FailingMockStorage(),
        "slow": SlowMockStorage(0.1),  # 100ms delay
        "limited": LimitedMockStorage(5),
        "save_failing": PartiallyFailingMockStorage(["save_image"]),
        "get_failing": PartiallyFailingMockStorage(["get_image"]),
        "delete_failing": PartiallyFailingMockStorage(["delete_image"]),
        "stateful": StatefulMockStorage(),
    }


# Mock storage factory for dependency injection
class MockStorageFactory:
    """Factory for creating mock storage instances."""
    
    def __init__(self):
        self.instances: Dict[str, MockStorage] = {}
        self.default_type = "mock"
    
    def create_storage(self, storage_type: str = None, **kwargs) -> MockStorage:
        """Create mock storage instance."""
        storage_type = storage_type or self.default_type
        
        if storage_type == "failing":
            return FailingMockStorage(kwargs.get("exception"))
        elif storage_type == "slow":
            return SlowMockStorage(kwargs.get("delay_seconds", 1.0))
        elif storage_type == "limited":
            return LimitedMockStorage(kwargs.get("max_operations", 10))
        elif storage_type == "populated":
            return create_populated_mock_storage(
                kwargs.get("image_count", 5),
                kwargs.get("image_size", 1024),
                kwargs.get("prefix", "test_img")
            )
        else:
            return MockStorage()
    
    def get_or_create(self, name: str, storage_type: str = None, **kwargs) -> MockStorage:
        """Get existing instance or create new one."""
        if name not in self.instances:
            self.instances[name] = self.create_storage(storage_type, **kwargs)
        return self.instances[name]
    
    def reset_all(self):
        """Reset all managed storage instances."""
        for storage in self.instances.values():
            storage.reset()
    
    def clear_all(self):
        """Clear all managed storage instances."""
        self.instances.clear()
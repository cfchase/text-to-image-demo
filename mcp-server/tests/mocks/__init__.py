"""Mock implementations for testing MCP image generation server components."""

from .storage import (
    MockStorage,
    FailingMockStorage,
    SlowMockStorage,
    LimitedMockStorage,
    PartiallyFailingMockStorage,
    StatefulMockStorage,
    MockStorageFactory,
    create_populated_mock_storage,
    create_mock_storage_with_scenarios,
)

from .kserve import (
    MockKServeClient,
    FailingMockKServeClient,
    SlowMockKServeClient,
    UnhealthyMockKServeClient,
    RateLimitedMockKServeClient,
    TimeoutMockKServeClient,
    ConnectionErrorMockKServeClient,
    ValidationErrorMockKServeClient,
    RealisticMockKServeClient,
    MockKServeClientFactory,
    MockHttpResponse,
    MockHttpClient,
    create_mock_client_scenarios,
)

__all__ = [
    # Storage mocks
    "MockStorage",
    "FailingMockStorage", 
    "SlowMockStorage",
    "LimitedMockStorage",
    "PartiallyFailingMockStorage",
    "StatefulMockStorage",
    "MockStorageFactory",
    "create_populated_mock_storage",
    "create_mock_storage_with_scenarios",
    
    # KServe mocks
    "MockKServeClient",
    "FailingMockKServeClient",
    "SlowMockKServeClient", 
    "UnhealthyMockKServeClient",
    "RateLimitedMockKServeClient",
    "TimeoutMockKServeClient",
    "ConnectionErrorMockKServeClient",
    "ValidationErrorMockKServeClient",
    "RealisticMockKServeClient",
    "MockKServeClientFactory",
    "MockHttpResponse",
    "MockHttpClient",
    "create_mock_client_scenarios",
]

# Convenience functions for common test setups
def create_test_environment():
    """Create a complete test environment with all mocks."""
    return {
        "storage_factory": MockStorageFactory(),
        "kserve_factory": MockKServeClientFactory(),
        "storage_scenarios": create_mock_storage_with_scenarios(),
        "kserve_scenarios": create_mock_client_scenarios(),
    }


def create_failing_environment():
    """Create test environment where all components fail."""
    return {
        "storage": FailingMockStorage(),
        "kserve_client": FailingMockKServeClient(
            endpoint="http://mock-kserve:8080",
            model_name="test-model"
        ),
    }


def create_slow_environment(delay_seconds: float = 1.0):
    """Create test environment with slow responses."""
    return {
        "storage": SlowMockStorage(delay_seconds),
        "kserve_client": SlowMockKServeClient(
            delay_seconds=delay_seconds,
            endpoint="http://mock-kserve:8080", 
            model_name="test-model"
        ),
    }


def create_realistic_environment():
    """Create test environment with realistic behavior."""
    return {
        "storage": create_populated_mock_storage(image_count=10),
        "kserve_client": RealisticMockKServeClient(
            endpoint="http://mock-kserve:8080",
            model_name="stable-diffusion-v1-5"
        ),
    }
"""Integration tests for KServe client."""

import asyncio
import os
from unittest.mock import patch

import pytest

from src.kserve import KServeClient, KServeConnectionError


class TestKServeIntegration:
    """Integration tests for KServe client.
    
    These tests can be run against a real KServe endpoint if available,
    or will use mocked responses for CI/CD environments.
    """

    @pytest.fixture
    def kserve_endpoint(self):
        """Get KServe endpoint from environment or use mock."""
        return os.environ.get("KSERVE_ENDPOINT", "http://localhost:8080")

    @pytest.fixture
    def model_name(self):
        """Get model name from environment or use default."""
        return os.environ.get("KSERVE_MODEL_NAME", "stable-diffusion")

    @pytest.fixture
    def client(self, kserve_endpoint, model_name):
        """Create KServe client for integration testing."""
        return KServeClient(
            endpoint=kserve_endpoint,
            model_name=model_name,
            timeout=120.0,  # Longer timeout for integration tests
            max_retries=3,
        )

    @pytest.mark.integration
    async def test_health_check_real_endpoint(self, client):
        """Test health check against real endpoint if available."""
        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test
            try:
                is_healthy = await client.health_check()
                # Just check that we get a boolean response
                assert isinstance(is_healthy, bool)
            except KServeConnectionError:
                # Real endpoint might not be available
                pytest.skip("KServe endpoint not available")
        else:
            # Mock test for CI/CD
            with patch.object(client, "_make_request_with_retry") as mock_request:
                mock_response = type("MockResponse", (), {})()
                mock_response.json = lambda: {"name": client.model_name, "ready": True}
                mock_request.return_value = mock_response

                result = await client.health_check()
                assert result is True

        await client.close()

    @pytest.mark.integration
    async def test_model_metadata_real_endpoint(self, client):
        """Test model metadata retrieval against real endpoint if available."""
        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test
            try:
                metadata = await client.get_model_metadata()
                if metadata:
                    assert metadata.name == client.model_name
                    assert hasattr(metadata, "platform")
            except KServeConnectionError:
                pytest.skip("KServe endpoint not available")
        else:
            # Mock test for CI/CD
            with patch.object(client, "_make_request_with_retry") as mock_request:
                mock_response = type("MockResponse", (), {})()
                mock_response.json = lambda: {
                    "name": client.model_name,
                    "platform": "diffusers",
                    "versions": ["v1.0"],
                    "inputs": [{"name": "prompt", "datatype": "STRING", "shape": [-1]}],
                    "outputs": [{"name": "image", "datatype": "BYTES", "shape": [-1]}],
                }
                mock_request.return_value = mock_response

                metadata = await client.get_model_metadata()
                assert metadata is not None
                assert metadata.name == client.model_name
                assert metadata.platform == "diffusers"

        await client.close()

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_image_generation_real_endpoint(self, client):
        """Test image generation against real endpoint if available."""
        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test - only run if explicitly configured
            try:
                # Check if model is ready first
                is_healthy = await client.health_check()
                if not is_healthy:
                    pytest.skip("KServe model not ready")

                # Generate a simple image
                result = await client.generate_image(
                    prompt="a red apple on a table",
                    width=512,
                    height=512,
                    num_inference_steps=20,  # Fewer steps for faster testing
                    guidance_scale=7.5,
                    seed=42,  # Fixed seed for reproducibility
                )

                # Validate response
                assert isinstance(result.image_data, bytes)
                assert len(result.image_data) > 1000  # Should be a real image
                assert result.generation_time > 0
                assert isinstance(result.metadata, dict)

            except KServeConnectionError:
                pytest.skip("KServe endpoint not available")
        else:
            # Mock test for CI/CD
            import base64

            # Create a small test image (1x1 PNG)
            test_image_data = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x00"
                b"\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x18\xdd\x8d\xb4\x00\x00"
                b"\x00\x00IEND\xaeB`\x82"
            )
            test_image_b64 = base64.b64encode(test_image_data).decode("utf-8")

            with patch.object(client, "_make_request_with_retry") as mock_request:
                mock_response = type("MockResponse", (), {})()
                mock_response.json = lambda: {
                    "predictions": [
                        {
                            "image_data": test_image_b64,
                            "metadata": {
                                "generation_time": 15.5,
                                "steps": 20,
                                "guidance": 7.5,
                            },
                        }
                    ],
                    "model_name": client.model_name,
                    "model_version": "v1.0",
                }
                mock_request.return_value = mock_response

                result = await client.generate_image(
                    prompt="a red apple on a table",
                    width=512,
                    height=512,
                    num_inference_steps=20,
                    guidance_scale=7.5,
                    seed=42,
                )

                assert result.image_data == test_image_data
                assert result.generation_time > 0
                assert result.metadata["steps"] == 20

        await client.close()

    @pytest.mark.integration
    async def test_concurrent_health_checks(self, client):
        """Test concurrent health check requests."""
        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test
            try:
                # Make multiple concurrent health checks
                tasks = [client.health_check() for _ in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All should return boolean results or exceptions
                for result in results:
                    if isinstance(result, Exception):
                        assert isinstance(result, KServeConnectionError)
                    else:
                        assert isinstance(result, bool)

            except Exception:
                pytest.skip("Concurrent requests not supported or endpoint unavailable")
        else:
            # Mock test for CI/CD
            with patch.object(client, "_make_request_with_retry") as mock_request:
                mock_response = type("MockResponse", (), {})()
                mock_response.json = lambda: {"name": client.model_name, "ready": True}
                mock_request.return_value = mock_response

                # Make multiple concurrent health checks
                tasks = [client.health_check() for _ in range(5)]
                results = await asyncio.gather(*tasks)

                # All should return True
                assert all(result is True for result in results)

        await client.close()

    @pytest.mark.integration
    async def test_client_context_manager(self, kserve_endpoint, model_name):
        """Test client usage as async context manager."""
        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test
            async with KServeClient(kserve_endpoint, model_name) as client:
                try:
                    result = await client.health_check()
                    assert isinstance(result, bool)
                except KServeConnectionError:
                    # Endpoint might not be available
                    pass
        else:
            # Mock test for CI/CD
            async with KServeClient(kserve_endpoint, model_name) as client:
                with patch.object(client, "_make_request_with_retry") as mock_request:
                    mock_response = type("MockResponse", (), {})()
                    mock_response.json = lambda: {"name": model_name, "ready": True}
                    mock_request.return_value = mock_response

                    result = await client.health_check()
                    assert result is True

    @pytest.mark.integration
    async def test_error_handling_with_invalid_endpoint(self):
        """Test error handling with invalid endpoint."""
        client = KServeClient(
            endpoint="http://invalid-endpoint-that-does-not-exist:9999",
            model_name="test-model",
            timeout=5.0,
            max_retries=1,
        )

        # Should handle connection errors gracefully
        result = await client.health_check()
        assert result is False

        # Should raise appropriate exceptions for generation
        with pytest.raises(KServeConnectionError):
            await client.generate_image(prompt="test prompt")

        await client.close()

    @pytest.mark.integration
    async def test_timeout_handling(self):
        """Test timeout handling with very short timeout."""
        # Use a real endpoint but with very short timeout to test timeout handling
        client = KServeClient(
            endpoint=os.environ.get("KSERVE_ENDPOINT", "http://httpbin.org/delay/10"),
            model_name="test-model",
            timeout=0.1,  # Very short timeout
            max_retries=1,
        )

        # Health check should handle timeout gracefully
        result = await client.health_check()
        assert result is False

        await client.close()

    @pytest.mark.integration
    async def test_large_prompt_handling(self, client):
        """Test handling of large prompts."""
        # Create a very long prompt
        large_prompt = "a beautiful landscape with " * 100  # ~2700 characters

        if os.environ.get("KSERVE_ENDPOINT"):
            # Real endpoint test
            try:
                result = await client.generate_image(
                    prompt=large_prompt,
                    width=256,  # Smaller image for faster processing
                    height=256,
                    num_inference_steps=10,  # Fewer steps
                )
                assert isinstance(result.image_data, bytes)
            except Exception as e:
                # Some endpoints might have prompt length limits
                if "prompt" in str(e).lower() or "length" in str(e).lower():
                    pytest.skip("Endpoint has prompt length limitations")
                else:
                    raise
        else:
            # Mock test - should handle large prompts without issues
            import base64

            test_image_data = b"fake_image_data"
            test_image_b64 = base64.b64encode(test_image_data).decode("utf-8")

            with patch.object(client, "_make_request_with_retry") as mock_request:
                mock_response = type("MockResponse", (), {})()
                mock_response.json = lambda: {
                    "predictions": [
                        {"image_data": test_image_b64, "metadata": {}}
                    ]
                }
                mock_request.return_value = mock_response

                result = await client.generate_image(prompt=large_prompt)
                assert result.image_data == test_image_data

        await client.close()

    @pytest.mark.integration
    async def test_parameter_validation_integration(self, client):
        """Test parameter validation in integration context."""
        # These should work regardless of endpoint
        valid_params = {
            "prompt": "test prompt",
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "seed": 42,
        }

        # Test each parameter validation
        invalid_params_tests = [
            {"prompt": ""},  # Empty prompt
            {"width": 32},  # Too small width
            {"height": 3000},  # Too large height
            {"num_inference_steps": 0},  # Invalid steps
            {"guidance_scale": 0.5},  # Invalid guidance scale
        ]

        for invalid_param in invalid_params_tests:
            test_params = valid_params.copy()
            test_params.update(invalid_param)

            with pytest.raises(Exception):  # Should raise some validation error
                await client.generate_image(**test_params)

        await client.close()
"""Unit tests for KServe client."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.kserve.client import KServeClient
from src.kserve.exceptions import (
    KServeConnectionError,
    KServeInferenceError,
    KServeInvalidResponseError,
    KServeModelNotReadyError,
    KServeRateLimitError,
    KServeTimeoutError,
    KServeValidationError,
)
from src.kserve.models import (
    InternalImageRequest,
    KServeInferenceResponse,
    KServeModelMetadata,
    KServeModelStatus,
    KServePrediction,
)


class TestKServeClient:
    """Test cases for KServeClient."""

    @pytest.fixture
    def client(self):
        """Create KServe client for testing."""
        return KServeClient(
            endpoint="http://localhost:8080",
            model_name="stable-diffusion",
            timeout=30.0,
            max_retries=2,
        )

    @pytest.fixture
    def mock_response_data(self):
        """Mock successful inference response data."""
        # Create a small test image (1x1 PNG)
        test_image = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x18\xdd\x8d\xb4\x00\x00"
            b"\x00\x00IEND\xaeB`\x82"
        ).decode("utf-8")

        return {
            "predictions": [
                {
                    "image_data": test_image,
                    "metadata": {
                        "generation_time": 5.2,
                        "steps": 50,
                        "guidance": 7.5,
                    },
                }
            ],
            "model_name": "stable-diffusion",
            "model_version": "v1.0",
        }

    @pytest.fixture
    def mock_metadata_response(self):
        """Mock model metadata response."""
        return {
            "name": "stable-diffusion",
            "platform": "diffusers",
            "versions": ["v1.0"],
            "inputs": [
                {
                    "name": "prompt",
                    "datatype": "STRING",
                    "shape": [-1],
                }
            ],
            "outputs": [
                {
                    "name": "image",
                    "datatype": "BYTES",
                    "shape": [-1],
                }
            ],
        }

    async def test_client_initialization(self):
        """Test client initialization."""
        client = KServeClient(
            endpoint="http://test.com",
            model_name="test-model",
            timeout=60.0,
            max_retries=5,
        )

        assert client.endpoint == "http://test.com"
        assert client.model_name == "test-model"
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert isinstance(client.client, httpx.AsyncClient)

        await client.close()

    async def test_async_context_manager(self):
        """Test async context manager usage."""
        async with KServeClient("http://test.com", "test-model") as client:
            assert isinstance(client, KServeClient)
            assert client.client is not None

    def test_url_generation(self, client):
        """Test URL generation methods."""
        assert client._get_inference_url() == (
            "http://localhost:8080/v1/models/stable-diffusion/infer"
        )
        assert client._get_metadata_url() == (
            "http://localhost:8080/v1/models/stable-diffusion"
        )
        assert client._get_ready_url() == (
            "http://localhost:8080/v1/models/stable-diffusion/ready"
        )

    def test_convert_to_kserve_format(self, client):
        """Test conversion from internal to KServe format."""
        internal_request = InternalImageRequest(
            prompt="test prompt",
            negative_prompt="bad quality",
            width=512,
            height=768,
            num_inference_steps=25,
            guidance_scale=8.0,
            seed=42,
        )

        kserve_request = client._convert_to_kserve_format(internal_request)

        assert len(kserve_request.instances) == 1
        instance = kserve_request.instances[0]
        assert instance.prompt == "test prompt"
        assert instance.negative_prompt == "bad quality"
        assert instance.width == 512
        assert instance.height == 768
        assert instance.num_inference_steps == 25
        assert instance.guidance_scale == 8.0
        assert instance.seed == 42

    def test_convert_from_kserve_format(self, client, mock_response_data):
        """Test conversion from KServe to internal format."""
        kserve_response = KServeInferenceResponse(**mock_response_data)
        internal_response = client._convert_from_kserve_format(kserve_response, 5.5)

        assert isinstance(internal_response.image_data, bytes)
        assert internal_response.generation_time == 5.5
        assert internal_response.metadata["model_name"] == "stable-diffusion"
        assert internal_response.metadata["model_version"] == "v1.0"
        assert internal_response.metadata["generation_time"] == 5.2

    def test_convert_from_kserve_format_no_predictions(self, client):
        """Test conversion with no predictions raises error."""
        response_data = {"predictions": []}
        kserve_response = KServeInferenceResponse(**response_data)

        with pytest.raises(KServeInvalidResponseError, match="No predictions"):
            client._convert_from_kserve_format(kserve_response, 1.0)

    def test_convert_from_kserve_format_invalid_base64(self, client):
        """Test conversion with invalid base64 data."""
        response_data = {
            "predictions": [{"image_data": "invalid-base64!", "metadata": {}}]
        }
        kserve_response = KServeInferenceResponse(**response_data)

        with pytest.raises(KServeInvalidResponseError, match="Failed to decode"):
            client._convert_from_kserve_format(kserve_response, 1.0)

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_success(self, mock_request, client):
        """Test successful request without retries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        response = await client._make_request_with_retry(
            "GET", "http://test.com", expected_status=200
        )

        assert response == mock_response
        mock_request.assert_called_once_with("GET", "http://test.com", json=None)

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_connection_error(self, mock_request, client):
        """Test connection error with retries."""
        mock_request.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(KServeConnectionError, match="Failed to connect"):
            await client._make_request_with_retry("GET", "http://test.com")

        # Should have tried max_retries + 1 times
        assert mock_request.call_count == client.max_retries + 1

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_timeout_error(self, mock_request, client):
        """Test timeout error with retries."""
        mock_request.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(KServeTimeoutError, match="Request timed out"):
            await client._make_request_with_retry("GET", "http://test.com")

        assert mock_request.call_count == client.max_retries + 1

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_404_error(self, mock_request, client):
        """Test 404 error (model not ready)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with pytest.raises(KServeModelNotReadyError, match="not found or not ready"):
            await client._make_request_with_retry("GET", "http://test.com")

        # Should not retry for 404
        mock_request.assert_called_once()

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_429_error(self, mock_request, client):
        """Test 429 error (rate limit)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response

        with pytest.raises(KServeRateLimitError, match="Rate limit exceeded"):
            await client._make_request_with_retry("GET", "http://test.com")

        # Should not retry for 429
        mock_request.assert_called_once()

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_server_error_with_json(
        self, mock_request, client
    ):
        """Test server error with JSON error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": "Something went wrong",
        }
        mock_request.return_value = mock_response

        with pytest.raises(KServeInferenceError) as exc_info:
            await client._make_request_with_retry("GET", "http://test.com")

        assert exc_info.value.error_code == "INTERNAL_ERROR"
        assert exc_info.value.details == "Something went wrong"

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_server_error_without_json(
        self, mock_request, client
    ):
        """Test server error without JSON error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(KServeInferenceError, match="Request failed with status 500"):
            await client._make_request_with_retry("GET", "http://test.com")

    @patch("httpx.AsyncClient.request")
    async def test_make_request_with_retry_eventual_success(self, mock_request, client):
        """Test eventual success after retries."""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200

        # Fail twice, then succeed
        mock_request.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            mock_success_response,
        ]

        response = await client._make_request_with_retry("GET", "http://test.com")

        assert response == mock_success_response
        assert mock_request.call_count == 3

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_generate_image_success(self, mock_request, client, mock_response_data):
        """Test successful image generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        result = await client.generate_image(
            prompt="test prompt",
            width=512,
            height=512,
            num_inference_steps=25,
            guidance_scale=7.5,
            seed=42,
        )

        assert isinstance(result.image_data, bytes)
        assert result.generation_time > 0
        assert result.metadata["model_name"] == "stable-diffusion"

        # Verify request was made correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "infer" in args[1]
        assert kwargs["expected_status"] == 200

    async def test_generate_image_validation_errors(self, client):
        """Test validation errors in generate_image."""
        # Empty prompt
        with pytest.raises(KServeValidationError, match="Prompt cannot be empty"):
            await client.generate_image(prompt="")

        # Invalid width
        with pytest.raises(KServeValidationError, match="Width must be between"):
            await client.generate_image(prompt="test", width=32)

        # Invalid height
        with pytest.raises(KServeValidationError, match="Height must be between"):
            await client.generate_image(prompt="test", height=3000)

        # Invalid steps
        with pytest.raises(
            KServeValidationError, match="Number of inference steps must be between"
        ):
            await client.generate_image(prompt="test", num_inference_steps=0)

        # Invalid guidance scale
        with pytest.raises(
            KServeValidationError, match="Guidance scale must be between"
        ):
            await client.generate_image(prompt="test", guidance_scale=0.5)

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_health_check_success(self, mock_request, client):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "stable-diffusion",
            "ready": True,
        }
        mock_request.return_value = mock_response

        result = await client.health_check()

        assert result is True
        mock_request.assert_called_once_with("GET", client._get_ready_url(), expected_status=200)

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_health_check_not_ready(self, mock_request, client):
        """Test health check when model is not ready."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "stable-diffusion",
            "ready": False,
        }
        mock_request.return_value = mock_response

        result = await client.health_check()

        assert result is False

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_health_check_invalid_response(self, mock_request, client):
        """Test health check with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_request.return_value = mock_response

        result = await client.health_check()

        # Should assume healthy if we got 200 but can't parse response
        assert result is True

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_health_check_exception(self, mock_request, client):
        """Test health check with exception."""
        mock_request.side_effect = KServeConnectionError("Connection failed")

        result = await client.health_check()

        assert result is False

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_get_model_metadata_success(self, mock_request, client, mock_metadata_response):
        """Test successful model metadata retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_metadata_response
        mock_request.return_value = mock_response

        result = await client.get_model_metadata()

        assert result is not None
        assert result.name == "stable-diffusion"
        assert result.platform == "diffusers"
        assert "v1.0" in result.versions

        mock_request.assert_called_once_with("GET", client._get_metadata_url(), expected_status=200)

    @patch("src.kserve.client.KServeClient._make_request_with_retry")
    async def test_get_model_metadata_failure(self, mock_request, client):
        """Test model metadata retrieval failure."""
        mock_request.side_effect = KServeConnectionError("Connection failed")

        result = await client.get_model_metadata()

        # Should return None on failure, not raise exception
        assert result is None

    @patch("asyncio.sleep")
    @patch("httpx.AsyncClient.request")
    async def test_exponential_backoff(self, mock_request, mock_sleep, client):
        """Test exponential backoff retry logic."""
        # Set shorter retry settings for testing
        client.max_retries = 3
        client.retry_backoff_factor = 2.0
        client.max_retry_delay = 10.0

        mock_request.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(KServeConnectionError):
            await client._make_request_with_retry("GET", "http://test.com")

        # Check that sleep was called with increasing delays
        expected_delays = [1.0, 2.0, 4.0]  # 2^0, 2^1, 2^2
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    async def test_client_cleanup(self, client):
        """Test client resource cleanup."""
        # Mock the aclose method
        client.client.aclose = AsyncMock()

        await client.close()

        client.client.aclose.assert_called_once()

    @patch("httpx.AsyncClient.request")
    async def test_custom_connection_limits(self, mock_request):
        """Test client with custom connection limits."""
        custom_limits = httpx.Limits(max_keepalive_connections=5, max_connections=50)

        with patch("httpx.AsyncClient") as mock_client_class:
            client = KServeClient(
                endpoint="http://test.com",
                model_name="test-model",
                connection_limits=custom_limits,
            )
            
            # Verify that AsyncClient was called with the custom limits
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args.kwargs["limits"] == custom_limits

    async def test_request_headers(self, client):
        """Test that client sets correct headers."""
        assert client.client.headers["Content-Type"] == "application/json"
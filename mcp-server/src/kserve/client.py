"""KServe client for interacting with inference endpoints."""

import asyncio
import base64
import time
from typing import Any, Dict, Optional

import httpx

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from .exceptions import (
    KServeConnectionError,
    KServeError,
    KServeInferenceError,
    KServeInvalidResponseError,
    KServeModelNotReadyError,
    KServeRateLimitError,
    KServeTimeoutError,
    KServeValidationError,
)
from .models import (
    InternalImageRequest,
    InternalImageResponse,
    KServeErrorResponse,
    KServeInferenceRequest,
    KServeInferenceResponse,
    KServeInstance,
    KServeModelMetadata,
    KServeModelStatus,
)


class KServeClient:
    """Client for interacting with KServe inference endpoints."""

    def __init__(
        self,
        endpoint: str,
        model_name: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        max_retry_delay: float = 60.0,
        connection_limits: Optional[httpx.Limits] = None,
    ):
        """
        Initialize KServe client.

        Args:
            endpoint: Base URL for KServe endpoint
            model_name: Name of the model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Exponential backoff factor for retries
            max_retry_delay: Maximum delay between retries in seconds
            connection_limits: Optional HTTP connection limits
        """
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.max_retry_delay = max_retry_delay

        # Set up HTTP client with connection pooling
        if connection_limits is None:
            connection_limits = httpx.Limits(
                max_keepalive_connections=10, max_connections=100
            )

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=connection_limits,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()

    async def __aenter__(self) -> "KServeClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def _get_inference_url(self) -> str:
        """Get the inference URL for the model."""
        return f"{self.endpoint}/v1/models/{self.model_name}/infer"

    def _get_metadata_url(self) -> str:
        """Get the metadata URL for the model."""
        return f"{self.endpoint}/v1/models/{self.model_name}"

    def _get_ready_url(self) -> str:
        """Get the ready URL for the model."""
        return f"{self.endpoint}/v1/models/{self.model_name}/ready"

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            json_data: Optional JSON data for POST requests
            expected_status: Expected HTTP status code

        Returns:
            HTTP response

        Raises:
            KServeError: If request fails after all retries
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Making request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                )

                response = await self.client.request(method, url, json=json_data)

                # Handle specific HTTP status codes
                if response.status_code == expected_status:
                    return response
                elif response.status_code == 404:
                    raise KServeModelNotReadyError(
                        f"Model {self.model_name} not found or not ready"
                    )
                elif response.status_code == 429:
                    raise KServeRateLimitError("Rate limit exceeded")
                elif response.status_code >= 400:
                    # Try to parse error response
                    try:
                        error_data = response.json()
                        error_response = KServeErrorResponse(**error_data)
                        raise KServeInferenceError(
                            error_response.error,
                            error_code=error_response.code,
                            details=error_response.details,
                        )
                    except Exception:
                        # If we can't parse the error, use the raw response
                        raise KServeInferenceError(
                            f"Request failed with status {response.status_code}: {response.text}"
                        )

            except httpx.ConnectError as e:
                last_exception = KServeConnectionError(
                    f"Failed to connect to KServe endpoint: {str(e)}"
                )
            except httpx.TimeoutException as e:
                last_exception = KServeTimeoutError(
                    f"Request timed out after {self.timeout}s: {str(e)}"
                )
            except (KServeRateLimitError, KServeModelNotReadyError, KServeInferenceError):
                # Don't retry these specific errors
                raise
            except Exception as e:
                last_exception = KServeError(f"Unexpected error: {str(e)}")

            # If this wasn't the last attempt, wait before retrying
            if attempt < self.max_retries:
                delay = min(
                    self.retry_backoff_factor**attempt, self.max_retry_delay
                )
                logger.warning(
                    "Request failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    delay=delay,
                    error=str(last_exception),
                )
                await asyncio.sleep(delay)

        # All retries exhausted, raise the last exception
        if last_exception:
            raise last_exception
        else:
            raise KServeError("Request failed after all retries")

    def _convert_to_kserve_format(
        self, request: InternalImageRequest
    ) -> KServeInferenceRequest:
        """
        Convert internal request format to KServe format.

        Args:
            request: Internal image generation request

        Returns:
            KServe inference request
        """
        instance = KServeInstance(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
        )

        return KServeInferenceRequest(instances=[instance])

    def _convert_from_kserve_format(
        self, response: KServeInferenceResponse, generation_time: float
    ) -> InternalImageResponse:
        """
        Convert KServe response format to internal format.

        Args:
            response: KServe inference response
            generation_time: Time taken for generation

        Returns:
            Internal image response

        Raises:
            KServeInvalidResponseError: If response format is invalid
        """
        if not response.predictions:
            raise KServeInvalidResponseError("No predictions in response")

        prediction = response.predictions[0]

        try:
            # Decode base64 image data
            image_data = base64.b64decode(prediction.image_data)
        except Exception as e:
            raise KServeInvalidResponseError(
                f"Failed to decode base64 image data: {str(e)}"
            )

        # Add model information to metadata
        metadata = prediction.metadata.copy()
        if response.model_name:
            metadata["model_name"] = response.model_name
        if response.model_version:
            metadata["model_version"] = response.model_version

        return InternalImageResponse(
            image_data=image_data,
            metadata=metadata,
            generation_time=generation_time,
        )

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
        """
        Generate an image using the diffusers runtime.

        Args:
            prompt: Text prompt for generation
            negative_prompt: Negative prompt to avoid features
            width: Image width in pixels
            height: Image height in pixels
            num_inference_steps: Number of denoising steps
            guidance_scale: Guidance scale for generation
            seed: Random seed for reproducibility

        Returns:
            Internal image response containing image data and metadata

        Raises:
            KServeValidationError: If parameters are invalid
            KServeError: If generation fails
        """
        # Validate parameters
        if not prompt or not prompt.strip():
            raise KServeValidationError("Prompt cannot be empty")

        if width < 64 or width > 2048:
            raise KServeValidationError("Width must be between 64 and 2048 pixels")

        if height < 64 or height > 2048:
            raise KServeValidationError("Height must be between 64 and 2048 pixels")

        if num_inference_steps < 1 or num_inference_steps > 200:
            raise KServeValidationError(
                "Number of inference steps must be between 1 and 200"
            )

        if guidance_scale < 1.0 or guidance_scale > 20.0:
            raise KServeValidationError("Guidance scale must be between 1.0 and 20.0")

        # Create internal request
        internal_request = InternalImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )

        # Convert to KServe format
        kserve_request = self._convert_to_kserve_format(internal_request)

        logger.info(
            "Generating image",
            prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )

        # Make inference request
        start_time = time.time()
        try:
            response = await self._make_request_with_retry(
                "POST",
                self._get_inference_url(),
                json_data=kserve_request.dict(),
                expected_status=200,
            )
            generation_time = time.time() - start_time

            # Parse response
            response_data = response.json()
            kserve_response = KServeInferenceResponse(**response_data)

            # Convert to internal format
            internal_response = self._convert_from_kserve_format(
                kserve_response, generation_time
            )

            logger.info(
                "Image generated successfully",
                generation_time=generation_time,
                image_size=len(internal_response.image_data),
            )

            return internal_response

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(
                "Image generation failed",
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                generation_time=generation_time,
                error=str(e),
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if the KServe endpoint is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            logger.debug("Performing health check", model_name=self.model_name)

            # Check if model is ready
            response = await self._make_request_with_retry(
                "GET", self._get_ready_url(), expected_status=200
            )

            # Parse response to check ready status
            try:
                status_data = response.json()
                status = KServeModelStatus(**status_data)
                is_healthy = status.ready
            except Exception:
                # If we can't parse the response, assume healthy if we got 200
                is_healthy = True

            logger.debug(
                "Health check completed",
                model_name=self.model_name,
                healthy=is_healthy,
            )

            return is_healthy

        except Exception as e:
            logger.warning(
                "Health check failed",
                model_name=self.model_name,
                error=str(e),
            )
            return False

    async def get_model_metadata(self) -> Optional[KServeModelMetadata]:
        """
        Get metadata for the model.

        Returns:
            Model metadata or None if not available

        Raises:
            KServeError: If metadata request fails
        """
        try:
            logger.debug("Getting model metadata", model_name=self.model_name)

            response = await self._make_request_with_retry(
                "GET", self._get_metadata_url(), expected_status=200
            )

            metadata_data = response.json()
            metadata = KServeModelMetadata(**metadata_data)

            logger.debug(
                "Model metadata retrieved",
                model_name=self.model_name,
                platform=metadata.platform,
            )

            return metadata

        except Exception as e:
            logger.error(
                "Failed to get model metadata",
                model_name=self.model_name,
                error=str(e),
            )
            # Don't raise exception here, metadata is optional
            return None
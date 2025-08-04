"""Request and response models for KServe communication."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KServeInstance(BaseModel):
    """Single instance in a KServe inference request."""

    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(
        None, description="Negative prompt to avoid features"
    )
    width: int = Field(512, ge=64, le=2048, description="Image width in pixels")
    height: int = Field(512, ge=64, le=2048, description="Image height in pixels")
    num_inference_steps: int = Field(
        50, ge=1, le=200, description="Number of denoising steps"
    )
    guidance_scale: float = Field(
        7.5, ge=1.0, le=20.0, description="Guidance scale for generation"
    )
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")

    class Config:
        """Pydantic configuration."""
        
        extra = "allow"  # Allow additional parameters for future extensibility


class KServeInferenceRequest(BaseModel):
    """KServe v1 inference request format."""

    instances: List[KServeInstance] = Field(
        ..., description="List of instances to process", min_items=1, max_items=1
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Optional global parameters"
    )


class KServePrediction(BaseModel):
    """Single prediction in a KServe inference response."""

    image: Optional[Dict[str, str]] = Field(None, description="Image data with b64 field")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    model_name: Optional[str] = Field(None, description="Model name")
    prompt: Optional[str] = Field(None, description="Generation prompt")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Generation metadata"
    )


class KServeInferenceResponse(BaseModel):
    """KServe v1 inference response format."""

    predictions: List[KServePrediction] = Field(
        ..., description="List of predictions", min_items=1
    )
    model_name: Optional[str] = Field(None, description="Name of the model used")
    model_version: Optional[str] = Field(None, description="Version of the model used")


class KServeModelMetadata(BaseModel):
    """KServe model metadata response."""

    name: str = Field(..., description="Model name")
    platform: Optional[str] = Field(None, description="Model platform")
    versions: Optional[List[str]] = Field(None, description="Available model versions")
    inputs: Optional[List[Dict[str, Any]]] = Field(
        None, description="Model input specifications"
    )
    outputs: Optional[List[Dict[str, Any]]] = Field(
        None, description="Model output specifications"
    )


class KServeModelStatus(BaseModel):
    """KServe model status response."""

    name: str = Field(..., description="Model name")
    version: Optional[str] = Field(None, description="Model version")
    ready: bool = Field(..., description="Whether model is ready for inference")


class KServeErrorResponse(BaseModel):
    """KServe error response format."""

    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[str] = Field(None, description="Detailed error information")


class InternalImageRequest(BaseModel):
    """Internal format for image generation requests."""

    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(
        None, description="Negative prompt to avoid features"
    )
    width: int = Field(512, ge=64, le=2048, description="Image width in pixels")
    height: int = Field(512, ge=64, le=2048, description="Image height in pixels")
    num_inference_steps: int = Field(
        50, ge=1, le=200, description="Number of denoising steps"
    )
    guidance_scale: float = Field(
        7.5, ge=1.0, le=20.0, description="Guidance scale for generation"
    )
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class InternalImageResponse(BaseModel):
    """Internal format for image generation responses."""

    image_data: bytes = Field(..., description="Raw image bytes")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Generation metadata"
    )
    generation_time: Optional[float] = Field(
        None, description="Time taken to generate image in seconds"
    )
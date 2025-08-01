"""Configuration settings for the MCP image generation server."""

import os
from typing import Any, Dict, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ConfigurationError(Exception):
    """Configuration is invalid."""

    pass


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""

    # Service Configuration
    service_name: str = Field("mcp-image-server", env="SERVICE_NAME")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    workers: int = Field(4, env="WORKERS")

    # Storage Configuration
    storage_backend: Literal["file", "s3"] = Field("file", env="STORAGE_BACKEND")
    storage_path: str = Field("/tmp/mcp-images", env="STORAGE_PATH")

    # S3 Configuration
    s3_bucket: Optional[str] = Field(None, env="S3_BUCKET")
    s3_prefix: str = Field("mcp-images/", env="S3_PREFIX")
    s3_endpoint_url: Optional[str] = Field(None, env="S3_ENDPOINT_URL")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", env="AWS_REGION")

    # KServe Configuration
    kserve_endpoint: str = Field(..., env="KSERVE_ENDPOINT")
    kserve_model_name: str = Field("stable-diffusion", env="KSERVE_MODEL_NAME")
    kserve_timeout: float = Field(60.0, env="KSERVE_TIMEOUT")
    kserve_max_retries: int = Field(3, env="KSERVE_MAX_RETRIES")

    # Image Management
    image_cleanup_interval: int = Field(300, env="IMAGE_CLEANUP_INTERVAL")
    image_ttl: int = Field(3600, env="IMAGE_TTL")
    max_image_size: int = Field(10485760, env="MAX_IMAGE_SIZE")  # 10MB

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False
        validate_assignment = True

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """Validate worker count is positive."""
        if v < 1:
            raise ValueError("Workers must be at least 1")
        return v

    @field_validator("s3_bucket")
    @classmethod 
    def validate_s3_bucket(cls, v: Optional[str], info) -> Optional[str]:
        """Validate S3 bucket is provided when using S3 storage."""
        values = info.data if info else {}
        if values.get("storage_backend") == "s3" and not v:
            raise ValueError("S3 bucket is required when storage_backend is 's3'")
        return v

    @field_validator("aws_access_key_id")
    @classmethod
    def validate_aws_credentials(cls, v: Optional[str], info) -> Optional[str]:
        """Validate AWS credentials are provided when using S3 storage."""
        values = info.data if info else {}
        if values.get("storage_backend") == "s3":
            if not v:
                raise ValueError(
                    "AWS access key ID is required when storage_backend is 's3'"
                )
            if not values.get("aws_secret_access_key"):
                raise ValueError(
                    "AWS secret access key is required when storage_backend is 's3'"
                )
        return v

    @field_validator("storage_path")
    @classmethod
    def validate_storage_path(cls, v: str, info) -> str:
        """Validate storage path is writable for file storage."""
        values = info.data if info else {}
        if values.get("storage_backend") == "file":
            # Check if we can create the directory
            try:
                os.makedirs(v, exist_ok=True)
            except PermissionError:
                raise ValueError(f"Storage path '{v}' is not writable")
        return v

    @field_validator("kserve_timeout")
    @classmethod
    def validate_kserve_timeout(cls, v: float) -> float:
        """Validate KServe timeout is positive."""
        if v <= 0:
            raise ValueError("KServe timeout must be positive")
        return v

    @field_validator("kserve_max_retries")
    @classmethod
    def validate_kserve_max_retries(cls, v: int) -> int:
        """Validate KServe max retries is non-negative."""
        if v < 0:
            raise ValueError("KServe max retries must be non-negative")
        return v

    @field_validator("image_cleanup_interval")
    @classmethod
    def validate_image_cleanup_interval(cls, v: int) -> int:
        """Validate image cleanup interval is positive."""
        if v <= 0:
            raise ValueError("Image cleanup interval must be positive")
        return v

    @field_validator("image_ttl")
    @classmethod
    def validate_image_ttl(cls, v: int) -> int:
        """Validate image TTL is positive."""
        if v <= 0:
            raise ValueError("Image TTL must be positive")
        return v

    @field_validator("max_image_size")
    @classmethod
    def validate_max_image_size(cls, v: int) -> int:
        """Validate max image size is positive."""
        if v <= 0:
            raise ValueError("Maximum image size must be positive")
        return v

    def get_storage_url(self) -> str:
        """Get the base URL for serving images."""
        return f"http://{self.host}:{self.port}/images"

    def is_s3_configured(self) -> bool:
        """Check if S3 configuration is complete."""
        return (
            self.storage_backend == "s3"
            and self.s3_bucket is not None
            and self.aws_access_key_id is not None
            and self.aws_secret_access_key is not None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary, excluding sensitive values."""
        data = self.dict()
        # Mask sensitive values
        if data.get("aws_secret_access_key"):
            data["aws_secret_access_key"] = "***MASKED***"
        return data
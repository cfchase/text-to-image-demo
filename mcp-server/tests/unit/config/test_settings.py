"""Tests for configuration settings."""

import os
import tempfile
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from config import ConfigurationError, Settings


class TestSettings:
    """Test settings configuration and validation."""

    def test_default_settings(self):
        """Test settings with default values."""
        # Only provide required field
        with patch.dict(os.environ, {"KSERVE_ENDPOINT": "http://test:8080"}):
            settings = Settings()
            
            assert settings.service_name == "mcp-image-server"
            assert settings.log_level == "INFO"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.workers == 4
            assert settings.storage_backend == "file"
            assert settings.storage_path == "/tmp/mcp-images"
            assert settings.kserve_endpoint == "http://test:8080"
            assert settings.kserve_model_name == "stable-diffusion"
            assert settings.kserve_timeout == 60.0
            assert settings.kserve_max_retries == 3

    def test_environment_override(self):
        """Test settings from environment variables."""
        env_vars = {
            "SERVICE_NAME": "test-service",
            "LOG_LEVEL": "DEBUG",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "WORKERS": "8",
            "STORAGE_BACKEND": "file",
            "STORAGE_PATH": "/custom/path",
            "KSERVE_ENDPOINT": "http://kserve:8080",
            "KSERVE_MODEL_NAME": "custom-model",
            "KSERVE_TIMEOUT": "120.0",
            "KSERVE_MAX_RETRIES": "5",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.service_name == "test-service"
            assert settings.log_level == "DEBUG"
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.workers == 8
            assert settings.storage_backend == "file"
            assert settings.storage_path == "/custom/path"
            assert settings.kserve_endpoint == "http://kserve:8080"
            assert settings.kserve_model_name == "custom-model"
            assert settings.kserve_timeout == 120.0
            assert settings.kserve_max_retries == 5

    def test_s3_configuration(self):
        """Test S3 storage configuration."""
        env_vars = {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
            "S3_PREFIX": "images/",
            "S3_ENDPOINT_URL": "http://minio:9000",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_REGION": "us-west-2",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.storage_backend == "s3"
            assert settings.s3_bucket == "test-bucket"
            assert settings.s3_prefix == "images/"
            assert settings.s3_endpoint_url == "http://minio:9000"
            assert settings.aws_access_key_id == "test-key"
            assert settings.aws_secret_access_key == "test-secret"
            assert settings.aws_region == "us-west-2"

    def test_invalid_log_level(self):
        """Test validation of log level."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "LOG_LEVEL": "INVALID"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Log level must be one of" in str(exc_info.value)

    def test_invalid_port(self):
        """Test validation of port number."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "PORT": "70000"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_invalid_workers(self):
        """Test validation of worker count."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "WORKERS": "0"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Workers must be at least 1" in str(exc_info.value)

    def test_s3_backend_requires_bucket(self):
        """Test that S3 backend requires bucket configuration."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "S3 bucket is required" in str(exc_info.value)

    def test_s3_backend_requires_credentials(self):
        """Test that S3 backend requires AWS credentials."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "AWS access key ID is required" in str(exc_info.value)

    def test_s3_backend_requires_secret_key(self):
        """Test that S3 backend requires secret access key."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
            "AWS_ACCESS_KEY_ID": "test-key",
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "AWS secret access key is required" in str(exc_info.value)

    def test_file_storage_path_validation(self):
        """Test validation of file storage path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {
                "KSERVE_ENDPOINT": "http://test:8080",
                "STORAGE_BACKEND": "file",
                "STORAGE_PATH": tmp_dir,
            }):
                settings = Settings()
                assert settings.storage_path == tmp_dir

    def test_invalid_kserve_timeout(self):
        """Test validation of KServe timeout."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "KSERVE_TIMEOUT": "-5.0"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "KServe timeout must be positive" in str(exc_info.value)

    def test_invalid_kserve_max_retries(self):
        """Test validation of KServe max retries."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "KSERVE_MAX_RETRIES": "-1"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "KServe max retries must be non-negative" in str(exc_info.value)

    def test_invalid_cleanup_interval(self):
        """Test validation of image cleanup interval."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "IMAGE_CLEANUP_INTERVAL": "0"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Image cleanup interval must be positive" in str(exc_info.value)

    def test_invalid_image_ttl(self):
        """Test validation of image TTL."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "IMAGE_TTL": "0"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Image TTL must be positive" in str(exc_info.value)

    def test_invalid_max_image_size(self):
        """Test validation of max image size."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "MAX_IMAGE_SIZE": "0"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Maximum image size must be positive" in str(exc_info.value)

    def test_get_storage_url(self):
        """Test storage URL generation."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "HOST": "example.com",
            "PORT": "9000"
        }):
            settings = Settings()
            assert settings.get_storage_url() == "http://example.com:9000/images"

    def test_is_s3_configured_true(self):
        """Test S3 configuration check when properly configured."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
        }):
            settings = Settings()
            assert settings.is_s3_configured() is True

    def test_is_s3_configured_false_file_backend(self):
        """Test S3 configuration check with file backend."""
        with patch.dict(os.environ, {"KSERVE_ENDPOINT": "http://test:8080"}):
            settings = Settings()
            assert settings.is_s3_configured() is False

    def test_is_s3_configured_false_missing_credentials(self):
        """Test S3 configuration check with missing credentials."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
        }):
            # This will fail validation, but we can test the method logic
            try:
                settings = Settings()
                assert settings.is_s3_configured() is False
            except ValidationError:
                # Expected due to missing credentials
                pass

    def test_to_dict_masks_secrets(self):
        """Test that to_dict masks sensitive values."""
        with patch.dict(os.environ, {
            "KSERVE_ENDPOINT": "http://test:8080",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "test-bucket",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "secret-value",
        }):
            settings = Settings()
            data = settings.to_dict()
            
            assert data["aws_access_key_id"] == "test-key"
            assert data["aws_secret_access_key"] == "***MASKED***"

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        with patch.dict(os.environ, {
            "kserve_endpoint": "http://test:8080",
            "log_level": "debug",
        }):
            settings = Settings()
            assert settings.kserve_endpoint == "http://test:8080"
            assert settings.log_level == "DEBUG"

    def test_missing_required_kserve_endpoint(self):
        """Test that missing KServe endpoint raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "field required" in str(exc_info.value)

    def test_env_file_support(self):
        """Test that .env file is supported."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KSERVE_ENDPOINT=http://env-file:8080\n")
            f.write("SERVICE_NAME=env-service\n")
            env_file = f.name
        
        try:
            # Change working directory context for .env file
            original_cwd = os.getcwd()
            env_dir = os.path.dirname(env_file)
            env_filename = os.path.basename(env_file)
            
            os.chdir(env_dir)
            os.rename(env_filename, '.env')
            
            settings = Settings()
            assert settings.kserve_endpoint == "http://env-file:8080"
            assert settings.service_name == "env-service"
            
        finally:
            os.chdir(original_cwd)
            # Clean up
            env_file_path = os.path.join(env_dir, '.env')
            if os.path.exists(env_file_path):
                os.unlink(env_file_path)
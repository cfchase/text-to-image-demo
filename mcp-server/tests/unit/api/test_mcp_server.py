"""Tests for MCP server functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.api.mcp_server import (
    GenerateImageParams,
    GenerateImageResponse,
    ImageGenerationError,
    MCPImageError,
    MCPImageServer,
    StorageError,
    ValidationError,
    create_mcp_server,
)
from mcp_server.config.settings import Settings
from mcp_server.kserve.exceptions import KServeError, KServeValidationError
from mcp_server.kserve.models import InternalImageResponse
from mcp_server.storage.base import AbstractStorage, StorageError as BaseStorageError
from mcp_server.utils.images import ImageValidationError


class TestGenerateImageParams:
    """Test GenerateImageParams validation."""
    
    def test_valid_params(self):
        """Test valid parameter creation."""
        params = GenerateImageParams(
            prompt="a beautiful sunset",
            negative_prompt="blurry",
            width=512,
            height=512,
            num_inference_steps=50,
            guidance_scale=7.5,
            seed=42,
        )
        
        assert params.prompt == "a beautiful sunset"
        assert params.negative_prompt == "blurry"
        assert params.width == 512
        assert params.height == 512
        assert params.num_inference_steps == 50
        assert params.guidance_scale == 7.5
        assert params.seed == 42
    
    def test_default_values(self):
        """Test default parameter values."""
        params = GenerateImageParams(prompt="sunset")
        
        assert params.prompt == "sunset"
        assert params.negative_prompt is None
        assert params.width == 512
        assert params.height == 512
        assert params.num_inference_steps == 50
        assert params.guidance_scale == 7.5
        assert params.seed is None
    
    def test_invalid_prompt_empty(self):
        """Test validation of empty prompt."""
        with pytest.raises(ValueError, match="at least 1 character"):
            GenerateImageParams(prompt="")
    
    def test_invalid_prompt_too_long(self):
        """Test validation of overly long prompt."""
        long_prompt = "a" * 1001
        with pytest.raises(ValueError, match="at most 1000 characters"):
            GenerateImageParams(prompt=long_prompt)
    
    def test_invalid_dimensions(self):
        """Test validation of invalid dimensions."""
        # Width too small
        with pytest.raises(ValueError, match="greater than or equal to 64"):
            GenerateImageParams(prompt="test", width=32)
        
        # Height too large
        with pytest.raises(ValueError, match="less than or equal to 2048"):
            GenerateImageParams(prompt="test", height=4096)
    
    def test_invalid_steps(self):
        """Test validation of invalid inference steps."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            GenerateImageParams(prompt="test", num_inference_steps=0)
        
        with pytest.raises(ValueError, match="less than or equal to 200"):
            GenerateImageParams(prompt="test", num_inference_steps=300)
    
    def test_invalid_guidance_scale(self):
        """Test validation of invalid guidance scale."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            GenerateImageParams(prompt="test", guidance_scale=0.5)
        
        with pytest.raises(ValueError, match="less than or equal to 20"):
            GenerateImageParams(prompt="test", guidance_scale=25.0)


class TestMCPImageServer:
    """Test MCPImageServer functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.service_name = "test-server"
        settings.kserve_endpoint = "http://test-kserve:8080"
        settings.storage_backend = "file"
        settings.max_image_size = 10485760
        settings.get_storage_url.return_value = "http://localhost:8000/images"
        return settings
    
    @pytest.fixture
    def mock_kserve_client(self):
        """Mock KServe client for testing."""
        client = AsyncMock()
        client.generate_image.return_value = InternalImageResponse(
            image_data=b"fake_image_data",
            metadata={
                "prompt": "test prompt",
                "width": 512,
                "height": 512,
                "model_name": "test-model",
                "generation_time": 2.5,
            },
            generation_time=2.5,
        )
        client.health_check.return_value = True
        client.close = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock(spec=AbstractStorage)
        storage.save_image.return_value = "/path/to/image.png"
        storage.get_image_url.return_value = "http://localhost:8000/images/test-id"
        storage.list_images.return_value = []
        return storage
    
    @pytest.fixture
    def mcp_server(self, mock_settings, mock_kserve_client, mock_storage):
        """Create MCP server for testing."""
        return MCPImageServer(
            settings=mock_settings,
            kserve_client=mock_kserve_client,
            storage=mock_storage,
        )
    
    def test_initialization(self, mcp_server, mock_settings, mock_kserve_client, mock_storage):
        """Test MCP server initialization."""
        assert mcp_server.settings == mock_settings
        assert mcp_server.kserve_client == mock_kserve_client
        assert mcp_server.storage == mock_storage
        assert mcp_server.app is not None
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self, mcp_server, mock_kserve_client, mock_storage):
        """Test successful image generation."""
        params = GenerateImageParams(
            prompt="a beautiful sunset",
            width=512,
            height=512,
        )
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
             patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
            
            mock_id_gen.return_value = "test-image-id"
            mock_validate.return_value = None
            
            result = await mcp_server.generate_image(params)
            
            # Verify KServe was called correctly
            mock_kserve_client.generate_image.assert_called_once_with(
                prompt="a beautiful sunset",
                negative_prompt=None,
                width=512,
                height=512,
                num_inference_steps=50,
                guidance_scale=7.5,
                seed=None,
            )
            
            # Verify storage was called
            mock_storage.save_image.assert_called_once()
            mock_storage.get_image_url.assert_called_once_with("test-image-id")
            
            # Verify response
            assert isinstance(result, GenerateImageResponse)
            assert result.image_id == "test-image-id"
            assert result.url == "http://localhost:8000/images/test-id"
            assert "prompt" in result.metadata
    
    @pytest.mark.asyncio
    async def test_generate_image_validation_error(self, mcp_server):
        """Test image generation with validation error."""
        params = GenerateImageParams(prompt="   ")  # Whitespace only
        
        with pytest.raises(ValidationError, match="Prompt cannot be empty"):
            await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_dimensions_too_large(self, mcp_server):
        """Test image generation with dimensions too large."""
        params = GenerateImageParams(
            prompt="test",
            width=2048,
            height=2048,  # 4,194,304 pixels exactly at limit
        )
        
        # This should pass
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
             patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
            
            mock_id_gen.return_value = "test-id"
            mock_validate.return_value = None
            
            result = await mcp_server.generate_image(params)
            assert result is not None
        
        # This should fail (over limit)
        params.width = 2049
        with pytest.raises(ValidationError, match="Image dimensions too large"):
            await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_invalid_seed(self, mcp_server):
        """Test image generation with invalid seed."""
        params = GenerateImageParams(
            prompt="test",
            seed=-1,  # Invalid seed
        )
        
        with pytest.raises(ValidationError, match="Seed must be between"):
            await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_kserve_error(self, mcp_server, mock_kserve_client):
        """Test image generation with KServe error."""
        params = GenerateImageParams(prompt="test")
        
        mock_kserve_client.generate_image.side_effect = KServeError("KServe failed")
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen:
            mock_id_gen.return_value = "test-id"
            
            with pytest.raises(ImageGenerationError, match="Image generation failed"):
                await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_validation_error_from_kserve(self, mcp_server, mock_kserve_client):
        """Test image generation with validation error from KServe."""
        params = GenerateImageParams(prompt="test")
        
        mock_kserve_client.generate_image.side_effect = KServeValidationError("Invalid parameters")
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen:
            mock_id_gen.return_value = "test-id"
            
            with pytest.raises(ImageGenerationError, match="Image generation failed"):
                await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_invalid_generated_image(self, mcp_server, mock_kserve_client):
        """Test image generation with invalid generated image."""
        params = GenerateImageParams(prompt="test")
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
             patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
            
            mock_id_gen.return_value = "test-id"
            mock_validate.side_effect = ImageValidationError("Invalid image format")
            
            with pytest.raises(ValidationError, match="Generated image validation failed"):
                await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_storage_error(self, mcp_server, mock_storage):
        """Test image generation with storage error."""
        params = GenerateImageParams(prompt="test")
        
        mock_storage.save_image.side_effect = BaseStorageError("Storage failed")
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
             patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
            
            mock_id_gen.return_value = "test-id"
            mock_validate.return_value = None
            
            with pytest.raises(StorageError, match="Failed to store image"):
                await mcp_server.generate_image(params)
    
    @pytest.mark.asyncio
    async def test_generate_image_storage_url_fallback(self, mcp_server, mock_storage, mock_settings):
        """Test image generation with storage URL fallback."""
        params = GenerateImageParams(prompt="test")
        
        # Storage returns None for URL, should fallback to constructed URL
        mock_storage.get_image_url.return_value = None
        
        with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
             patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
            
            mock_id_gen.return_value = "test-image-id"
            mock_validate.return_value = None
            
            result = await mcp_server.generate_image(params)
            
            # Should use fallback URL construction
            assert result.url == "http://localhost:8000/images/test-image-id"
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, mcp_server, mock_kserve_client, mock_storage):
        """Test health check when all components are healthy."""
        mock_kserve_client.health_check.return_value = True
        mock_storage.list_images.return_value = []
        
        with patch("mcp_server.api.mcp_server.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            result = await mcp_server.health_check()
            
            assert result["service"] == "healthy"
            assert result["kserve"] == "healthy"
            assert result["storage"] == "healthy"
            assert result["timestamp"] == "2024-01-01T12:00:00Z"
    
    @pytest.mark.asyncio
    async def test_health_check_kserve_unhealthy(self, mcp_server, mock_kserve_client, mock_storage):
        """Test health check when KServe is unhealthy."""
        mock_kserve_client.health_check.return_value = False
        mock_storage.list_images.return_value = []
        
        result = await mcp_server.health_check()
        
        assert result["service"] == "degraded"
        assert result["kserve"] == "unhealthy"
        assert result["storage"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_storage_error(self, mcp_server, mock_kserve_client, mock_storage):
        """Test health check when storage has error."""
        mock_kserve_client.health_check.return_value = True
        mock_storage.list_images.side_effect = Exception("Storage error")
        
        result = await mcp_server.health_check()
        
        assert result["service"] == "degraded"
        assert result["kserve"] == "healthy"
        assert result["storage"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_kserve_error(self, mcp_server, mock_kserve_client, mock_storage):
        """Test health check when KServe throws error."""
        mock_kserve_client.health_check.side_effect = Exception("KServe error")
        mock_storage.list_images.return_value = []
        
        result = await mcp_server.health_check()
        
        assert result["service"] == "degraded"
        assert result["kserve"] == "unhealthy"
        assert result["storage"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_close(self, mcp_server, mock_kserve_client):
        """Test MCP server close."""
        await mcp_server.close()
        
        mock_kserve_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_with_error(self, mcp_server, mock_kserve_client):
        """Test MCP server close with error."""
        mock_kserve_client.close.side_effect = Exception("Close error")
        
        # Should not raise exception
        await mcp_server.close()
        
        mock_kserve_client.close.assert_called_once()
    
    def test_get_app(self, mcp_server):
        """Test getting FastMCP app."""
        app = mcp_server.get_app()
        assert app is not None
        assert app == mcp_server.app


class TestCreateMCPServer:
    """Test MCP server factory function."""
    
    def test_create_mcp_server(self):
        """Test creating MCP server via factory."""
        settings = MagicMock(spec=Settings)
        kserve_client = AsyncMock()
        storage = AsyncMock(spec=AbstractStorage)
        
        server = create_mcp_server(
            settings=settings,
            kserve_client=kserve_client, 
            storage=storage,
        )
        
        assert isinstance(server, MCPImageServer)
        assert server.settings == settings
        assert server.kserve_client == kserve_client
        assert server.storage == storage


class TestMCPExceptions:
    """Test MCP-specific exceptions."""
    
    def test_mcp_image_error(self):
        """Test base MCPImageError."""
        error = MCPImageError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, MCPImageError)
    
    def test_image_generation_error(self):
        """Test ImageGenerationError."""
        error = ImageGenerationError("Generation failed")
        assert str(error) == "Generation failed"
        assert isinstance(error, MCPImageError)
    
    def test_storage_error(self):
        """Test StorageError."""
        error = StorageError("Storage failed")
        assert str(error) == "Storage failed"
        assert isinstance(error, MCPImageError)


class TestGenerateImageResponse:
    """Test GenerateImageResponse model."""
    
    def test_valid_response(self):
        """Test valid response creation."""
        response = GenerateImageResponse(
            url="http://example.com/image.png",
            image_id="test-id",
            metadata={"prompt": "test"},
        )
        
        assert response.url == "http://example.com/image.png"
        assert response.image_id == "test-id"
        assert response.metadata == {"prompt": "test"}
    
    def test_response_serialization(self):
        """Test response serialization."""
        response = GenerateImageResponse(
            url="http://example.com/image.png",
            image_id="test-id",
            metadata={"prompt": "test", "width": 512},
        )
        
        data = response.dict()
        
        assert data["url"] == "http://example.com/image.png"
        assert data["image_id"] == "test-id"
        assert data["metadata"]["prompt"] == "test"
        assert data["metadata"]["width"] == 512


@pytest.mark.integration
class TestMCPServerIntegration:
    """Integration tests for MCP server."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, test_settings, sample_image_data, sample_image_metadata):
        """Test full image generation workflow."""
        # Create mock components
        mock_kserve_client = AsyncMock()
        mock_kserve_client.generate_image.return_value = InternalImageResponse(
            image_data=sample_image_data,
            metadata=sample_image_metadata,
            generation_time=2.5,
        )
        mock_kserve_client.health_check.return_value = True
        mock_kserve_client.close = AsyncMock()
        
        mock_storage = AsyncMock()
        mock_storage.save_image.return_value = "/path/to/image.png"
        mock_storage.get_image_url.return_value = "http://localhost:8000/images/test-id"
        mock_storage.list_images.return_value = []
        
        # Create server
        server = MCPImageServer(
            settings=test_settings,
            kserve_client=mock_kserve_client,
            storage=mock_storage,
        )
        
        try:
            # Test image generation
            params = GenerateImageParams(
                prompt="a beautiful landscape",
                width=512,
                height=512,
            )
            
            with patch("mcp_server.api.mcp_server.generate_image_id") as mock_id_gen, \
                 patch("mcp_server.api.mcp_server.validate_image") as mock_validate:
                
                mock_id_gen.return_value = "integration-test-id"
                mock_validate.return_value = None
                
                result = await server.generate_image(params)
                
                assert isinstance(result, GenerateImageResponse)
                assert result.image_id == "integration-test-id"
                assert result.url == "http://localhost:8000/images/test-id"
                assert "prompt" in result.metadata
            
            # Test health check
            health = await server.health_check()
            assert health["service"] == "healthy"
            
        finally:
            # Cleanup
            await server.close()
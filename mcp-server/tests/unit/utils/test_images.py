"""Tests for image utilities."""

import base64
import io
from unittest.mock import Mock, patch

import pytest

from mcp_server.utils.images import (
    FORMAT_EXTENSIONS,
    FORMAT_MIME_TYPES,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_FORMATS,
    SUPPORTED_MIME_TYPES,
    ImageFormatError,
    ImageSizeError,
    ImageValidationError,
    create_image_filename,
    decode_image_base64,
    detect_image_format,
    encode_image_base64,
    format_file_size,
    get_file_extension,
    get_image_dimensions,
    get_mime_type,
    validate_image,
    validate_image_dimensions,
    validate_image_format,
    validate_image_size,
)


# Test image data (minimal valid headers)
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24  # Minimal PNG with IHDR
JPEG_HEADER = b"\xff\xd8\xff" + b"\x00" * 20
WEBP_HEADER = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 16
INVALID_HEADER = b"\x00\x01\x02\x03" + b"\x00" * 20

# Create more complete test images
def create_png_data(width=100, height=100):
    """Create minimal valid PNG data."""
    header = b"\x89PNG\r\n\x1a\n"
    # IHDR chunk
    ihdr = b"IHDR"
    ihdr += width.to_bytes(4, "big")  # width
    ihdr += height.to_bytes(4, "big")  # height
    ihdr += b"\x08\x02\x00\x00\x00"  # bit_depth, color_type, compression, filter, interlace
    
    # Calculate CRC (simplified - not actual CRC32)
    crc = b"\x00\x00\x00\x00"
    
    chunk = len(ihdr[4:]).to_bytes(4, "big") + ihdr + crc
    return header + chunk + b"IEND\xaeB`\x82"  # Minimal end chunk

def create_jpeg_data():
    """Create minimal valid JPEG data."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
        b"\xff\xc0\x00\x11\x08\x00\x64\x00\x64\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
        b"\xff\xd9"
    )

def create_webp_data():
    """Create minimal valid WebP data."""
    return b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


class TestImageFormatDetection:
    """Test image format detection."""

    def test_detect_png_format(self):
        """Test PNG format detection."""
        png_data = create_png_data()
        assert detect_image_format(png_data) == "PNG"

    def test_detect_jpeg_format(self):
        """Test JPEG format detection."""
        jpeg_data = create_jpeg_data()
        assert detect_image_format(jpeg_data) == "JPEG"

    def test_detect_webp_format(self):
        """Test WebP format detection."""
        webp_data = create_webp_data()
        assert detect_image_format(webp_data) == "WEBP"

    def test_detect_unknown_format(self):
        """Test unknown format detection."""
        assert detect_image_format(INVALID_HEADER) is None

    def test_detect_empty_data(self):
        """Test format detection with empty data."""
        assert detect_image_format(b"") is None

    def test_detect_insufficient_data(self):
        """Test format detection with insufficient data."""
        assert detect_image_format(b"\x89PNG") is None  # Too short for PNG


class TestImageFormatValidation:
    """Test image format validation."""

    def test_validate_png_format(self):
        """Test PNG format validation."""
        png_data = create_png_data()
        assert validate_image_format(png_data) == "PNG"

    def test_validate_jpeg_format(self):
        """Test JPEG format validation."""
        jpeg_data = create_jpeg_data()
        assert validate_image_format(jpeg_data) == "JPEG"

    def test_validate_webp_format(self):
        """Test WebP format validation."""
        webp_data = create_webp_data()
        assert validate_image_format(webp_data) == "WEBP"

    def test_validate_with_allowed_formats(self):
        """Test format validation with specific allowed formats."""
        png_data = create_png_data()
        
        # Should pass with PNG in allowed formats
        assert validate_image_format(png_data, ["PNG", "JPEG"]) == "PNG"
        
        # Should fail with PNG not in allowed formats
        with pytest.raises(ImageFormatError, match="Unsupported image format"):
            validate_image_format(png_data, ["JPEG", "WEBP"])

    def test_validate_unknown_format_raises_error(self):
        """Test that unknown format raises error."""
        with pytest.raises(ImageFormatError, match="Unable to detect image format"):
            validate_image_format(INVALID_HEADER)

    def test_validate_empty_data_raises_error(self):
        """Test that empty data raises error."""
        with pytest.raises(ImageFormatError, match="Unable to detect image format"):
            validate_image_format(b"")


class TestImageSizeValidation:
    """Test image size validation."""

    def test_validate_size_within_limit(self):
        """Test size validation within limit."""
        data = b"test image data"
        size = validate_image_size(data, max_size=100)
        assert size == len(data)

    def test_validate_size_exceeds_limit(self):
        """Test size validation exceeding limit."""
        data = b"x" * 100
        with pytest.raises(ImageSizeError, match="exceeds maximum"):
            validate_image_size(data, max_size=50)

    def test_validate_size_at_limit(self):
        """Test size validation at exact limit."""
        data = b"x" * 50
        size = validate_image_size(data, max_size=50)
        assert size == 50


class TestImageDimensions:
    """Test image dimension extraction."""

    def test_get_png_dimensions(self):
        """Test PNG dimension extraction."""
        png_data = create_png_data(width=200, height=150)
        dimensions = get_image_dimensions(png_data)
        assert dimensions == (200, 150)

    def test_get_dimensions_with_pil_mock(self):
        """Test dimension extraction with PIL mock."""
        test_data = b"fake image data"
        
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (300, 200)
        
        with patch('mcp_server.utils.images.Image') as mock_pil:
            mock_pil.open.return_value.__enter__.return_value = mock_image
            
            dimensions = get_image_dimensions(test_data)
            assert dimensions == (300, 200)

    def test_get_dimensions_invalid_data(self):
        """Test dimension extraction with invalid data."""
        dimensions = get_image_dimensions(INVALID_HEADER)
        assert dimensions is None

    def test_get_dimensions_empty_data(self):
        """Test dimension extraction with empty data."""
        dimensions = get_image_dimensions(b"")
        assert dimensions is None

    def test_validate_dimensions_within_limits(self):
        """Test dimension validation within limits."""
        png_data = create_png_data(width=100, height=100)
        dimensions = validate_image_dimensions(png_data, max_width=200, max_height=200)
        assert dimensions == (100, 100)

    def test_validate_dimensions_width_exceeds(self):
        """Test dimension validation with width exceeding limit."""
        png_data = create_png_data(width=300, height=100)
        with pytest.raises(ImageSizeError, match="Image width 300 exceeds maximum 200"):
            validate_image_dimensions(png_data, max_width=200, max_height=200)

    def test_validate_dimensions_height_exceeds(self):
        """Test dimension validation with height exceeding limit."""
        png_data = create_png_data(width=100, height=300)
        with pytest.raises(ImageSizeError, match="Image height 300 exceeds maximum 200"):
            validate_image_dimensions(png_data, max_width=200, max_height=200)

    def test_validate_dimensions_unknown_size(self):
        """Test dimension validation with unknown dimensions."""
        with pytest.raises(ImageSizeError, match="Unable to determine image dimensions"):
            validate_image_dimensions(INVALID_HEADER)


class TestBase64Encoding:
    """Test base64 encoding/decoding."""

    def test_encode_image_base64(self):
        """Test base64 encoding."""
        data = b"test image data"
        encoded = encode_image_base64(data)
        
        assert isinstance(encoded, str)
        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert decoded == data

    def test_decode_image_base64(self):
        """Test base64 decoding."""
        data = b"test image data"
        encoded = base64.b64encode(data).decode("utf-8")
        
        decoded = decode_image_base64(encoded)
        assert decoded == data

    def test_decode_invalid_base64(self):
        """Test base64 decoding with invalid data."""
        with pytest.raises(ValueError, match="Invalid base64 data"):
            decode_image_base64("invalid-base64!")


class TestMimeTypes:
    """Test MIME type and extension utilities."""

    def test_get_mime_type_valid(self):
        """Test getting MIME type for valid formats."""
        assert get_mime_type("PNG") == "image/png"
        assert get_mime_type("JPEG") == "image/jpeg"
        assert get_mime_type("WEBP") == "image/webp"

    def test_get_mime_type_invalid(self):
        """Test getting MIME type for invalid format."""
        with pytest.raises(ValueError, match="Unsupported image format"):
            get_mime_type("INVALID")

    def test_get_file_extension_valid(self):
        """Test getting file extension for valid formats."""
        assert get_file_extension("PNG") == ".png"
        assert get_file_extension("JPEG") == ".jpg"
        assert get_file_extension("WEBP") == ".webp"

    def test_get_file_extension_invalid(self):
        """Test getting file extension for invalid format."""
        with pytest.raises(ValueError, match="Unsupported image format"):
            get_file_extension("INVALID")

    def test_create_image_filename(self):
        """Test creating image filename."""
        assert create_image_filename("img123", "PNG") == "img123.png"
        assert create_image_filename("photo", "JPEG") == "photo.jpg"
        assert create_image_filename("test", "WEBP") == "test.webp"


class TestComprehensiveValidation:
    """Test comprehensive image validation."""

    def test_validate_image_success(self):
        """Test successful comprehensive image validation."""
        png_data = create_png_data(width=100, height=100)
        
        result = validate_image(
            png_data,
            max_size=1000,
            max_width=200,
            max_height=200,
            allowed_formats=["PNG", "JPEG"]
        )
        
        assert result["format"] == "PNG"
        assert result["size"] == len(png_data)
        assert result["dimensions"] == (100, 100)
        assert result["mime_type"] == "image/png"
        assert result["extension"] == ".png"

    def test_validate_image_empty_data(self):
        """Test validation with empty image data."""
        with pytest.raises(ImageValidationError, match="Empty image data"):
            validate_image(b"")

    def test_validate_image_size_exceeds(self):
        """Test validation with size exceeding limit."""
        png_data = create_png_data()
        
        with pytest.raises(ImageSizeError):
            validate_image(png_data, max_size=10)

    def test_validate_image_dimensions_exceed(self):
        """Test validation with dimensions exceeding limits."""
        png_data = create_png_data(width=300, height=200)
        
        with pytest.raises(ImageSizeError):
            validate_image(png_data, max_width=100, max_height=100)

    def test_validate_image_unsupported_format(self):
        """Test validation with unsupported format."""
        png_data = create_png_data()
        
        with pytest.raises(ImageFormatError):
            validate_image(png_data, allowed_formats=["JPEG", "WEBP"])


class TestFormatFileSize:
    """Test file size formatting."""

    def test_format_zero_bytes(self):
        """Test formatting zero bytes."""
        assert format_file_size(0) == "0 B"

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(500) == "500 B"
        assert format_file_size(1023) == "1023 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(2048) == "2.0 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1024 * 1024 * 1024 * 1.5) == "1.5 GB"

    def test_format_large_sizes(self):
        """Test formatting very large sizes."""
        # Should cap at GB
        very_large = 1024 * 1024 * 1024 * 1024  # 1 TB
        result = format_file_size(very_large)
        assert "GB" in result


class TestConstants:
    """Test module constants."""

    def test_supported_formats(self):
        """Test supported formats constant."""
        assert "PNG" in SUPPORTED_FORMATS
        assert "JPEG" in SUPPORTED_FORMATS
        assert "WEBP" in SUPPORTED_FORMATS

    def test_supported_extensions(self):
        """Test supported extensions constant."""
        assert ".png" in SUPPORTED_EXTENSIONS
        assert ".jpg" in SUPPORTED_EXTENSIONS
        assert ".jpeg" in SUPPORTED_EXTENSIONS
        assert ".webp" in SUPPORTED_EXTENSIONS

    def test_supported_mime_types(self):
        """Test supported MIME types constant."""
        assert "image/png" in SUPPORTED_MIME_TYPES
        assert "image/jpeg" in SUPPORTED_MIME_TYPES
        assert "image/webp" in SUPPORTED_MIME_TYPES

    def test_format_mappings(self):
        """Test format mapping constants."""
        assert FORMAT_EXTENSIONS["PNG"] == ".png"
        assert FORMAT_EXTENSIONS["JPEG"] == ".jpg"
        assert FORMAT_EXTENSIONS["WEBP"] == ".webp"
        
        assert FORMAT_MIME_TYPES["PNG"] == "image/png"
        assert FORMAT_MIME_TYPES["JPEG"] == "image/jpeg"
        assert FORMAT_MIME_TYPES["WEBP"] == "image/webp"


class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_exception_inheritance(self):
        """Test that custom exceptions inherit properly."""
        assert issubclass(ImageFormatError, ImageValidationError)
        assert issubclass(ImageSizeError, ImageValidationError)
        assert issubclass(ImageValidationError, Exception)

    def test_exception_messages(self):
        """Test exception messages."""
        try:
            raise ImageFormatError("Test format error")
        except ImageFormatError as e:
            assert str(e) == "Test format error"
        
        try:
            raise ImageSizeError("Test size error")
        except ImageSizeError as e:
            assert str(e) == "Test size error"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_small_image_data(self):
        """Test with very small image data."""
        small_data = b"\x89PNG"  # Too small to be valid
        assert detect_image_format(small_data) is None

    def test_corrupted_png_header(self):
        """Test with corrupted PNG header."""
        corrupted_png = b"\x89PNG\r\n\x1a\n" + b"\xff" * 100  # Wrong data after header
        # Should still detect as PNG based on header
        assert detect_image_format(corrupted_png) == "PNG"

    def test_jpeg_with_different_markers(self):
        """Test JPEG detection with different markers."""
        jpeg_variants = [
            b"\xff\xd8\xff\xe0",  # JFIF
            b"\xff\xd8\xff\xe1",  # EXIF
            b"\xff\xd8\xff\xdb",  # Quantization table
        ]
        
        for variant in jpeg_variants:
            data = variant + b"\x00" * 20
            assert detect_image_format(data) == "JPEG"

    def test_webp_different_formats(self):
        """Test WebP detection with different internal formats."""
        # Test different WebP chunk types (would need more complex data for full test)
        webp_data = b"RIFF\x20\x00\x00\x00WEBPVP8L\x00\x00\x00\x00" + b"\x00" * 16
        assert detect_image_format(webp_data) == "WEBP"
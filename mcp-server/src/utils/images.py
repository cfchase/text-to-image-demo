"""Image format validation and utility functions."""

import base64
import io
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Image format constants
SUPPORTED_FORMATS = ["PNG", "JPEG", "WEBP"]
SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
SUPPORTED_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"]

# Format to extension mapping
FORMAT_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
}

# Format to MIME type mapping
FORMAT_MIME_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


class ImageValidationError(Exception):
    """Image validation failed."""

    pass


class ImageFormatError(ImageValidationError):
    """Unsupported image format."""

    pass


class ImageSizeError(ImageValidationError):
    """Image size validation failed."""

    pass


def detect_image_format(image_data: bytes) -> Optional[str]:
    """
    Detect image format from binary data by examining magic bytes.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Image format string (PNG, JPEG, WEBP) or None if unknown
    """
    if not image_data:
        return None
    
    # Check for PNG signature
    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    
    # Check for JPEG signature
    if image_data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    
    # Check for WebP signature
    if (
        len(image_data) >= 12
        and image_data[:4] == b"RIFF"
        and image_data[8:12] == b"WEBP"
    ):
        return "WEBP"
    
    return None


def validate_image_format(image_data: bytes, allowed_formats: List[str] = None) -> str:
    """
    Validate image format and return the detected format.
    
    Args:
        image_data: Raw image bytes
        allowed_formats: List of allowed formats (defaults to SUPPORTED_FORMATS)
        
    Returns:
        Detected image format
        
    Raises:
        ImageFormatError: If format is invalid or unsupported
    """
    if allowed_formats is None:
        allowed_formats = SUPPORTED_FORMATS
    
    detected_format = detect_image_format(image_data)
    
    if detected_format is None:
        raise ImageFormatError("Unable to detect image format")
    
    if detected_format not in allowed_formats:
        raise ImageFormatError(
            f"Unsupported image format: {detected_format}. "
            f"Allowed formats: {', '.join(allowed_formats)}"
        )
    
    return detected_format


def validate_image_size(image_data: bytes, max_size: int) -> int:
    """
    Validate image size in bytes.
    
    Args:
        image_data: Raw image bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        Actual image size in bytes
        
    Raises:
        ImageSizeError: If image is too large
    """
    actual_size = len(image_data)
    
    if actual_size > max_size:
        raise ImageSizeError(
            f"Image size {actual_size} bytes exceeds maximum {max_size} bytes"
        )
    
    return actual_size


def get_image_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
    """
    Extract image dimensions from binary data without loading the full image.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Tuple of (width, height) or None if unable to determine
    """
    try:
        # Try to use PIL if available for accurate dimension detection
        try:
            from PIL import Image
            
            with Image.open(io.BytesIO(image_data)) as img:
                return img.size
        except ImportError:
            pass
        
        # Fallback: basic dimension extraction for common formats
        format_type = detect_image_format(image_data)
        
        if format_type == "PNG":
            return _extract_png_dimensions(image_data)
        elif format_type == "JPEG":
            return _extract_jpeg_dimensions(image_data)
        elif format_type == "WEBP":
            return _extract_webp_dimensions(image_data)
        
        return None
    except Exception:
        return None


def _extract_png_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
    """Extract dimensions from PNG image data."""
    if len(image_data) < 24:
        return None
    
    # PNG dimensions are at bytes 16-23 (big-endian)
    width = int.from_bytes(image_data[16:20], "big")
    height = int.from_bytes(image_data[20:24], "big")
    
    return (width, height)


def _extract_jpeg_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
    """Extract dimensions from JPEG image data."""
    # This is a simplified JPEG parser - may not work for all JPEG variants
    pos = 2  # Skip SOI marker
    
    while pos < len(image_data) - 1:
        # Find next marker
        if image_data[pos] != 0xFF:
            return None
        
        marker = image_data[pos + 1]
        pos += 2
        
        # Check for frame markers (SOF0, SOF1, SOF2)
        if marker in (0xC0, 0xC1, 0xC2):
            if pos + 5 < len(image_data):
                height = int.from_bytes(image_data[pos + 3 : pos + 5], "big")
                width = int.from_bytes(image_data[pos + 5 : pos + 7], "big")
                return (width, height)
            return None
        
        # Skip segment data
        if pos + 1 < len(image_data):
            segment_length = int.from_bytes(image_data[pos : pos + 2], "big")
            pos += segment_length
        else:
            return None
    
    return None


def _extract_webp_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
    """Extract dimensions from WebP image data."""
    if len(image_data) < 30:
        return None
    
    # Check WebP format type
    format_type = image_data[12:16]
    
    if format_type == b"VP8 ":
        # Simple WebP format
        if len(image_data) < 30:
            return None
        width = int.from_bytes(image_data[26:28], "little") & 0x3FFF
        height = int.from_bytes(image_data[28:30], "little") & 0x3FFF
        return (width + 1, height + 1)  # WebP stores dimensions - 1
    
    elif format_type == b"VP8L":
        # Lossless WebP format
        if len(image_data) < 25:
            return None
        # WebP lossless dimensions are stored differently
        # This is a simplified extraction
        return None
    
    elif format_type == b"VP8X":
        # Extended WebP format
        if len(image_data) < 30:
            return None
        width = int.from_bytes(image_data[24:27], "little") + 1
        height = int.from_bytes(image_data[27:30], "little") + 1
        return (width, height)
    
    return None


def validate_image_dimensions(
    image_data: bytes, max_width: int = 2048, max_height: int = 2048
) -> Tuple[int, int]:
    """
    Validate image dimensions.
    
    Args:
        image_data: Raw image bytes
        max_width: Maximum allowed width
        max_height: Maximum allowed height
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ImageSizeError: If dimensions exceed limits
    """
    dimensions = get_image_dimensions(image_data)
    
    if dimensions is None:
        raise ImageSizeError("Unable to determine image dimensions")
    
    width, height = dimensions
    
    if width > max_width:
        raise ImageSizeError(f"Image width {width} exceeds maximum {max_width}")
    
    if height > max_height:
        raise ImageSizeError(f"Image height {height} exceeds maximum {max_height}")
    
    return dimensions


def encode_image_base64(image_data: bytes) -> str:
    """
    Encode image data as base64 string.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(image_data).decode("utf-8")


def decode_image_base64(base64_data: str) -> bytes:
    """
    Decode base64 string to image data.
    
    Args:
        base64_data: Base64 encoded string
        
    Returns:
        Raw image bytes
        
    Raises:
        ValueError: If base64 data is invalid
    """
    try:
        return base64.b64decode(base64_data)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}")


def get_mime_type(image_format: str) -> str:
    """
    Get MIME type for image format.
    
    Args:
        image_format: Image format (PNG, JPEG, WEBP)
        
    Returns:
        MIME type string
        
    Raises:
        ValueError: If format is unsupported
    """
    if image_format not in FORMAT_MIME_TYPES:
        raise ValueError(f"Unsupported image format: {image_format}")
    
    return FORMAT_MIME_TYPES[image_format]


def get_file_extension(image_format: str) -> str:
    """
    Get file extension for image format.
    
    Args:
        image_format: Image format (PNG, JPEG, WEBP)
        
    Returns:
        File extension string (including dot)
        
    Raises:
        ValueError: If format is unsupported
    """
    if image_format not in FORMAT_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {image_format}")
    
    return FORMAT_EXTENSIONS[image_format]


def create_image_filename(image_id: str, image_format: str) -> str:
    """
    Create a filename for an image.
    
    Args:
        image_id: Unique image identifier
        image_format: Image format (PNG, JPEG, WEBP)
        
    Returns:
        Filename string
    """
    extension = get_file_extension(image_format)
    return f"{image_id}{extension}"


def validate_image(
    image_data: bytes,
    max_size: int = 10485760,  # 10MB
    max_width: int = 2048,
    max_height: int = 2048,
    allowed_formats: List[str] = None,
) -> Dict[str, Union[str, int, Tuple[int, int]]]:
    """
    Comprehensive image validation.
    
    Args:
        image_data: Raw image bytes
        max_size: Maximum size in bytes
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        allowed_formats: List of allowed formats
        
    Returns:
        Dictionary with validation results:
            - format: Detected format
            - size: Size in bytes
            - dimensions: Tuple of (width, height)
            - mime_type: MIME type
            - extension: File extension
            
    Raises:
        ImageValidationError: If validation fails
    """
    if not image_data:
        raise ImageValidationError("Empty image data")
    
    # Validate format
    image_format = validate_image_format(image_data, allowed_formats)
    
    # Validate size
    size = validate_image_size(image_data, max_size)
    
    # Validate dimensions
    dimensions = validate_image_dimensions(image_data, max_width, max_height)
    
    return {
        "format": image_format,
        "size": size,
        "dimensions": dimensions,
        "mime_type": get_mime_type(image_format),
        "extension": get_file_extension(image_format),
    }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"
"""Secure ID generation utilities using UUIDs."""

import time
import uuid
from datetime import datetime
from typing import Optional


def generate_uuid() -> str:
    """
    Generate a secure random UUID4.
    
    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())


def generate_id(prefix: Optional[str] = None) -> str:
    """
    Generate a prefixed ID with UUID4.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Prefixed ID string (e.g., "img_123e4567-e89b-12d3-a456-426614174000")
    """
    uuid_str = generate_uuid()
    if prefix:
        return f"{prefix}_{uuid_str}"
    return uuid_str


def generate_image_id() -> str:
    """
    Generate an ID specifically for images.
    
    Returns:
        Image ID with "img" prefix
    """
    return generate_id("img")


def generate_request_id() -> str:
    """
    Generate an ID specifically for requests.
    
    Returns:
        Request ID with "req" prefix
    """
    return generate_id("req")


def generate_session_id() -> str:
    """
    Generate an ID specifically for sessions.
    
    Returns:
        Session ID with "sess" prefix
    """
    return generate_id("sess")


def generate_timestamped_id(prefix: Optional[str] = None) -> str:
    """
    Generate an ID with timestamp prefix for ordering.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Timestamped ID (e.g., "20240301120000_img_uuid")
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    uuid_part = generate_uuid()
    
    if prefix:
        return f"{timestamp}_{prefix}_{uuid_part}"
    return f"{timestamp}_{uuid_part}"


def generate_short_id(length: int = 8) -> str:
    """
    Generate a shorter ID for cases where full UUIDs are too long.
    
    Args:
        length: Length of the short ID (default 8)
        
    Returns:
        Short alphanumeric ID
        
    Note:
        This is less secure than full UUIDs but useful for user-facing IDs
    """
    import secrets
    import string
    
    if length < 4:
        raise ValueError("Short ID length must be at least 4")
    if length > 32:
        raise ValueError("Short ID length must not exceed 32")
    
    # Use URL-safe characters (no confusing characters like 0, O, l, I)
    alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def is_valid_prefixed_id(id_string: str, expected_prefix: Optional[str] = None) -> bool:
    """
    Check if a string is a valid prefixed ID.
    
    Args:
        id_string: String to validate
        expected_prefix: Expected prefix (optional)
        
    Returns:
        True if valid prefixed ID, False otherwise
    """
    if not id_string:
        return False
    
    parts = id_string.split("_", 1)
    if len(parts) != 2:
        # No prefix, check if it's just a UUID
        return is_valid_uuid(id_string)
    
    prefix, uuid_part = parts
    
    # Check prefix if expected
    if expected_prefix and prefix != expected_prefix:
        return False
    
    # Check UUID part
    return is_valid_uuid(uuid_part)


def extract_uuid_from_id(id_string: str) -> Optional[str]:
    """
    Extract the UUID part from a prefixed ID.
    
    Args:
        id_string: Prefixed ID string
        
    Returns:
        UUID string if found, None otherwise
    """
    if not id_string:
        return None
    
    # Check if it's already a UUID
    if is_valid_uuid(id_string):
        return id_string
    
    # Try to extract from prefixed format
    parts = id_string.split("_", 1)
    if len(parts) == 2 and is_valid_uuid(parts[1]):
        return parts[1]
    
    return None


def extract_prefix_from_id(id_string: str) -> Optional[str]:
    """
    Extract the prefix from a prefixed ID.
    
    Args:
        id_string: Prefixed ID string
        
    Returns:
        Prefix string if found, None otherwise
    """
    if not id_string:
        return None
    
    # Check if it's just a UUID (no prefix)
    if is_valid_uuid(id_string):
        return None
    
    # Try to extract prefix
    parts = id_string.split("_", 1)
    if len(parts) == 2 and is_valid_uuid(parts[1]):
        return parts[0]
    
    return None


def generate_correlation_id() -> str:
    """
    Generate a correlation ID for distributed tracing.
    
    Returns:
        Correlation ID with "corr" prefix
    """
    return generate_id("corr")


def generate_batch_id() -> str:
    """
    Generate a batch ID for grouping operations.
    
    Returns:
        Batch ID with "batch" prefix
    """
    return generate_id("batch")


class IDGenerator:
    """Class-based ID generator with configurable prefixes."""
    
    def __init__(self, default_prefix: Optional[str] = None):
        """
        Initialize ID generator.
        
        Args:
            default_prefix: Default prefix for generated IDs
        """
        self.default_prefix = default_prefix
    
    def generate(self, prefix: Optional[str] = None) -> str:
        """
        Generate an ID with optional prefix override.
        
        Args:
            prefix: Prefix override (uses default if not provided)
            
        Returns:
            Generated ID string
        """
        used_prefix = prefix or self.default_prefix
        return generate_id(used_prefix)
    
    def generate_timestamped(self, prefix: Optional[str] = None) -> str:
        """
        Generate a timestamped ID with optional prefix override.
        
        Args:
            prefix: Prefix override (uses default if not provided)
            
        Returns:
            Generated timestamped ID string
        """
        used_prefix = prefix or self.default_prefix
        return generate_timestamped_id(used_prefix)


# Pre-configured generators for common use cases
image_id_generator = IDGenerator("img")
request_id_generator = IDGenerator("req")
session_id_generator = IDGenerator("sess")
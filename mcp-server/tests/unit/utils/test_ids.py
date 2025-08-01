"""Tests for ID generation utilities."""

import re
import uuid
from unittest.mock import patch

import pytest

from utils.ids import (
    IDGenerator,
    extract_prefix_from_id,
    extract_uuid_from_id,
    generate_batch_id,
    generate_correlation_id,
    generate_id,
    generate_image_id,
    generate_request_id,
    generate_session_id,
    generate_short_id,
    generate_timestamped_id,
    generate_uuid,
    image_id_generator,
    is_valid_prefixed_id,
    is_valid_uuid,
    request_id_generator,
    session_id_generator,
)


class TestIDGeneration:
    """Test ID generation utilities."""

    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid_str = generate_uuid()
        
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36  # Standard UUID string length
        assert is_valid_uuid(uuid_str)
        
        # Test uniqueness
        uuid2 = generate_uuid()
        assert uuid_str != uuid2

    def test_generate_id_without_prefix(self):
        """Test ID generation without prefix."""
        id_str = generate_id()
        
        assert isinstance(id_str, str)
        assert is_valid_uuid(id_str)

    def test_generate_id_with_prefix(self):
        """Test ID generation with prefix."""
        id_str = generate_id("test")
        
        assert isinstance(id_str, str)
        assert id_str.startswith("test_")
        assert is_valid_prefixed_id(id_str, "test")
        
        # Extract UUID part and validate
        uuid_part = id_str.split("_", 1)[1]
        assert is_valid_uuid(uuid_part)

    def test_generate_image_id(self):
        """Test image ID generation."""
        image_id = generate_image_id()
        
        assert image_id.startswith("img_")
        assert is_valid_prefixed_id(image_id, "img")

    def test_generate_request_id(self):
        """Test request ID generation."""
        request_id = generate_request_id()
        
        assert request_id.startswith("req_")
        assert is_valid_prefixed_id(request_id, "req")

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = generate_session_id()
        
        assert session_id.startswith("sess_")
        assert is_valid_prefixed_id(session_id, "sess")

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        corr_id = generate_correlation_id()
        
        assert corr_id.startswith("corr_")
        assert is_valid_prefixed_id(corr_id, "corr")

    def test_generate_batch_id(self):
        """Test batch ID generation."""
        batch_id = generate_batch_id()
        
        assert batch_id.startswith("batch_")
        assert is_valid_prefixed_id(batch_id, "batch")

    def test_generate_timestamped_id_without_prefix(self):
        """Test timestamped ID generation without prefix."""
        timestamped_id = generate_timestamped_id()
        
        # Should have format: YYYYMMDDHHMMSS_uuid
        parts = timestamped_id.split("_", 1)
        assert len(parts) == 2
        
        timestamp_part, uuid_part = parts
        assert len(timestamp_part) == 14  # YYYYMMDDHHMMSS
        assert timestamp_part.isdigit()
        assert is_valid_uuid(uuid_part)

    def test_generate_timestamped_id_with_prefix(self):
        """Test timestamped ID generation with prefix."""
        timestamped_id = generate_timestamped_id("test")
        
        # Should have format: YYYYMMDDHHMMSS_test_uuid
        parts = timestamped_id.split("_")
        assert len(parts) == 3
        
        timestamp_part, prefix_part, uuid_part = parts
        assert len(timestamp_part) == 14
        assert timestamp_part.isdigit()
        assert prefix_part == "test"
        assert is_valid_uuid(uuid_part)

    def test_generate_short_id_default_length(self):
        """Test short ID generation with default length."""
        short_id = generate_short_id()
        
        assert isinstance(short_id, str)
        assert len(short_id) == 8
        # Should only contain safe characters
        assert re.match(r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]+$", short_id)

    def test_generate_short_id_custom_length(self):
        """Test short ID generation with custom length."""
        short_id = generate_short_id(12)
        
        assert len(short_id) == 12
        assert re.match(r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]+$", short_id)

    def test_generate_short_id_minimum_length(self):
        """Test short ID generation with minimum length."""
        short_id = generate_short_id(4)
        assert len(short_id) == 4

    def test_generate_short_id_invalid_length(self):
        """Test short ID generation with invalid lengths."""
        with pytest.raises(ValueError, match="Short ID length must be at least 4"):
            generate_short_id(3)
        
        with pytest.raises(ValueError, match="Short ID length must not exceed 32"):
            generate_short_id(33)

    def test_generate_short_id_uniqueness(self):
        """Test short ID uniqueness."""
        ids = [generate_short_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique

    def test_is_valid_uuid_valid(self):
        """Test UUID validation with valid UUIDs."""
        valid_uuid = str(uuid.uuid4())
        assert is_valid_uuid(valid_uuid)
        
        # Test different UUID formats
        assert is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
        assert is_valid_uuid("00000000-0000-0000-0000-000000000000")

    def test_is_valid_uuid_invalid(self):
        """Test UUID validation with invalid UUIDs."""
        assert not is_valid_uuid("not-a-uuid")
        assert not is_valid_uuid("123e4567-e89b-12d3-a456-42661417400")  # Too short
        assert not is_valid_uuid("123e4567-e89b-12d3-a456-4266141740000")  # Too long
        assert not is_valid_uuid("")
        assert not is_valid_uuid(None)

    def test_is_valid_prefixed_id_valid(self):
        """Test prefixed ID validation with valid IDs."""
        valid_id = f"test_{uuid.uuid4()}"
        assert is_valid_prefixed_id(valid_id)
        assert is_valid_prefixed_id(valid_id, "test")
        
        # Test with just UUID (no prefix)
        valid_uuid = str(uuid.uuid4())
        assert is_valid_prefixed_id(valid_uuid)

    def test_is_valid_prefixed_id_invalid(self):
        """Test prefixed ID validation with invalid IDs."""
        assert not is_valid_prefixed_id("test_not-a-uuid")
        assert not is_valid_prefixed_id("test_")
        assert not is_valid_prefixed_id("")
        assert not is_valid_prefixed_id(None)
        
        # Test with wrong prefix
        valid_id = f"other_{uuid.uuid4()}"
        assert not is_valid_prefixed_id(valid_id, "test")

    def test_extract_uuid_from_id_prefixed(self):
        """Test UUID extraction from prefixed ID."""
        original_uuid = str(uuid.uuid4())
        prefixed_id = f"test_{original_uuid}"
        
        extracted_uuid = extract_uuid_from_id(prefixed_id)
        assert extracted_uuid == original_uuid

    def test_extract_uuid_from_id_just_uuid(self):
        """Test UUID extraction from plain UUID."""
        original_uuid = str(uuid.uuid4())
        
        extracted_uuid = extract_uuid_from_id(original_uuid)
        assert extracted_uuid == original_uuid

    def test_extract_uuid_from_id_invalid(self):
        """Test UUID extraction from invalid ID."""
        assert extract_uuid_from_id("invalid") is None
        assert extract_uuid_from_id("") is None
        assert extract_uuid_from_id(None) is None
        assert extract_uuid_from_id("test_invalid-uuid") is None

    def test_extract_prefix_from_id_prefixed(self):
        """Test prefix extraction from prefixed ID."""
        prefixed_id = f"myprefix_{uuid.uuid4()}"
        
        prefix = extract_prefix_from_id(prefixed_id)
        assert prefix == "myprefix"

    def test_extract_prefix_from_id_just_uuid(self):
        """Test prefix extraction from plain UUID."""
        plain_uuid = str(uuid.uuid4())
        
        prefix = extract_prefix_from_id(plain_uuid)
        assert prefix is None

    def test_extract_prefix_from_id_invalid(self):
        """Test prefix extraction from invalid ID."""
        assert extract_prefix_from_id("invalid") is None
        assert extract_prefix_from_id("") is None
        assert extract_prefix_from_id(None) is None


class TestIDGenerator:
    """Test IDGenerator class."""

    def test_id_generator_default_prefix(self):
        """Test IDGenerator with default prefix."""
        generator = IDGenerator("test")
        
        id_str = generator.generate()
        assert id_str.startswith("test_")
        assert is_valid_prefixed_id(id_str, "test")

    def test_id_generator_no_default_prefix(self):
        """Test IDGenerator without default prefix."""
        generator = IDGenerator()
        
        id_str = generator.generate()
        assert is_valid_uuid(id_str)

    def test_id_generator_prefix_override(self):
        """Test IDGenerator with prefix override."""
        generator = IDGenerator("default")
        
        id_str = generator.generate("override")
        assert id_str.startswith("override_")
        assert is_valid_prefixed_id(id_str, "override")

    def test_id_generator_timestamped(self):
        """Test IDGenerator timestamped ID generation."""
        generator = IDGenerator("test")
        
        timestamped_id = generator.generate_timestamped()
        parts = timestamped_id.split("_")
        assert len(parts) == 3
        assert parts[1] == "test"
        assert is_valid_uuid(parts[2])

    def test_id_generator_timestamped_override(self):
        """Test IDGenerator timestamped ID with prefix override."""
        generator = IDGenerator("default")
        
        timestamped_id = generator.generate_timestamped("override")
        parts = timestamped_id.split("_")
        assert len(parts) == 3
        assert parts[1] == "override"


class TestPreConfiguredGenerators:
    """Test pre-configured generator instances."""

    def test_image_id_generator(self):
        """Test pre-configured image ID generator."""
        image_id = image_id_generator.generate()
        assert image_id.startswith("img_")
        assert is_valid_prefixed_id(image_id, "img")

    def test_request_id_generator(self):
        """Test pre-configured request ID generator."""
        request_id = request_id_generator.generate()
        assert request_id.startswith("req_")
        assert is_valid_prefixed_id(request_id, "req")

    def test_session_id_generator(self):
        """Test pre-configured session ID generator."""
        session_id = session_id_generator.generate()
        assert session_id.startswith("sess_")
        assert is_valid_prefixed_id(session_id, "sess")

    def test_generator_timestamped(self):
        """Test pre-configured generator timestamped IDs."""
        timestamped_id = image_id_generator.generate_timestamped()
        parts = timestamped_id.split("_")
        assert len(parts) == 3
        assert parts[1] == "img"
        assert is_valid_uuid(parts[2])


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_prefix(self):
        """Test ID generation with empty prefix."""
        id_str = generate_id("")
        # Empty prefix should be treated as no prefix
        assert is_valid_uuid(id_str)

    def test_special_characters_in_prefix(self):
        """Test ID generation with special characters in prefix."""
        # This should work but might not be recommended
        id_str = generate_id("test-with-dashes")
        assert id_str.startswith("test-with-dashes_")
        
        uuid_part = id_str.split("_", 1)[1]
        assert is_valid_uuid(uuid_part)

    def test_very_long_prefix(self):
        """Test ID generation with very long prefix."""
        long_prefix = "a" * 100
        id_str = generate_id(long_prefix)
        assert id_str.startswith(f"{long_prefix}_")

    def test_concurrent_id_generation(self):
        """Test ID generation is thread-safe and produces unique IDs."""
        import concurrent.futures
        
        def generate_many_ids():
            return [generate_uuid() for _ in range(100)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_many_ids) for _ in range(4)]
            all_ids = []
            
            for future in concurrent.futures.as_completed(futures):
                all_ids.extend(future.result())
        
        # All IDs should be unique
        assert len(set(all_ids)) == len(all_ids)

    def test_id_format_consistency(self):
        """Test that generated IDs follow consistent format."""
        # Generate many IDs and check format consistency
        for _ in range(100):
            image_id = generate_image_id()
            assert re.match(r"^img_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", image_id)
            
            request_id = generate_request_id()
            assert re.match(r"^req_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", request_id)
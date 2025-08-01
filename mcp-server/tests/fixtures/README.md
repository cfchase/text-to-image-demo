# Test Fixtures Documentation

This directory contains test fixtures and sample data used by the MCP Image Generation Server test suite.

## Overview

Test fixtures provide consistent, reusable test data and components that ensure reliable and repeatable testing across all test modules. The fixtures are organized into several categories:

- **Sample Images**: Pre-generated image files in various formats
- **Mock Data**: JSON files with sample metadata and configurations
- **Configuration Files**: Test-specific configuration overrides
- **Test Assets**: Additional resources needed for integration tests

## Directory Structure

```
tests/fixtures/
├── README.md                 # This documentation file
├── images/                   # Sample image files
│   ├── sample_512x512.png   # Standard 512x512 PNG image
│   ├── sample_1024x1024.png # High resolution PNG image
│   ├── sample_image.jpg     # JPEG format sample
│   ├── sample_image.webp    # WebP format sample
│   ├── tiny_image.png       # Minimal size PNG (1x1)
│   └── large_image.png      # Large size test image
├── metadata/                 # Sample metadata files
│   ├── basic_metadata.json  # Basic image generation metadata
│   ├── batch_metadata.json  # Multiple image metadata
│   └── invalid_metadata.json # Invalid metadata for error testing
├── configs/                  # Test configuration files
│   ├── test_settings.env    # Environment variables for testing
│   ├── s3_config.json       # S3 storage configuration
│   └── file_config.json     # File storage configuration
└── responses/               # Mock API response data
    ├── kserve_success.json  # Successful KServe response
    ├── kserve_error.json    # Error KServe response
    └── health_check.json    # Health check responses
```

## Fixture Categories

### 1. Image Fixtures

#### Standard Test Images
- **sample_512x512.png**: 512x512 pixel PNG image, typical generation size
- **sample_1024x1024.png**: High resolution PNG for testing large images
- **tiny_image.png**: 1x1 pixel image for minimal size testing
- **large_image.png**: Large image for testing size limits and performance

#### Format Variations
- **sample_image.jpg**: JPEG format for format detection testing
- **sample_image.webp**: WebP format for modern format support testing

#### Usage in Tests
```python
from pathlib import Path

# Load sample image data
fixtures_dir = Path(__file__).parent / "fixtures" / "images"
sample_png = (fixtures_dir / "sample_512x512.png").read_bytes()

# Use in test
async def test_save_image(storage):
    result = await storage.save_image(sample_png, "test-id", metadata)
    assert result is not None
```

### 2. Metadata Fixtures

#### Basic Metadata (`basic_metadata.json`)
Standard image generation metadata with all required fields:
```json
{
  "image_id": "img_12345678-1234-1234-1234-123456789abc",
  "prompt": "a beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "num_inference_steps": 50,
  "guidance_scale": 7.5,
  "seed": 42,
  "model_name": "stable-diffusion-v1-5",
  "generation_time": 3.2,
  "created_at": "2024-01-01T12:00:00Z",
  "format": "png",
  "size": 65536
}
```

#### Batch Metadata (`batch_metadata.json`)
Array of metadata for testing batch operations:
```json
[
  {
    "image_id": "batch_001",
    "prompt": "mountain landscape",
    "width": 512,
    "height": 512,
    ...
  },
  {
    "image_id": "batch_002", 
    "prompt": "ocean sunset",
    "width": 1024,
    "height": 1024,
    ...
  }
]
```

#### Invalid Metadata (`invalid_metadata.json`)
Metadata with missing or invalid fields for error testing:
```json
{
  "prompt": "",
  "width": -1,
  "height": "invalid",
  "guidance_scale": 100.0
}
```

### 3. Configuration Fixtures

#### Test Settings (`test_settings.env`)
Environment variables for test configuration:
```env
SERVICE_NAME=test-mcp-server
LOG_LEVEL=DEBUG
HOST=127.0.0.1
PORT=18000
STORAGE_BACKEND=file
STORAGE_PATH=/tmp/test-images
KSERVE_ENDPOINT=http://localhost:8080
KSERVE_MODEL_NAME=test-model
```

#### Storage Configurations
- **s3_config.json**: S3 storage settings for integration tests
- **file_config.json**: File storage settings for local tests

### 4. Response Fixtures

#### Successful KServe Response (`kserve_success.json`)
```json
{
  "model_name": "stable-diffusion",
  "model_version": "v1.5",
  "predictions": [
    {
      "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jQUz...",
      "metadata": {
        "prompt": "test prompt",
        "width": 512,
        "height": 512,
        "generation_time": 2.5
      }
    }
  ]
}
```

#### Error Response (`kserve_error.json`)
```json
{
  "error": "Model inference failed",
  "code": "INFERENCE_ERROR",
  "details": {
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
  }
}
```

## Using Fixtures in Tests

### Loading Fixture Data

```python
import json
from pathlib import Path

def load_fixture_json(filename: str) -> dict:
    """Load JSON fixture file."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / filename, 'r') as f:
        return json.load(f)

def load_fixture_image(filename: str) -> bytes:
    """Load image fixture file."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "images"
    return (fixtures_dir / filename).read_bytes()

# Usage in tests
metadata = load_fixture_json("metadata/basic_metadata.json")
image_data = load_fixture_image("sample_512x512.png")
```

### Fixture-Based Pytest Fixtures

```python
@pytest.fixture
def sample_metadata():
    """Load sample metadata from fixture."""
    return load_fixture_json("metadata/basic_metadata.json")

@pytest.fixture  
def sample_image_data():
    """Load sample image from fixture."""
    return load_fixture_image("sample_512x512.png")

@pytest.fixture
def batch_metadata():
    """Load batch metadata from fixture."""
    return load_fixture_json("metadata/batch_metadata.json")
```

### Parameterized Tests with Fixtures

```python
@pytest.mark.parametrize("image_file,expected_format", [
    ("sample_512x512.png", "PNG"),
    ("sample_image.jpg", "JPEG"), 
    ("sample_image.webp", "WEBP"),
])
def test_image_format_detection(image_file, expected_format):
    """Test image format detection with various formats."""
    image_data = load_fixture_image(image_file)
    detected_format = detect_image_format(image_data)
    assert detected_format == expected_format
```

## Maintaining Fixtures

### Adding New Fixtures

1. **Create the fixture file** in the appropriate subdirectory
2. **Update this README** with documentation for the new fixture
3. **Add validation tests** to ensure fixture integrity
4. **Update related test cases** to use the new fixture

### Fixture Validation

Fixtures should be validated to ensure they remain correct:

```python
def test_fixture_integrity():
    """Validate that all fixtures are valid."""
    # Validate image fixtures
    for image_file in fixtures_images_dir.glob("*.png"):
        image_data = image_file.read_bytes()
        assert image_data.startswith(b"\x89PNG")
    
    # Validate JSON fixtures
    for json_file in fixtures_metadata_dir.glob("*.json"):
        data = json.loads(json_file.read_text())
        assert isinstance(data, (dict, list))
```

### Best Practices

1. **Keep fixtures minimal** but representative of real data
2. **Use descriptive filenames** that indicate the fixture purpose
3. **Include both valid and invalid** fixtures for comprehensive testing
4. **Document any special characteristics** of fixtures in this README
5. **Avoid binary fixtures** when possible; prefer generated test data
6. **Version control friendly** - use deterministic data where possible

## Fixture Generation

Some fixtures are generated programmatically to ensure consistency:

```python
def generate_test_images():
    """Generate test image fixtures."""
    from tests.utils import TestImageGenerator
    
    # Generate various sized PNG images
    sizes = [(1, 1), (512, 512), (1024, 1024)]
    for width, height in sizes:
        image_data = TestImageGenerator.create_png_data(width, height)
        filename = f"sample_{width}x{height}.png"
        (fixtures_images_dir / filename).write_bytes(image_data)
```

## Integration with CI/CD

Test fixtures are included in the repository and used by CI/CD pipelines:

- **Fixtures are committed** to version control for reproducibility
- **Large binary fixtures** (>1MB) should be avoided or stored externally
- **Generated fixtures** should have deterministic content for consistent testing
- **Fixture validation** is run as part of the test suite

## Troubleshooting

### Common Issues

1. **Missing fixture files**: Ensure all required fixtures are committed to the repository
2. **Invalid fixture data**: Run fixture validation tests to identify corrupted files
3. **Platform-specific paths**: Use `pathlib.Path` for cross-platform compatibility
4. **Encoding issues**: Specify encoding explicitly when reading text fixtures

### Debugging Fixture Loading

```python
def debug_fixture_loading():
    """Debug fixture loading issues."""
    fixtures_base = Path(__file__).parent / "fixtures"
    
    print(f"Fixtures base directory: {fixtures_base}")
    print(f"Directory exists: {fixtures_base.exists()}")
    print(f"Is directory: {fixtures_base.is_dir()}")
    
    for subdir in ["images", "metadata", "configs", "responses"]:
        subdir_path = fixtures_base / subdir
        print(f"{subdir}: exists={subdir_path.exists()}, files={list(subdir_path.glob('*'))}")
```

## Security Considerations

- **No sensitive data** should be included in fixtures
- **Mock credentials** should be obviously fake (test-*, mock-*, etc.)
- **API responses** should not contain real API keys or tokens
- **File permissions** should be appropriate for test data

---

For questions about test fixtures or to request new fixtures, please refer to the main project documentation or contact the development team.
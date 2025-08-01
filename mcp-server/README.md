# MCP Image Generation Server

An MCP (Model Context Protocol) server that provides image generation capabilities through integration with the KServe diffusers runtime.

## Features

- Generate images from text prompts using Stable Diffusion models
- Support for multiple storage backends (local filesystem, S3)
- HTTP file serving for generated images with automatic cleanup
- Configurable image generation parameters
- Full MCP protocol compliance using FastMCP 2.10.6

## Quick Start

### Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start the server (local storage)
python -m mcp_server.main
```

### Docker

```bash
# Build the container
docker build -t mcp-image-server .

# Run with local storage
docker run -p 8000:8000 mcp-image-server

# Run with S3 storage
docker run -p 8000:8000 \
  -e STORAGE_BACKEND=s3 \
  -e S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=yyy \
  mcp-image-server
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Configuration

The server can be configured via environment variables:

- `STORAGE_BACKEND`: Storage backend to use (`file` or `s3`, default: `file`)
- `STORAGE_PATH`: Local storage path (default: `/tmp/mcp-images`)
- `S3_BUCKET`: S3 bucket name (required for S3 backend)
- `S3_PREFIX`: S3 key prefix (default: `mcp-images/`)
- `S3_ENDPOINT_URL`: Custom S3 endpoint URL (optional)
- `KSERVE_ENDPOINT`: KServe inference endpoint URL
- `KSERVE_MODEL_NAME`: Model name for KServe requests
- `IMAGE_CLEANUP_INTERVAL`: Cleanup interval in seconds (default: 300)
- `IMAGE_TTL`: Image time-to-live in seconds (default: 3600)

## MCP Tools

The server provides the following MCP tools:

### generate_image

Generates an image from a text prompt.

Parameters:
- `prompt` (string, required): The text prompt for image generation
- `width` (integer, optional): Image width in pixels (default: 512)
- `height` (integer, optional): Image height in pixels (default: 512)
- `num_inference_steps` (integer, optional): Number of denoising steps (default: 50)
- `guidance_scale` (number, optional): Guidance scale for generation (default: 7.5)
- `negative_prompt` (string, optional): Negative prompt to avoid certain features
- `seed` (integer, optional): Random seed for reproducible generation

Returns:
- `url` (string): URL to access the generated image
- `image_id` (string): Unique identifier for the image
- `metadata` (object): Generation metadata including parameters used

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_storage.py

# Run integration tests only
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## Deployment

### Kubernetes

```bash
# Deploy to OpenShift/Kubernetes
kubectl apply -f deployment/k8s/
```

### Configuration for Production

For production deployments with S3:

```yaml
env:
  - name: STORAGE_BACKEND
    value: "s3"
  - name: S3_BUCKET
    valueFrom:
      secretKeyRef:
        name: s3-credentials
        key: bucket
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: s3-credentials
        key: access-key-id
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: s3-credentials
        key: secret-access-key
```

## License

This project is part of the Red Hat OpenShift AI demo suite.
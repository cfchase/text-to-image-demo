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
docker build -t mcp-image-server -f deployment/docker/Dockerfile .

# Run with local storage
docker run -p 8000:8000 \
  -e KSERVE_ENDPOINT="http://host.docker.internal:8080/v1/models/stable-diffusion" \
  mcp-image-server

# Run with S3 storage
docker run -p 8000:8000 \
  -e STORAGE_BACKEND=s3 \
  -e S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=yyy \
  -e KSERVE_ENDPOINT="http://host.docker.internal:8080/v1/models/stable-diffusion" \
  mcp-image-server

# Development build with live reload
docker build -t mcp-image-server:dev \
  --target development \
  -f deployment/docker/Dockerfile .
docker run -p 8000:8000 \
  -v $(pwd)/src:/app/src \
  -e KSERVE_ENDPOINT="http://host.docker.internal:8080/v1/models/stable-diffusion" \
  mcp-image-server:dev
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

The server supports multiple deployment scenarios:

- **Local Development**: Direct Python execution with file storage
- **Docker**: Containerized deployment with multi-stage builds
- **Kubernetes**: Production deployment with scaling and high availability
- **OpenShift**: Enterprise Kubernetes with additional security features

### Local Development

```bash
# Set up environment
export KSERVE_ENDPOINT="http://localhost:8080/v1/models/stable-diffusion"
export STORAGE_BACKEND="file"
export STORAGE_PATH="/tmp/mcp-images"

# Run development server
python -m mcp_server.main dev
```

### Docker Deployment

```bash
# Production build
docker build -t mcp-image-server \
  --target production \
  -f deployment/docker/Dockerfile .

# Run with file storage
docker run -d \
  --name mcp-image-server \
  -p 8000:8000 \
  -v /host/storage:/app/storage \
  -e KSERVE_ENDPOINT="http://diffusers-runtime:8080/v1/models/stable-diffusion" \
  mcp-image-server

# Run with S3 storage
docker run -d \
  --name mcp-image-server \
  -p 8000:8000 \
  -e STORAGE_BACKEND=s3 \
  -e S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e KSERVE_ENDPOINT="http://diffusers-runtime:8080/v1/models/stable-diffusion" \
  mcp-image-server
```

### Kubernetes Deployment

```bash
# Quick deployment
kubectl apply -f deployment/k8s/

# Or step by step
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/secret.yaml      # Configure secrets first
kubectl apply -f deployment/k8s/deployment.yaml
kubectl apply -f deployment/k8s/service.yaml

# Check deployment status
kubectl get pods -l app=mcp-image-server
kubectl get svc mcp-image-server
```

### Configuration Examples

**File Storage (PVC)**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-image-server-config
data:
  storage_backend: "file"
  storage_path: "/app/storage"
  kserve_endpoint: "http://diffusers-runtime.default.svc.cluster.local:8080/v1/models/stable-diffusion"
```

**S3 Storage**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-image-server-config
data:
  storage_backend: "s3"
  s3_bucket: "my-image-bucket"
  s3_prefix: "mcp-images/"
  kserve_endpoint: "http://diffusers-runtime.default.svc.cluster.local:8080/v1/models/stable-diffusion"
---
apiVersion: v1
kind: Secret
metadata:
  name: mcp-image-server-secrets
type: Opaque
data:
  aws_access_key_id: <base64-encoded-key>
  aws_secret_access_key: <base64-encoded-secret>
```

### Service Exposure

**LoadBalancer**:
```bash
kubectl patch service mcp-image-server -p '{"spec":{"type":"LoadBalancer"}}'
```

**Ingress**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-image-server-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - mcp-image-server.yourdomain.com
    secretName: mcp-image-server-tls
  rules:
  - host: mcp-image-server.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-image-server
            port:
              number: 8000
```

**OpenShift Route**:
```bash
oc expose service mcp-image-server --hostname=mcp-image-server.apps.cluster.com
```

## Documentation

- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Comprehensive deployment guide
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture details

## License

This project is part of the Red Hat OpenShift AI demo suite.
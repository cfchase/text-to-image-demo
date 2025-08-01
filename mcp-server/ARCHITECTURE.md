# MCP Image Generation Server Architecture

## Overview

The MCP Image Generation Server provides a Model Context Protocol (MCP) interface for image generation, integrating with the KServe diffusers runtime. It's designed to work in both local development and distributed Kubernetes environments.

## System Architecture

```
┌─────────────────┐     MCP Protocol      ┌──────────────────┐
│   MCP Client    │◄────────────────────►│  MCP Server      │
│  (LLM/Claude)   │                       │  (FastMCP 2.10.6)│
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │  Core Logic    │
                                          │  & Routing     │
                                          └───┬────────┬───┘
                                              │        │
                                              ▼        ▼
                                     ┌──────────┐  ┌──────────┐
                                     │ Storage  │  │ KServe   │
                                     │ System   │  │ Client   │
                                     └────┬─────┘  └────┬─────┘
                                          │             │
                         ┌────────────────┴───┐         │
                         ▼                    ▼         ▼
                   ┌──────────┐         ┌──────────┐  ┌──────────────┐
                   │   File   │         │    S3    │  │ Diffusers    │
                   │ Storage  │         │ Storage  │  │ Runtime Pod  │
                   └──────────┘         └──────────┘  └──────────────┘
```

## Component Details

### MCP Server (FastMCP 2.10.6)
- Implements MCP protocol for tool registration and invocation
- Provides `generate_image` tool with comprehensive parameters
- Handles async operations for efficient request processing
- Manages HTTP file serving endpoints for generated images

### Storage System
Abstracted storage interface supporting multiple backends:

#### File Storage Backend
- Used for local development and single-pod deployments
- Stores images in configurable local directory
- Supports both local filesystem and mounted PVC volumes
- Automatic cleanup of expired images

#### S3 Storage Backend
- Used for multi-pod production deployments
- Supports any S3-compatible storage (AWS S3, MinIO, etc.)
- Generates presigned URLs for secure image access
- Configurable bucket and prefix settings

### KServe Integration
- HTTP client for v1 inference protocol
- Handles request formatting for diffusers runtime
- Manages model name and endpoint configuration
- Error handling and retry logic

### HTTP File Server
- Serves generated images via HTTP endpoints
- Unique URLs for each generated image
- Automatic cleanup based on TTL
- Security through unguessable UUIDs

## Data Flow

1. **Image Generation Request**
   ```
   MCP Client → generate_image tool → MCP Server
   ```

2. **Processing**
   ```
   MCP Server → KServe Client → Diffusers Runtime
   ```

3. **Storage**
   ```
   Diffusers Runtime → Image Data → Storage Backend
   ```

4. **Response**
   ```
   Storage Backend → Image URL → MCP Server → MCP Client
   ```

5. **Image Retrieval**
   ```
   HTTP Client → File Server Endpoint → Storage Backend → Image Data
   ```

## Configuration Management

### Environment Variables
- `STORAGE_BACKEND`: Selects storage implementation
- `KSERVE_ENDPOINT`: Target inference service URL
- `IMAGE_TTL`: Lifetime of generated images
- Storage-specific configs (S3 credentials, file paths)

### Deployment Modes

#### Local Development
```yaml
STORAGE_BACKEND: file
STORAGE_PATH: /tmp/mcp-images
KSERVE_ENDPOINT: http://localhost:8080/v1/models/stable-diffusion
```

#### Kubernetes with PVC
```yaml
STORAGE_BACKEND: file
STORAGE_PATH: /mnt/shared-storage/images
KSERVE_ENDPOINT: http://diffusers-runtime.namespace.svc.cluster.local:8080/v1/models/stable-diffusion
```

#### Kubernetes with S3
```yaml
STORAGE_BACKEND: s3
S3_BUCKET: image-generation
S3_PREFIX: mcp-server/
KSERVE_ENDPOINT: http://diffusers-runtime.namespace.svc.cluster.local:8080/v1/models/stable-diffusion
```

## Security Considerations

### Image Access
- Generated images have unguessable UUID-based URLs
- Optional authentication can be added to file serving endpoints
- S3 presigned URLs provide time-limited access

### Input Validation
- Prompt content filtering
- Parameter range validation
- Request rate limiting support

### Network Security
- Internal service communication in Kubernetes
- HTTPS support for external endpoints
- No direct filesystem access from MCP protocol

## Scalability

### Horizontal Scaling
- Stateless server design enables multiple replicas
- S3 backend supports concurrent access
- Load balancing through Kubernetes services

### Performance Optimization
- Async request handling
- Connection pooling for KServe requests
- Efficient image streaming
- Configurable cleanup intervals

## Error Handling

### Graceful Degradation
- Fallback error messages for generation failures
- Storage backend failover (future enhancement)
- Request retry with exponential backoff

### Monitoring Points
- Image generation success/failure rates
- Storage usage metrics
- KServe response times
- Cleanup effectiveness

## Extension Points

### Additional Tools
- `list_generated_images`: Browse recent generations
- `delete_image`: Manual cleanup capability
- `get_image_metadata`: Retrieve generation parameters

### Storage Backends
- Redis for metadata caching
- Database for generation history
- CDN integration for image serving

### Model Support
- Multiple model selection
- Model-specific parameter validation
- Custom pipeline support
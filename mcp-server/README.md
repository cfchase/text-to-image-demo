# MCP Server for Image Generation

A unified FastMCP server that provides text-to-image generation capabilities with integrated image serving.

## Features

- **MCP Protocol Support**: Exposes image generation as an MCP tool
- **Integrated Image Serving**: Serves generated images via HTTP endpoints
- **Configurable Backend**: Works with any diffusers-runtime instance
- **Input Validation**: Validates prompts and parameters
- **Health Checks**: Built-in health monitoring endpoint

## Quick Start

```bash
# Install dependencies
make install

# Run the server
make run
```

## Endpoints

- `/mcp` - MCP protocol endpoint for tool calls
- `/images/{name}` - Serve individual images
- `/images` - List all available images
- `/health` - Health check endpoint
- `/docs` - API documentation

## Configuration

Environment variables:
- `DIFFUSERS_RUNTIME_URL` - URL of diffusers-runtime (default: http://0.0.0.0:8080)
- `DIFFUSERS_MODEL_ID` - Model ID to use (default: model)
- `IMAGE_OUTPUT_PATH` - Directory for images (default: /tmp/image-generator)

## Testing

```bash
# Test diffusers-runtime connection
make test-diffusers

# Run integration tests
make test
```
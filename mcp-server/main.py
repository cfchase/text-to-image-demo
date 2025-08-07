#!/usr/bin/env python3
"""Unified MCP and image server using FastMCP with custom routes."""

from fastmcp import FastMCP
import click
import httpx
import base64
import uuid
import os
from typing import Optional
from pathlib import Path
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response


# Get configuration from environment variables or use defaults
DIFFUSERS_RUNTIME_URL = os.environ.get("DIFFUSERS_RUNTIME_URL", "http://0.0.0.0:8080")
DIFFUSERS_MODEL_ID = os.environ.get("DIFFUSERS_MODEL_ID", "model")
IMAGE_OUTPUT_PATH = os.environ.get("IMAGE_OUTPUT_PATH", "/tmp/image-generator")

# Ensure output directory exists
os.makedirs(IMAGE_OUTPUT_PATH, exist_ok=True)

# Create MCP server
mcp = FastMCP("My MCP Server")


def validate_prompt(prompt: str) -> str:
    """Validate and sanitize prompt input"""
    if not prompt or len(prompt.strip()) == 0:
        raise ValueError("Prompt cannot be empty")
    if len(prompt) > 1000:  # reasonable limit
        raise ValueError("Prompt too long (max 1000 characters)")
    return prompt.strip()


@mcp.tool
def generate_image(prompt: str,
                   negative_prompt: Optional[str] = None,
                   num_inference_steps: Optional[int] = 50
                   ) -> str:
    """Generate an image using the diffusers-runtime service.
    
    Args:
        prompt: Text prompt describing the image to generate
        negative_prompt: Text describing what to avoid in the image
        num_inference_steps: Number of denoising steps (higher = better quality but slower)
    
    Returns:
        URL to access the generated image
    """
    try:
        # Validate inputs
        prompt = validate_prompt(prompt)
        if negative_prompt:
            negative_prompt = validate_prompt(negative_prompt)
        
        # Validate num_inference_steps
        if not 1 <= num_inference_steps <= 150:
            return "Error: num_inference_steps must be between 1 and 150"
    except ValueError as e:
        return f"Validation error: {str(e)}"
    
    # Diffusers runtime endpoint
    url = f"{DIFFUSERS_RUNTIME_URL}/v1/models/{DIFFUSERS_MODEL_ID}:predict"
    
    # Build request payload
    payload = {
        "instances": [
            {
                "prompt": prompt,
                "num_inference_steps": num_inference_steps
            }
        ]
    }
    
    # Add negative prompt if provided
    if negative_prompt:
        payload["instances"][0]["negative_prompt"] = negative_prompt
    
    try:
        # Make request to diffusers-runtime
        response = httpx.post(
            url, 
            json=payload,
            timeout=120.0  # 2 minute timeout for image generation
        )
        response.raise_for_status()
        
        # Extract base64 image from response with validation
        result = response.json()
        
        # Validate response structure
        if "predictions" not in result or not result["predictions"]:
            return "Error: Invalid response format from diffusers-runtime (missing predictions)"
        
        prediction = result["predictions"][0]
        if "image" not in prediction or "b64" not in prediction["image"]:
            return "Error: Invalid response format from diffusers-runtime (missing image data)"
        
        image_b64 = prediction["image"]["b64"]
        if not image_b64:
            return "Error: Empty image data received from diffusers-runtime"
        
        # Decode and save image
        image_data = base64.b64decode(image_b64)
        
        # Generate unique filename
        image_id = str(uuid.uuid4())
        image_path = os.path.join(IMAGE_OUTPUT_PATH, f"{image_id}.png")
        
        # Save image to file
        with open(image_path, "wb") as f:
            f.write(image_data)
        
        # Return URL for the unified server
        if os.environ.get("PUBLIC_URL"):
            image_url = f"{os.environ.get('PUBLIC_URL')}/images/{image_id}.png"
        else:
            port = os.environ.get("PORT", "8000")
            image_url = f"http://localhost:{port}/images/{image_id}.png"
        return f"Image generated: {image_url}"
        
    except httpx.HTTPError as e:
        return f"Error generating image: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Add custom routes using FastMCP's custom_route decorator
@mcp.custom_route("/images/{image_name}", methods=["GET"])
async def serve_image(request: Request) -> Response:
    """Serve generated images."""
    image_name = request.path_params["image_name"]
    
    # Validate image name (prevent directory traversal)
    if ".." in image_name or "/" in image_name or "\\" in image_name:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid image name"}
        )
    
    image_path = Path(IMAGE_OUTPUT_PATH) / image_name
    
    if not image_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "Image not found"}
        )
    
    # Return the image file with proper headers
    return FileResponse(
        path=image_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET"
        }
    )


@mcp.custom_route("/images", methods=["GET"])
async def list_images(request: Request) -> Response:
    """List available generated images."""
    image_dir = Path(IMAGE_OUTPUT_PATH)
    images = []
    
    # Get base URL from environment or default to localhost
    if os.environ.get("PUBLIC_URL"):
        base_url = os.environ.get("PUBLIC_URL")
    else:
        port = os.environ.get("PORT", "8000")
        base_url = f"http://localhost:{port}"
    
    for image_path in image_dir.glob("*.png"):
        images.append({
            "name": image_path.name,
            "url": f"{base_url}/images/{image_path.name}",
            "size": image_path.stat().st_size,
            "created": image_path.stat().st_mtime
        })
    
    return JSONResponse({
        "images": sorted(images, key=lambda x: x["created"], reverse=True)
    })


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "mcp_server": "active",
        "image_server": "active"
    })


@click.command()
@click.option("--port", type=int, default=8000,
              help="Port for unified server (default: 8000)")
def main(port: int):
    """Unified Image Generation MCP Server with integrated image serving"""
    # Set port in environment for URL generation
    os.environ["PORT"] = str(port)
    
    print(f"\n🚀 Starting unified server on port {port}")
    print(f"📡 MCP endpoint: http://localhost:{port}/mcp")
    print(f"🖼️  Image endpoint: http://localhost:{port}/images")
    print(f"📊 Health check: http://localhost:{port}/health")
    print(f"📚 API docs: http://localhost:{port}/docs\n")
    
    # Run the unified server (bind to 0.0.0.0 for container access)
    mcp.run(transport="http", port=port, host="0.0.0.0")


if __name__ == "__main__":
    main()
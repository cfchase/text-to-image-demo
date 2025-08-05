from fastmcp import FastMCP
import click
import httpx
import base64
import uuid
import os
from typing import Optional


# Get configuration from environment variables or use defaults
DIFFUSERS_RUNTIME_URL = os.environ.get("DIFFUSERS_RUNTIME_URL", "http://0.0.0.0:8080")
DIFFUSERS_MODEL_ID = os.environ.get("DIFFUSERS_MODEL_ID", "model")
IMAGE_OUTPUT_PATH = os.environ.get("IMAGE_OUTPUT_PATH", "/tmp/image-generator")

# Ensure output directory exists
os.makedirs(IMAGE_OUTPUT_PATH, exist_ok=True)

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
        Path to the generated image file
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
        
        return f"Image saved to: {image_path}"
        
    except httpx.HTTPError as e:
        return f"Error generating image: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
    

@click.command()
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio",
              help="Transport type (default: stdio)")
@click.option("--port", type=int, default=8000,
              help="Port for HTTP transport (default: 8000)")
def main(transport: str, port: int):
    """Image Generation MCP Server"""
    # Initialize and run the server with appropriate transport
    if transport == "http":
        mcp.run(transport="http", port=port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
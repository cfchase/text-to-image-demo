#!/usr/bin/env python3
"""Test script to verify the MCP server with diffusers-runtime integration"""

import asyncio
import httpx
import re
import os
import sys
from pathlib import Path
from fastmcp import Client

# Get MCP server URL from environment or use default
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
print(f"Using MCP server at: {MCP_URL}")

# Connect to the HTTP server
client = Client({"mcpServers": {
    "image_generator": {
        "transport": "http",
        "url": MCP_URL
    }
}})

async def download_image_from_url(url: str, filename: str):
    """Download image from URL and save it locally"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # Save image to test_output directory
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / filename
            output_path.write_bytes(response.content)
            
            print(f"  ✅ Downloaded image to: {output_path}")
            return output_path
    except Exception as e:
        print(f"  ❌ Failed to download image: {e}")
        return None


async def extract_and_download_image(result_data: str, test_name: str):
    """Extract URL from result and download image if it's a URL"""
    # Check if result contains a URL
    url_match = re.search(r'(https?://[^\s]+\.png)', result_data)
    if url_match:
        url = url_match.group(1)
        # Replace localhost:8080 with 127.0.0.1:8000 for port-forwarded access
        if "localhost:8080" in url:
            url = url.replace("localhost:8080", "127.0.0.1:8000")
        print(f"  🔗 Image URL: {url}")
        filename = f"{test_name}_{url.split('/')[-1]}"
        await download_image_from_url(url, filename)
    else:
        # Check if it's a file path
        path_match = re.search(r'Image saved to: (.+\.png)', result_data)
        if path_match:
            print(f"  📁 Image path: {path_match.group(1)}")
        else:
            print(f"  ⚠️  No image URL or path found in result")


async def test_generate_image():
    try:
        async with client:
            # Test 1: Simple prompt (fast)
            print("\n🎨 Test 1: Generating image with simple prompt...")
            result = await client.call_tool("generate_image", {
                "prompt": "a beautiful sunset over the ocean",
                "num_inference_steps": 20  # Faster for testing
            })
            print(f"Result: {result}")
            if hasattr(result, 'data'):
                await extract_and_download_image(result.data, "test1")
            print()
            
            # Test 2: With negative prompt
            print("🎨 Test 2: Generating image with negative prompt...")
            result = await client.call_tool("generate_image", {
                "prompt": "a futuristic city at night",
                "negative_prompt": "blurry, low quality, distorted",
                "num_inference_steps": 25  # Reasonable quality
            })
            print(f"Result: {result}")
            if hasattr(result, 'data'):
                await extract_and_download_image(result.data, "test2")
            print()
            
            # Test 3: Check if server handles errors gracefully
            print("🎨 Test 3: Testing error handling with invalid parameters...")
            try:
                result = await client.call_tool("generate_image", {
                    "prompt": "test image",
                    "num_inference_steps": -1  # Invalid value
                })
                print(f"Result: {result}")
            except Exception as e:
                print(f"  ✅ Error handled correctly: {e}")
            print()
            
            print("\n✅ All tests completed!")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_generate_image())
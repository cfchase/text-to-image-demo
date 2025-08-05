#!/usr/bin/env python3
"""Test script to verify the MCP server with diffusers-runtime integration"""

import asyncio
import httpx
import re
from pathlib import Path
from fastmcp import Client

# Connect to the HTTP server
client = Client({"mcpServers": {
    "image_generator": {
        "transport": "http",
        "url": "http://127.0.0.1:8000/mcp"
    }
}})

async def download_image_from_url(url: str, filename: str):
    """Download image from URL and save it locally"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url)
            response.raise_for_status()
            
            # Save image to test_output directory
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / filename
            output_path.write_bytes(response.content)
            
            print(f"  Downloaded image to: {output_path}")
            return output_path
    except Exception as e:
        print(f"  Failed to download image: {e}")
        return None


async def extract_and_download_image(result_data: str, test_name: str):
    """Extract URL from result and download image if it's a URL"""
    # Check if result contains a URL
    url_match = re.search(r'(https?://[^\s]+\.png)', result_data)
    if url_match:
        url = url_match.group(1)
        print(f"  Image URL: {url}")
        filename = f"{test_name}_{url.split('/')[-1]}"
        await download_image_from_url(url, filename)
    else:
        # Check if it's a file path
        path_match = re.search(r'Image saved to: (.+\.png)', result_data)
        if path_match:
            print(f"  Image path: {path_match.group(1)}")
        else:
            print(f"  No image URL or path found in result")


async def test_generate_image():
    async with client:
        # Test 1: Simple prompt
        print("Test 1: Generating image with simple prompt...")
        result = await client.call_tool("generate_image", {
            "prompt": "a beautiful sunset over the ocean"
        })
        print(f"Result: {result}")
        if hasattr(result, 'data'):
            await extract_and_download_image(result.data, "test1")
        print()
        
        # Test 2: With negative prompt
        print("Test 2: Generating image with negative prompt...")
        result = await client.call_tool("generate_image", {
            "prompt": "a futuristic city at night",
            "negative_prompt": "blurry, low quality, distorted"
        })
        print(f"Result: {result}")
        if hasattr(result, 'data'):
            await extract_and_download_image(result.data, "test2")
        print()
        
        # Test 3: With custom inference steps
        print("Test 3: Generating high-quality image with more inference steps...")
        result = await client.call_tool("generate_image", {
            "prompt": "a detailed painting of a forest with a waterfall",
            "negative_prompt": "cartoon, anime, unrealistic",
            "num_inference_steps": 60
        })
        print(f"Result: {result}")
        if hasattr(result, 'data'):
            await extract_and_download_image(result.data, "test3")
        print()
        
        print("\nAll tests completed!")

asyncio.run(test_generate_image())
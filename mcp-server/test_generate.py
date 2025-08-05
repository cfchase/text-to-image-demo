#!/usr/bin/env python3
"""Test script to verify the MCP server with diffusers-runtime integration"""

import asyncio
from fastmcp import Client

client = Client("main.py")

async def test_generate_image():
    async with client:
        # Test 1: Simple prompt
        print("Test 1: Generating image with simple prompt...")
        result = await client.call_tool("generate_image", {
            "prompt": "a beautiful sunset over the ocean"
        })
        print(f"Result: {result}")
        if hasattr(result, 'data'):
            print(f"Generated image: {result.data}\n")
        else:
            print(f"Full result: {result}\n")
        
        # Test 2: With negative prompt
        print("Test 2: Generating image with negative prompt...")
        result = await client.call_tool("generate_image", {
            "prompt": "a futuristic city at night",
            "negative_prompt": "blurry, low quality, distorted"
        })
        print(f"Result: {result}\n")
        
        # Test 3: With custom inference steps
        print("Test 3: Generating high-quality image with more inference steps...")
        result = await client.call_tool("generate_image", {
            "prompt": "a detailed painting of a forest with a waterfall",
            "negative_prompt": "cartoon, anime, unrealistic",
            "num_inference_steps": 60
        })
        print(f"Result: {result}\n")

asyncio.run(test_generate_image())
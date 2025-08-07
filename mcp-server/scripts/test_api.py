#!/usr/bin/env python3
"""Simple API test for the deployed MCP server"""

import httpx
import json
import os
import sys
from pathlib import Path
import time

# Get base URL from environment or use local default
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
print(f"Testing API at: {BASE_URL}")

def test_health():
    """Test the health endpoint"""
    print("\n1. Testing health endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Health check passed: {data}")
        return True
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

def test_image_list():
    """Test listing images"""
    print("\n2. Testing image list endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/images", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Image list retrieved: {len(data.get('images', []))} images")
        return True
    except Exception as e:
        print(f"   ❌ Image list failed: {e}")
        return False

def test_mcp_direct():
    """Test MCP endpoint directly with a tool call"""
    print("\n3. Testing MCP tool call directly...")
    
    # Create a direct MCP request for generate_image
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "generate_image",
            "arguments": {
                "prompt": "a simple test image of a red circle on white background",
                "num_inference_steps": 20
            }
        },
        "id": "test-1"
    }
    
    try:
        # MCP uses Server-Sent Events, so we need to handle streaming
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print("   📤 Sending MCP request...")
        response = httpx.post(
            f"{BASE_URL}/mcp/",
            headers=headers,
            json=mcp_request,
            timeout=60.0  # Image generation can take time
        )
        
        # Parse SSE response
        content = response.text
        print(f"   📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Extract data from SSE format
            for line in content.split('\n'):
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    if 'result' in data:
                        print(f"   ✅ Image generated: {data['result'].get('content', ['No content'])[0].get('text', 'No text')[:100]}")
                        return True
                    elif 'error' in data:
                        print(f"   ❌ MCP error: {data['error']}")
                        return False
        else:
            print(f"   ❌ Request failed: {content[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ MCP test failed: {e}")
        return False

def main():
    """Run all tests"""
    print(f"\n🧪 Running API tests for: {BASE_URL}\n")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Image List", test_image_list()))
    results.append(("MCP Tool Call", test_mcp_direct()))
    
    # Summary
    print("\n📊 Test Summary:")
    print("-" * 40)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print("-" * 40)
    print(f"Total: {passed}/{total} tests passed")
    
    # Exit with error if any test failed
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
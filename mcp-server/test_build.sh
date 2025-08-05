#!/bin/bash
# Test script to verify Docker build works correctly

echo "🔨 Building Docker image..."
CONTAINER_RUNTIME=docker make build

if [ $? -eq 0 ]; then
    echo "✅ Docker build successful!"
    
    echo "🔍 Checking image details..."
    docker images quay.io/cfchase/mcp-server:latest
    
    echo "📦 Testing container startup..."
    docker run --rm -d --name mcp-test \
        -e DIFFUSERS_RUNTIME_URL=http://test:8080 \
        -e PORT=8080 \
        -p 8080:8080 \
        quay.io/cfchase/mcp-server:latest
    
    sleep 5
    
    echo "🏥 Checking health endpoint..."
    curl -s http://localhost:8080/health || echo "Health check failed"
    
    echo "🧹 Cleaning up..."
    docker stop mcp-test 2>/dev/null || true
    
    echo "✅ Test complete!"
else
    echo "❌ Docker build failed!"
    exit 1
fi
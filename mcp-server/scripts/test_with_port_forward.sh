#!/bin/bash
# Test script that uses port forwarding to test the MCP server

echo "🚀 Starting test with port forwarding..."

# Get the pod name
POD=$(oc get pods -l app=image-generation-mcp -o jsonpath='{.items[0].metadata.name}')
if [ -z "$POD" ]; then
    echo "❌ No pod found for image-generation-mcp"
    exit 1
fi

echo "📦 Using pod: $POD"

# Start port forwarding in background
echo "🔗 Starting port forwarding..."
oc port-forward $POD 8000:8080 &
PF_PID=$!

# Give it time to start
sleep 3

# Run the test
echo "🧪 Running MCP test..."
MCP_URL="http://127.0.0.1:8000/mcp" .venv/bin/python scripts/test_generate.py

# Capture test result
TEST_RESULT=$?

# Kill port forwarding
echo "🛑 Stopping port forwarding..."
kill $PF_PID 2>/dev/null

# Exit with test result
exit $TEST_RESULT
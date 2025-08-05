#!/bin/bash
# Script to run both MCP server and image server with proper signal handling

# Trap SIGINT (Ctrl+C) to kill both processes
trap 'echo "Stopping servers..."; kill $IMAGE_PID $MCP_PID 2>/dev/null; exit' INT TERM

# Start image server in background
echo "Starting image server on port 8001..."
.venv/bin/python image_server.py --port 8001 &
IMAGE_PID=$!

# Wait a moment for image server to start
sleep 2

# Start MCP server in foreground
echo "Starting MCP server on port 8000 with image URL configured..."
IMAGE_SERVER_URL=http://localhost:8001 .venv/bin/python main.py --port 8000 &
MCP_PID=$!

# Wait for both processes
echo "Both servers running. Press Ctrl+C to stop."
wait $IMAGE_PID $MCP_PID
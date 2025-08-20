#!/bin/bash

# Build container images for registry
# Usage: ./scripts/build-images.sh [tag] [registry]

set -e

# Default values
TAG=${1:-latest}
REGISTRY=${2:-quay.io/cfchase}
PROJECT_NAME="chatbot"

echo "Building images with tag: $TAG"
echo "Registry: $REGISTRY"

# Build backend image
echo "Building backend image..."
docker build --platform linux/amd64 -t "${REGISTRY}/${PROJECT_NAME}-backend:${TAG}" ./backend

# Build frontend image
echo "Building frontend image..."
docker build --platform linux/amd64 -t "${REGISTRY}/${PROJECT_NAME}-frontend:${TAG}" ./frontend

echo "Images built successfully!"
echo "Backend: ${REGISTRY}/${PROJECT_NAME}-backend:${TAG}"
echo "Frontend: ${REGISTRY}/${PROJECT_NAME}-frontend:${TAG}"
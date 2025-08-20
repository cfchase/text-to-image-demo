#!/bin/bash

# Push container images to registry
# Usage: ./scripts/push-images.sh [tag] [registry]

set -e

# Default values
TAG=${1:-latest}
REGISTRY=${2:-quay.io/cfchase}
PROJECT_NAME="chatbot"

echo "Pushing images with tag: $TAG"
echo "Registry: $REGISTRY"

# Push backend image
echo "Pushing backend image..."
docker push "${REGISTRY}/${PROJECT_NAME}-backend:${TAG}"

# Push frontend image
echo "Pushing frontend image..."
docker push "${REGISTRY}/${PROJECT_NAME}-frontend:${TAG}"

echo "Images pushed successfully!"
echo "Backend: ${REGISTRY}/${PROJECT_NAME}-backend:${TAG}"
echo "Frontend: ${REGISTRY}/${PROJECT_NAME}-frontend:${TAG}"
#!/bin/bash

# Build and optionally apply kustomize configuration
# Usage: ./scripts/kustomize.sh [overlay] [--apply]

set -e

OVERLAY=${1:-deploy}
APPLY_FLAG=${2:-}

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "Error: kustomize is not installed or not in PATH"
    exit 1
fi

# Build the kustomize configuration
if [ "$APPLY_FLAG" == "--apply" ]; then
    # Check if oc is available for apply
    if ! command -v oc &> /dev/null; then
        echo "Error: oc (OpenShift CLI) is not installed or not in PATH"
        exit 1
    fi
    
    # Check if logged in to OpenShift
    if ! oc whoami &> /dev/null; then
        echo "Error: Not logged in to OpenShift. Please run 'oc login' first."
        exit 1
    fi
    
    echo "Building and applying kustomize configuration from overlay: $OVERLAY"
    kustomize build "k8s/overlays/$OVERLAY" | oc apply -f -
else
    echo "Building kustomize configuration from overlay: $OVERLAY"
    kustomize build "k8s/overlays/$OVERLAY"
fi
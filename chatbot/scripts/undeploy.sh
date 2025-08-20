#!/bin/bash

# Undeploy application from OpenShift/Kubernetes using kustomize
# Usage: ./scripts/undeploy.sh [overlay] [namespace]

set -e

OVERLAY=${1:-${OVERLAY:-deploy}}
NAMESPACE=${2:-${NAMESPACE:-chatbot}}

echo "Undeploying from overlay $OVERLAY..."
echo "Namespace: $NAMESPACE"

# Check if oc or kubectl is available
CLI_TOOL=""
if command -v oc &> /dev/null; then
    CLI_TOOL="oc"
    echo "Using OpenShift CLI (oc)"
elif command -v kubectl &> /dev/null; then
    CLI_TOOL="kubectl"
    echo "Using Kubernetes CLI (kubectl)"
else
    echo "Error: Neither oc (OpenShift CLI) nor kubectl (Kubernetes CLI) is installed or in PATH"
    exit 1
fi

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "Error: kustomize is not installed or not in PATH"
    exit 1
fi

# Check if logged in (for OpenShift) or cluster is accessible (for kubectl)
if [[ "$CLI_TOOL" == "oc" ]]; then
    if ! oc whoami &> /dev/null; then
        echo "Error: Not logged in to OpenShift. Please run 'oc login' first."
        exit 1
    fi
elif [[ "$CLI_TOOL" == "kubectl" ]]; then
    if ! kubectl cluster-info &> /dev/null; then
        echo "Error: Cannot access Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
fi

# Check if overlay directory exists
if [ ! -d "k8s/overlays/$OVERLAY" ]; then
    echo "Error: Overlay directory k8s/overlays/$OVERLAY does not exist"
    echo "Available overlays:"
    ls -d k8s/overlays/*/ 2>/dev/null | xargs -n1 basename
    exit 1
fi

# Delete resources using kustomize
echo "Deleting resources..."
# Build kustomize and delete from the specified namespace
# The sed commands ensure we're targeting the right namespace
kustomize build "k8s/overlays/$OVERLAY" | \
    sed "s|namespace: chatbot|namespace: $NAMESPACE|g" | \
    $CLI_TOOL delete -n "$NAMESPACE" -f - --ignore-not-found=true

echo "Undeploy complete!"
echo "Resources have been removed from namespace: $NAMESPACE"
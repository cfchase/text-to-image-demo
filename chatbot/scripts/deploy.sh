#!/bin/bash

# Deploy application to OpenShift/Kubernetes using kustomize
# Usage: ./scripts/deploy.sh [overlay] [namespace]
#
# Environment variables:
#   OVERLAY   - Kustomize overlay to use (default: deploy)
#   NAMESPACE - Kubernetes namespace (default: chatbot)
#   TAG       - Image tag to deploy (default: latest)
#   REGISTRY  - Container registry (default: quay.io/cfchase)

set -e

OVERLAY=${1:-${OVERLAY:-deploy}}
NAMESPACE=${2:-${NAMESPACE:-chatbot}}
TAG=${TAG:-latest}
REGISTRY=${REGISTRY:-quay.io/cfchase}

echo "Deploying chatbot application..."
echo "Overlay: $OVERLAY"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"

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
    echo "Install with: curl -s 'https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh' | bash"
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

# Check for required configuration files
if [ ! -f "k8s/overlays/$OVERLAY/.env" ]; then
    echo "Error: Missing .env file for $OVERLAY overlay"
    echo "Please copy .env.example to .env and configure with your values:"
    echo "  cp k8s/overlays/$OVERLAY/.env.example k8s/overlays/$OVERLAY/.env"
    echo "  # Edit k8s/overlays/$OVERLAY/.env with your API keys"
    exit 1
fi

if [ ! -f "k8s/overlays/$OVERLAY/mcp-config.json" ]; then
    echo "Warning: Missing mcp-config.json file for $OVERLAY overlay"
    echo "Creating default empty MCP configuration..."
    echo '{"mcpServers":{}}' > "k8s/overlays/$OVERLAY/mcp-config.json"
    echo "✅ Created k8s/overlays/$OVERLAY/mcp-config.json with empty MCP servers"
fi

# Create namespace if it doesn't exist
echo "Creating namespace if it doesn't exist..."
$CLI_TOOL create namespace "$NAMESPACE" --dry-run=client -o yaml | $CLI_TOOL apply -f -

# Build and apply kustomize configuration
echo "Building and applying kustomize configuration..."

# Build kustomize with namespace override and apply
# The sed commands update the namespace and image tags
kustomize build "k8s/overlays/$OVERLAY" | \
    sed "s|namespace: chatbot$|namespace: $NAMESPACE|g" | \
    sed "s|^\(  \)*namespace: chatbot$|namespace: $NAMESPACE|g" | \
    sed "s|$REGISTRY/chatbot-backend:latest|$REGISTRY/chatbot-backend:$TAG|g" | \
    sed "s|$REGISTRY/chatbot-frontend:latest|$REGISTRY/chatbot-frontend:$TAG|g" | \
    $CLI_TOOL apply -n "$NAMESPACE" -f -

echo "Deployment complete!"
echo "You can check the status with:"
echo "  $CLI_TOOL get pods -n $NAMESPACE"
if [[ "$CLI_TOOL" == "oc" ]]; then
    echo "  $CLI_TOOL get routes -n $NAMESPACE"
else
    echo "  $CLI_TOOL get ingress -n $NAMESPACE"
    echo "  $CLI_TOOL get services -n $NAMESPACE"
fi
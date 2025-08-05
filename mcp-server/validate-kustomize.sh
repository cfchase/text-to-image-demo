#!/bin/bash

# Validation script for MCP Server Kustomize deployments
# This script validates that all Kustomize overlays build successfully

set -e

echo "🔍 Validating MCP Server Kustomize Deployments..."
echo "================================================="

ENVIRONMENTS=("dev" "staging" "production")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUSTOMIZE_DIR="$SCRIPT_DIR/kustomize"

# Check if kustomize is installed
if ! command -v kustomize &> /dev/null; then
    echo "❌ Error: kustomize is not installed"
    echo "   Install with: brew install kustomize"
    exit 1
fi

echo "✅ kustomize found: $(kustomize version --short)"
echo ""

# Validate each environment
for env in "${ENVIRONMENTS[@]}"; do
    echo "🧪 Testing environment: $env"
    echo "----------------------------------------"
    
    overlay_dir="$KUSTOMIZE_DIR/overlays/$env"
    
    if [ ! -d "$overlay_dir" ]; then
        echo "❌ Error: Overlay directory not found: $overlay_dir"
        exit 1
    fi
    
    # Build the manifests
    echo "   Building manifests..."
    if ! kustomize build "$overlay_dir" > /tmp/mcp-server-$env.yaml 2>&1; then
        echo "❌ Error: Failed to build $env environment"
        cat /tmp/mcp-server-$env.yaml
        exit 1
    fi
    
    # Basic validation
    manifest_file="/tmp/mcp-server-$env.yaml"
    
    # Check for required resources
    required_resources=("Deployment" "Service" "Route" "ConfigMap")
    for resource in "${required_resources[@]}"; do
        if ! grep -q "kind: $resource" "$manifest_file"; then
            echo "❌ Error: Missing $resource in $env environment"
            exit 1
        fi
    done
    
    # Environment-specific validations
    case $env in
        "dev")
            if ! grep -q "namespace: mcp-server-dev" "$manifest_file"; then
                echo "❌ Error: Missing dev namespace"
                exit 1
            fi
            if ! grep -q "PersistentVolumeClaim" "$manifest_file"; then
                echo "❌ Error: Dev should have PVC"
                exit 1
            fi
            if grep -q "tls:" "$manifest_file"; then
                echo "❌ Error: Dev should not have TLS (HTTP only)"
                exit 1
            fi
            if ! grep -q "LOG_LEVEL: DEBUG" "$manifest_file"; then
                echo "❌ Error: Dev should have DEBUG logging"
                exit 1
            fi
            ;;
        "staging")
            if ! grep -q "namespace: mcp-server-staging" "$manifest_file"; then
                echo "❌ Error: Missing staging namespace"
                exit 1
            fi
            if ! grep -q "emptyDir:" "$manifest_file"; then
                echo "❌ Error: Staging should use emptyDir storage"
                exit 1
            fi
            if ! grep -q "tls:" "$manifest_file"; then
                echo "❌ Error: Staging should have TLS"
                exit 1
            fi
            if ! grep -q "mcp-server-images" "$manifest_file"; then
                echo "❌ Error: Staging should have images route"
                exit 1
            fi
            ;;
        "production")
            if ! grep -q "namespace: mcp-server-production" "$manifest_file"; then
                echo "❌ Error: Missing production namespace"
                exit 1
            fi
            if ! grep -q "PersistentVolumeClaim" "$manifest_file"; then
                echo "❌ Error: Production should have PVC"
                exit 1
            fi
            if ! grep -q "HorizontalPodAutoscaler" "$manifest_file"; then
                echo "❌ Error: Production should have HPA"
                exit 1
            fi
            if ! grep -q "NetworkPolicy" "$manifest_file"; then
                echo "❌ Error: Production should have NetworkPolicy"
                exit 1
            fi
            if ! grep -q "PodDisruptionBudget" "$manifest_file"; then
                echo "❌ Error: Production should have PodDisruptionBudget"
                exit 1
            fi
            if ! grep -q "replicas: 2" "$manifest_file"; then
                echo "❌ Error: Production should have 2 replicas"
                exit 1
            fi
            ;;
    esac
    
    # Count resources
    resource_count=$(grep -c "^kind:" "$manifest_file" || true)
    echo "   ✅ Built successfully ($resource_count resources)"
    
    # Clean up temp file
    rm -f "$manifest_file"
    echo ""
done

# Validate Makefile targets exist
echo "🔧 Validating Makefile targets..."
echo "----------------------------------------"

makefile="$SCRIPT_DIR/Makefile"
required_targets=("deploy-dev" "deploy-staging" "deploy-prod" "kustomize-build" "kustomize-diff")

for target in "${required_targets[@]}"; do
    if ! grep -q "^$target:" "$makefile"; then
        echo "❌ Error: Missing Makefile target: $target"
        exit 1
    fi
done

echo "   ✅ All required Makefile targets found"
echo ""

# Summary
echo "🎉 Validation Complete!"
echo "======================="
echo "✅ All 3 environments build successfully"
echo "✅ All required resources present"
echo "✅ Environment-specific configurations validated"
echo "✅ Makefile targets available"
echo ""
echo "Ready to deploy:"
echo "  make deploy-dev      # Development environment"
echo "  make deploy-staging  # Staging environment"  
echo "  make deploy-prod     # Production environment"
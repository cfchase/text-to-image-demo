# MCP Server + Diffusers-Runtime Integration Guide

This document explains how to deploy and integrate the MCP server with diffusers-runtime services in OpenShift, covering service discovery, networking, and troubleshooting.

## Architecture Overview

The integrated solution consists of two main components:

1. **Diffusers-Runtime**: KServe InferenceService that provides the AI model serving capabilities
   - Deployed as KServe InferenceService
   - Exposes REST API on port 8080
   - Typically deployed in the user's current namespace (often `default`)

2. **MCP Server**: Model Context Protocol server that provides image generation capabilities
   - Deployed in dedicated namespaces (`mcp-server-dev`, `mcp-server-staging`, `mcp-server-production`)
   - Acts as a client to diffusers-runtime
   - Provides MCP interface and HTTP REST API

## Service Discovery Patterns

### Kubernetes Service Discovery

Services communicate using Kubernetes DNS:
```
http://<service-name>.<namespace>.svc.cluster.local:<port>
```

### Environment-Specific Service Mappings

| Environment | MCP Namespace | Diffusers Service | Service URL |
|-------------|---------------|-------------------|-------------|
| Development | `mcp-server-dev` | `tiny-sd` | `http://tiny-sd.default.svc.cluster.local:8080` |
| Staging | `mcp-server-staging` | `tiny-sd` | `http://tiny-sd.default.svc.cluster.local:8080` |
| Production | `mcp-server-production` | `redhat-dog` | `http://redhat-dog.default.svc.cluster.local:8080` |

## Deployment Scenarios

### Quick Start: Complete Stack Deployment

Deploy both services together with a single command:

```bash
# Development stack (CPU-based, minimal resources)
make deploy-with-diffusers-dev

# Production stack (GPU-based, high availability)
make deploy-with-diffusers-prod
```

### Manual Step-by-Step Deployment

1. **Deploy Diffusers-Runtime First**:
   ```bash
   # For development/staging
   oc apply -f ../diffusers-runtime/templates/tiny-sd.yaml
   
   # For production
   oc apply -f ../diffusers-runtime/templates/redhat-dog.yaml
   ```

2. **Wait for Diffusers-Runtime to be Ready**:
   ```bash
   # Check status
   oc get inferenceservice
   oc get pods -l serving.kserve.io/inferenceservice=tiny-sd
   
   # Wait for ready state
   oc wait --for=condition=Ready pod -l serving.kserve.io/inferenceservice=tiny-sd --timeout=600s
   ```

3. **Deploy MCP Server**:
   ```bash
   # Choose environment
   make deploy-dev      # Development
   make deploy-staging  # Staging
   make deploy-prod     # Production
   ```

## Network Configuration

### Cross-Namespace Communication

MCP server runs in dedicated namespaces but needs to communicate with diffusers-runtime services in the default namespace.

#### NetworkPolicy Configuration

Production environments include NetworkPolicy rules that:
- Allow DNS resolution
- Allow outbound connections to diffusers-runtime services
- Allow inbound connections from OpenShift router
- Block other unnecessary traffic

#### Service Dependencies

The MCP server deployment includes an init container that:
- Waits for diffusers-runtime service to become available
- Tests connectivity before starting the main container
- Provides clear error messages if services are unavailable
- Times out after 5 minutes with helpful troubleshooting information

## Environment Variables

### MCP Server Configuration

Key environment variables for service discovery:

```bash
# Service URL (auto-configured per environment)
DIFFUSERS_RUNTIME_URL=http://tiny-sd.default.svc.cluster.local:8080

# Service identification (for diagnostics)
DIFFUSERS_RUNTIME_SERVICE=tiny-sd
DIFFUSERS_RUNTIME_NAMESPACE=default

# Model identifier
DIFFUSERS_MODEL_ID=model
```

### Diffusers-Runtime Configuration

The diffusers-runtime services use these environment variables for optimization:

```bash
# Data type selection
DTYPE=auto                    # Options: auto, bfloat16, float16, float32, native

# Memory optimizations
ENABLE_LOW_CPU_MEM=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_SLICING=true
ENABLE_CPU_OFFLOAD=true
```

## Testing and Validation

### Connectivity Testing

Test network connectivity between services:

```bash
# Test connectivity for specific environment
make test-connectivity ENV=dev
make test-connectivity ENV=staging
make test-connectivity ENV=production
```

### End-to-End Integration Testing

Test complete image generation workflow:

```bash
# Test image generation through MCP server
make test-integration ENV=dev
make test-integration ENV=staging
make test-integration ENV=production
```

### Service Status Checks

Check the status of all deployed services:

```bash
# Check all services for specific environment
make check-services ENV=dev
make check-services ENV=staging
make check-services ENV=production
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. MCP Server Cannot Reach Diffusers-Runtime

**Symptoms:**
- MCP server pod stuck in `Init:0/1` state
- Init container logs show connection timeouts
- HTTP 503 errors from image generation endpoints

**Diagnosis:**
```bash
# Check if diffusers-runtime service exists
oc get inferenceservice

# Check diffusers-runtime pod status
oc get pods -l serving.kserve.io/inferenceservice=tiny-sd

# Check diffusers-runtime logs
oc logs -l serving.kserve.io/inferenceservice=tiny-sd

# Test connectivity from MCP server pod
make test-connectivity ENV=dev
```

**Solutions:**
- Ensure diffusers-runtime InferenceService is deployed and ready
- Verify diffusers-runtime pod is not crash-looping
- Check NetworkPolicy rules allow cross-namespace communication
- Verify DNS resolution is working

#### 2. Diffusers-Runtime Pod Not Ready

**Symptoms:**
- Diffusers-runtime pod in `Pending` or `CrashLoopBackOff` state
- Long startup times for model loading
- GPU resource allocation issues

**Diagnosis:**
```bash
# Check pod status and events
oc describe pod -l serving.kserve.io/inferenceservice=tiny-sd

# Check resource allocation
oc get pods -o yaml -l serving.kserve.io/inferenceservice=tiny-sd

# Check logs
oc logs -l serving.kserve.io/inferenceservice=tiny-sd
```

**Solutions:**
- Ensure sufficient resources (CPU, memory, GPU) are available
- Check that GPU nodes are available for production workloads
- Verify model storage is accessible (S3, PVC, HuggingFace Hub)
- Wait longer for model download and loading (can take 5-10 minutes)

#### 3. Network Policy Blocking Communication

**Symptoms:**
- Connectivity tests fail
- DNS resolution works but HTTP requests timeout
- Services exist but are unreachable

**Diagnosis:**
```bash
# Check NetworkPolicy rules
oc get networkpolicies -n mcp-server-dev
oc describe networkpolicy mcp-server-netpol-dev -n mcp-server-dev

# Check if default namespace has NetworkPolicies
oc get networkpolicies -n default
```

**Solutions:**
- Review and update NetworkPolicy egress rules
- Ensure correct namespace labels for namespace selectors
- Verify KServe labels on diffusers-runtime pods
- Temporarily remove NetworkPolicy for testing (development only)

#### 4. Route/Ingress Issues

**Symptoms:**
- MCP server endpoints not accessible from outside cluster
- TLS/SSL certificate issues
- Route not found errors

**Diagnosis:**
```bash
# Check routes
oc get routes -n mcp-server-dev

# Check route details
oc describe route mcp-server -n mcp-server-dev

# Test from inside cluster
oc exec -n mcp-server-dev deployment/mcp-server -- curl localhost:8000/health
```

**Solutions:**
- Verify route configuration in Kustomize overlays
- Check if OpenShift router is healthy
- For development, use HTTP routes; for production, use HTTPS
- Verify DNS resolution for external access

### Diagnostic Commands

```bash
# Check all services status
make check-services ENV=dev

# View MCP server logs
make logs ENV=dev

# Check diffusers-runtime logs
oc logs -l serving.kserve.io/inferenceservice=tiny-sd -f

# Test connectivity
make test-connectivity ENV=dev

# Full integration test
make test-integration ENV=dev

# Check resource usage
oc top pods -n mcp-server-dev
oc top pods -l serving.kserve.io/inferenceservice=tiny-sd
```

## Performance Considerations

### Resource Requirements

#### Development Environment
- MCP Server: 128Mi-512Mi memory, 50m-250m CPU
- Diffusers-Runtime (tiny-sd): 4-8Gi memory, 1-4 CPU cores
- Total: ~4-8Gi memory, ~1-4 CPU cores

#### Production Environment
- MCP Server: 512Mi-2Gi memory, 200m-1000m CPU (2+ replicas)
- Diffusers-Runtime (redhat-dog): 8-64Gi memory, 1-6 CPU, 1 GPU
- Total: ~8-66Gi memory, ~1-7 CPU cores, 1 GPU

### Scaling Considerations

- **MCP Server**: Horizontally scalable, stateless
- **Diffusers-Runtime**: Typically single replica due to GPU constraints
- **Bottleneck**: Usually the diffusers-runtime service due to model inference time

### Optimization Tips

1. **Development**: Use tiny-sd model for faster iteration
2. **Production**: Use GPU-optimized models (redhat-dog)
3. **Memory**: Enable memory optimizations in diffusers-runtime
4. **Caching**: Consider persistent storage for model caching
5. **Load Balancing**: Scale MCP server replicas, not diffusers-runtime

## Security Best Practices

### Network Security
- Use NetworkPolicies to restrict communication
- Limit egress to necessary services only
- Use namespace isolation
- Enable TLS for production routes

### Container Security
- Run as non-root user
- Use read-only root filesystem where possible
- Drop unnecessary capabilities
- Use security context constraints (SCCs)
- Enable seccomp profiles

### Secret Management
- Use Kubernetes secrets for sensitive data
- Avoid hardcoding credentials in configurations
- Rotate credentials regularly
- Use service accounts with minimal privileges

## Monitoring and Observability

### Health Checks
- Both services provide `/health` endpoints
- Kubernetes liveness and readiness probes configured
- Startup probes for longer initialization times

### Metrics
- Prometheus metrics available on port 8888 (diffusers-runtime)
- Custom metrics can be added for MCP server operations
- Resource usage monitoring through OpenShift console

### Logging
- Structured logging with configurable levels
- Centralized log aggregation through OpenShift logging
- Debug logging available for development environments

## Next Steps

1. **Deploy a test environment**: Start with `make deploy-with-diffusers-dev`
2. **Run connectivity tests**: Use `make test-connectivity ENV=dev`
3. **Test image generation**: Use `make test-integration ENV=dev`
4. **Monitor performance**: Check resource usage and scaling needs
5. **Configure production**: Deploy with `make deploy-with-diffusers-prod`

For additional support, check the project README and individual component documentation.
# MCP Server OpenShift Deployment Guide

This guide covers deploying the MCP (Model Context Protocol) server to OpenShift with production-ready configurations.

## Prerequisites

1. **OpenShift Cluster Access**
   - OpenShift 4.10+ with GPU support (if using GPU-accelerated diffusers-runtime)
   - Admin or project admin permissions
   - `oc` CLI tool installed and configured

2. **Container Registry Access**
   - Push access to a container registry (default: quay.io/cfchase)
   - Podman or Docker installed locally

3. **Dependencies**
   - Diffusers-runtime service already deployed in the same namespace
   - S3-compatible storage configured (if using S3-based models)

## Quick Start

### 1. Build and Deploy (Basic Configuration)

```bash
# Build container image
make build

# Push to registry
make push

# Deploy to OpenShift (choose environment)
make deploy-dev      # Development
make deploy-staging  # Staging
make deploy-prod     # Production
```

### 2. Production Deployment

```bash
# Build and deploy with production settings
make build-and-deploy-prod

# Or deploy other environments
make build-and-deploy-dev     # Development
make build-and-deploy-staging  # Staging
```

## Deployment Configurations

The MCP server uses Kustomize for deployment management with three environment overlays:

### Development Environment (`make deploy-dev`)

- **Replicas**: 1
- **Resources**: 128Mi-512Mi memory, 50m-200m CPU
- **Storage**: 5Gi PVC for image storage
- **Security**: Basic network policies, non-root user
- **Monitoring**: Basic health checks
- **Routing**: HTTP (no TLS) for easier debugging

**Use for**: Local development, testing, debugging

### Staging Environment (`make deploy-staging`)

- **Replicas**: 1
- **Resources**: 256Mi-1Gi memory, 100m-500m CPU
- **Storage**: Ephemeral (emptyDir) - data lost on restart
- **Security**: Non-root user, minimal permissions
- **Monitoring**: Health checks and readiness probes
- **Routing**: HTTPS with TLS termination

**Use for**: Testing, CI/CD pipelines, non-persistent scenarios

### Production Environment (`make deploy-prod`)

- **Replicas**: 2-5 (auto-scaling based on CPU/memory)
- **Resources**: 512Mi-2Gi memory, 200m-1000m CPU
- **Storage**: 50Gi PVC for persistent image storage
- **Security**: Network policies, pod disruption budgets, security contexts
- **Monitoring**: Advanced health checks, startup probes
- **Networking**: Rate limiting, connection management

**Use for**: Production environments, high-availability requirements

## Configuration Options

### Environment Variables

Configure the MCP server through the ConfigMap:

```yaml
data:
  DIFFUSERS_RUNTIME_URL: "http://tiny-sd:8080"  # Diffusers service endpoint
  DIFFUSERS_MODEL_ID: "model"                   # Model identifier
  IMAGE_OUTPUT_PATH: "/opt/app-root/src/images"  # Container image storage path
  PORT: "8080"                                   # Server port
  LOG_LEVEL: "INFO"                             # Logging level
```

### Storage Configuration

The deployment uses a PersistentVolumeClaim for storing generated images:

- **Basic**: 10Gi storage
- **Production**: 50Gi storage
- **Storage Class**: `gp3-csi` (adjust based on your cluster)

### Resource Management

#### Basic Configuration
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

#### Production Configuration
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

## Security Features

### Container Security
- Non-root user (UID 1001)
- Read-only root filesystem
- No privilege escalation
- Dropped capabilities
- SecComp profile enforcement

### Network Security
- Network policies restricting ingress/egress
- TLS termination at route level
- Rate limiting on routes
- CORS headers for image serving

### OpenShift Security
- Security Context Constraints (SCC) compliance
- Service account with minimal permissions
- Pod security standards enforcement

## Monitoring and Observability

### Health Checks

The MCP server provides three types of health checks:

1. **Liveness Probe**: `/health` endpoint (checks if application is running)
2. **Readiness Probe**: `/health` endpoint (checks if ready to serve traffic)
3. **Startup Probe**: `/health` endpoint (allows extended startup time)

### Logging

Access logs using:

```bash
# Follow logs for all MCP server pods
make logs

# Get logs for specific pod
oc logs -f deployment/mcp-server
```

### Metrics and Monitoring

The deployment is prepared for monitoring integration:

- Prometheus annotations ready
- Health check endpoints exposed
- Resource usage tracking enabled

## Networking and Access

### Routes and Endpoints

After deployment, the MCP server exposes:

1. **MCP Protocol Endpoint**: `https://<route-host>/mcp`
2. **Image Server Endpoint**: `https://<route-host>/images`
3. **Health Check Endpoint**: `https://<route-host>/health`
4. **API Documentation**: `https://<route-host>/docs`

### Service Discovery

The diffusers-runtime service is accessed via:
- Service Name: `tiny-sd` (default)
- Port: `8080`
- Protocol: HTTP

## Scaling and Performance

### Horizontal Pod Autoscaling (Production)

The production deployment includes HPA configuration:

- **Min Replicas**: 2
- **Max Replicas**: 5
- **CPU Target**: 70% utilization
- **Memory Target**: 80% utilization

### Performance Tuning

1. **Container Resources**: Adjust based on expected load
2. **Storage**: Use fast storage classes for image operations
3. **Network**: Enable HTTP/2 for better performance
4. **Route Timeouts**: Set to 300s for image generation requests

## Troubleshooting

### Common Issues

1. **Pod Not Starting**
   ```bash
   oc describe pod -l app=mcp-server
   oc logs -l app=mcp-server
   ```

2. **Cannot Connect to Diffusers Runtime**
   ```bash
   # Check if diffusers-runtime service exists
   oc get svc tiny-sd
   
   # Test connectivity from MCP server pod
   oc exec deployment/mcp-server -- curl http://tiny-sd:8080/health
   ```

3. **Storage Issues**
   ```bash
   # Check PVC status
   oc get pvc mcp-server-images
   
   # Check volume mounts
   oc describe pod -l app=mcp-server
   ```

4. **Route/Network Issues**
   ```bash
   # Check route configuration
   oc get route mcp-server -o yaml
   
   # Test external connectivity
   curl https://$(oc get route mcp-server -o jsonpath='{.spec.host}')/health
   ```

### Debugging Commands

```bash
# Show deployment status
make status

# Get all resources
oc get all -l app=mcp-server

# Describe deployment
oc describe deployment mcp-server

# Check events
oc get events --sort-by='.lastTimestamp' | grep mcp-server
```

## Maintenance

### Updates and Rollouts

1. **Update Container Image**
   ```bash
   # Build new image
   make build IMAGE_TAG=v1.1.0
   make push IMAGE_TAG=v1.1.0
   
   # Update deployment
   oc set image deployment/mcp-server mcp-server=quay.io/cfchase/mcp-server:v1.1.0
   ```

2. **Configuration Updates**
   ```bash
   # Edit ConfigMap
   oc edit configmap mcp-server-config
   
   # Restart deployment to pick up changes
   oc rollout restart deployment/mcp-server
   ```

3. **Rollback**
   ```bash
   # View rollout history
   oc rollout history deployment/mcp-server
   
   # Rollback to previous version
   oc rollout undo deployment/mcp-server
   ```

### Backup and Recovery

1. **Backup Generated Images**
   ```bash
   # Create backup of PVC data
   oc create job backup-images --image=registry.redhat.io/ubi9/ubi:latest \
     --command -- tar czf /backup/images-$(date +%Y%m%d).tar.gz /app/images
   ```

2. **Disaster Recovery**
   ```bash
   # Redeploy from backup
   make undeploy
   make deploy
   # Restore image data from backup
   ```

## Security Best Practices

1. **Regular Updates**: Keep container images updated with security patches
2. **Access Control**: Use RBAC to limit access to deployment resources
3. **Network Isolation**: Leverage network policies to restrict communication
4. **Secret Management**: Store sensitive data in OpenShift Secrets
5. **Image Scanning**: Scan container images for vulnerabilities before deployment
6. **Audit Logging**: Enable OpenShift audit logging for compliance

## Performance Optimization

1. **Resource Sizing**: Monitor actual usage and adjust resource requests/limits
2. **Storage Performance**: Use SSD-backed storage classes for better I/O
3. **Network Optimization**: Enable HTTP/2 and connection pooling
4. **Caching**: Implement image caching strategies for frequently accessed content
5. **Load Testing**: Perform load testing to validate performance under expected load

## Support and Monitoring

For production deployments, consider:

1. **Monitoring Stack**: Deploy Prometheus and Grafana for metrics
2. **Alerting**: Set up alerts for pod failures, high resource usage
3. **Log Aggregation**: Use OpenShift logging or external solutions
4. **Backup Strategy**: Implement automated backup of generated images
5. **Documentation**: Maintain runbooks for operational procedures
# MCP Server Kustomize Deployments

This directory contains Kustomize manifests for deploying the MCP (Model Control Protocol) Server across different environments with a DRY (Don't Repeat Yourself) approach.

## Structure

```
kustomize/
├── README.md
├── base/                           # Common resources shared across environments
│   ├── kustomization.yaml         # Base configuration with common labels/annotations
│   ├── deployment.yaml            # Core deployment manifest
│   ├── service.yaml               # Service definition
│   └── route.yaml                 # OpenShift route
└── overlays/                      # Environment-specific configurations
    ├── dev/                       # Development environment
    │   ├── kustomization.yaml     # Dev-specific patches and configs
    │   └── pvc.yaml               # Persistent volume claim (5Gi)
    ├── staging/                   # Staging environment  
    │   ├── kustomization.yaml     # Staging-specific patches
    │   └── images-route.yaml      # Additional route for image access
    └── production/                # Production environment
        ├── kustomization.yaml     # Production-specific patches
        ├── pvc.yaml               # Production PVC (50Gi, specific storage class)
        ├── secret.yaml            # Production secrets
        ├── networkpolicy.yaml     # Network security policies
        ├── poddisruptionbudget.yaml # High availability settings
        ├── hpa.yaml               # Horizontal Pod Autoscaler
        └── headless-service.yaml  # Headless service for StatefulSet patterns
```

## Environment Configurations

### Development (`dev`)
- **Namespace**: `mcp-server-dev`
- **Storage**: 5Gi PVC (persistent)
- **Security**: HTTP only (no TLS for easier debugging)
- **Resources**: Minimal (128Mi RAM, 50m CPU requests)
- **Logging**: DEBUG level
- **Health Checks**: Fast (5-15 second intervals)
- **Replicas**: 1

### Staging (`staging`)
- **Namespace**: `mcp-server-staging`
- **Storage**: Ephemeral (emptyDir with 5Gi limit)
- **Security**: HTTPS with TLS termination
- **Resources**: Standard (256Mi RAM, 100m CPU requests)
- **Logging**: INFO level
- **Health Checks**: Standard (10-30 second intervals)
- **Rate Limiting**: 50 concurrent connections
- **Replicas**: 1

### Production (`production`)
- **Namespace**: `mcp-server-production`
- **Storage**: 50Gi PVC with `gp3-csi` storage class
- **Security**: HTTPS + NetworkPolicy + enhanced security context
- **Resources**: Enhanced (512Mi-2Gi RAM, 200m-1000m CPU)
- **Logging**: INFO level
- **High Availability**: 2-5 replicas with anti-affinity
- **Autoscaling**: HPA based on CPU (70%) and Memory (80%)
- **Reliability**: PodDisruptionBudget, startup/liveness/readiness probes
- **Rate Limiting**: 100 concurrent connections, 1000 req/sec
- **Replicas**: 2-5 (auto-scaling)

## Usage

### Building Manifests

```bash
# Build manifests for a specific environment
make kustomize-build ENV=dev
make kustomize-build ENV=staging  
make kustomize-build ENV=production

# Or use kustomize directly
kustomize build kustomize/overlays/dev
kustomize build kustomize/overlays/staging
kustomize build kustomize/overlays/production
```

### Deploying

```bash
# Deploy to development
make deploy-dev

# Deploy to staging  
make deploy-staging

# Deploy to production (with confirmation prompt)
make deploy-prod

# Build, push image, and deploy in one command
make build-and-deploy-dev
make build-and-deploy-staging
make build-and-deploy-prod
```

### Managing Deployments

```bash
# Check status across all environments
make status

# View logs from specific environment
make logs ENV=dev
make logs ENV=staging
make logs ENV=production

# Show diff between current deployment and manifests
make kustomize-diff ENV=production

# Remove deployments
make undeploy-dev      # Prompts for PVC deletion
make undeploy-staging  # No persistent storage to worry about
make undeploy-prod     # Prompts for PVC deletion
```

## Key Features

### ConfigMap Generation
- Base configuration generated via `configMapGenerator`
- Environment-specific variables merged using `behavior: merge`
- Automatic hash suffixes for config change detection

### Resource Patches
- JSON patches for environment-specific resource modifications
- Resource limits, health check intervals, replica counts
- Security contexts and storage configurations

### Storage Strategy
- **Development**: PVC for persistent debugging data
- **Staging**: EmptyDir for clean testing environment  
- **Production**: Large PVC with specific storage class

### Security Layers
- Pod Security Context with non-root user (1001)
- Container Security Context with dropped capabilities
- Network Policies (production only)
- Read-only root filesystem (production)
- Security Context Constraints compatible with OpenShift

### Observability
- Consistent labeling across all environments
- Environment-specific annotations
- Prometheus scraping annotations
- Health check endpoints at `/health`

## Customization

### Adding New Environments
1. Create new overlay directory: `kustomize/overlays/myenv/`
2. Create `kustomization.yaml` referencing `../../base`
3. Add environment-specific patches and resources
4. Update Makefile with new deployment targets

### Modifying Base Resources
Edit files in `kustomize/base/` to change configurations shared across all environments.

### Environment-Specific Changes
Use JSON patches in overlay `kustomization.yaml` files to modify base resources for specific environments.

## Best Practices Implemented

1. **DRY Principle**: Common resources in base, variations in overlays
2. **Environment Isolation**: Separate namespaces per environment
3. **Security First**: Non-root containers, dropped capabilities, network policies
4. **High Availability**: Anti-affinity, PDB, HPA for production
5. **Observability**: Consistent labeling, health checks, logging levels
6. **Resource Management**: Environment-appropriate resource limits
7. **Configuration Management**: ConfigMaps with automatic hash suffixes
8. **Storage Strategy**: Environment-appropriate storage solutions

## Troubleshooting

### Common Issues

1. **Kustomize not found**: Install with `brew install kustomize` or download from releases
2. **Storage class issues**: Update PVC `storageClassName` in overlay files
3. **Resource limits**: Adjust requests/limits in patches for your cluster capacity
4. **Network policies**: May need adjustment for your cluster's CNI and namespace labels

### Validation

```bash
# Validate YAML syntax
kustomize build kustomize/overlays/production | kubectl --dry-run=client apply -f -

# Check resource requirements
kustomize build kustomize/overlays/production | grep -A 10 resources:
```
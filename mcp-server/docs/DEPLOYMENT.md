# Deployment Guide

This guide covers multiple deployment scenarios for the MCP Image Generation Server, from local development to production Kubernetes deployments.

## Quick Start

### Local Development

```bash
# Clone and setup
git clone <repository-url>
cd mcp-server
pip install -e ".[dev]"

# Set environment variables
export KSERVE_ENDPOINT="http://localhost:8080/v1/models/stable-diffusion"
export STORAGE_BACKEND="file"
export STORAGE_PATH="/tmp/mcp-images"

# Run the server
python -m mcp_server.main dev
```

### Docker

```bash
# Build and run
docker build -t mcp-image-server -f deployment/docker/Dockerfile .
docker run -p 8000:8000 \
  -e KSERVE_ENDPOINT="http://host.docker.internal:8080/v1/models/stable-diffusion" \
  mcp-image-server
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/k8s/
```

## Deployment Scenarios

### 1. Local Development

**Use Case**: Development and testing on local machine

**Setup**:
```bash
# Install dependencies
pip install -e ".[dev]"

# Create environment file
cat > .env << EOF
SERVICE_NAME=mcp-image-server
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8000
STORAGE_BACKEND=file
STORAGE_PATH=/tmp/mcp-images
KSERVE_ENDPOINT=http://localhost:8080/v1/models/stable-diffusion
KSERVE_MODEL_NAME=stable-diffusion
IMAGE_CLEANUP_INTERVAL=60
IMAGE_TTL=300
EOF

# Run with auto-reload
python -m mcp_server.main dev
```

**Testing**:
```bash
# Health check
curl http://localhost:8000/health

# Test image generation via MCP
# (Use MCP client or test through API endpoints)
```

### 2. Docker Container

**Use Case**: Containerized deployment for single node or Docker Compose

#### Basic Docker Run

```bash
# Build the image
docker build -t mcp-image-server \
  --target production \
  -f deployment/docker/Dockerfile .

# Run with file storage
docker run -d \
  --name mcp-image-server \
  -p 8000:8000 \
  -v /host/storage:/app/storage \
  -e KSERVE_ENDPOINT="http://diffusers-runtime:8080/v1/models/stable-diffusion" \
  -e STORAGE_BACKEND="file" \
  -e STORAGE_PATH="/app/storage" \
  mcp-image-server
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-image-server:
    build:
      context: .
      dockerfile: deployment/docker/Dockerfile
      target: production
    ports:
      - "8000:8000"
    environment:
      - KSERVE_ENDPOINT=http://diffusers-runtime:8080/v1/models/stable-diffusion
      - STORAGE_BACKEND=file
      - STORAGE_PATH=/app/storage
      - LOG_LEVEL=INFO
    volumes:
      - ./storage:/app/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Optional: nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - mcp-image-server
```

#### With S3 Storage

```bash
docker run -d \
  --name mcp-image-server \
  -p 8000:8000 \
  -e KSERVE_ENDPOINT="http://diffusers-runtime:8080/v1/models/stable-diffusion" \
  -e STORAGE_BACKEND="s3" \
  -e S3_BUCKET="my-image-bucket" \
  -e S3_PREFIX="mcp-images/" \
  -e AWS_ACCESS_KEY_ID="your-access-key" \
  -e AWS_SECRET_ACCESS_KEY="your-secret-key" \
  -e AWS_REGION="us-east-1" \
  mcp-image-server
```

### 3. Kubernetes Deployment

**Use Case**: Production deployment with scaling, high availability, and cloud integration

#### Prerequisites

```bash
# Ensure kubectl is configured
kubectl cluster-info

# Create namespace (optional)
kubectl create namespace mcp-image-server
```

#### File Storage Deployment

**Best for**: Single availability zone, cost-effective storage

```bash
# Deploy with file storage (uses PVC)
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/secret.yaml  # After configuring secrets

# Edit deployment to use file storage config
kubectl patch deployment mcp-image-server \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","envFrom":[{"configMapRef":{"name":"mcp-image-server-config-prod-file"}}]}]}}}}'

kubectl apply -f deployment/k8s/deployment.yaml
kubectl apply -f deployment/k8s/service.yaml
```

**Create PVC for file storage**:
```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mcp-image-server-storage
spec:
  accessModes:
    - ReadWriteMany  # Required for multiple pods
  resources:
    requests:
      storage: 50Gi
  storageClassName: nfs  # Use appropriate storage class
```

#### S3 Storage Deployment

**Best for**: Multi-zone, scalable, production deployments

```bash
# Create S3 secrets
kubectl create secret generic mcp-image-server-secrets \
  --from-literal=aws_access_key_id="your-access-key" \
  --from-literal=aws_secret_access_key="your-secret-key"

# Deploy with S3 storage config
kubectl apply -f deployment/k8s/configmap.yaml

# Update deployment to use S3 config
kubectl patch deployment mcp-image-server \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","envFrom":[{"configMapRef":{"name":"mcp-image-server-config-prod-s3"}}]}]}}}}'

kubectl apply -f deployment/k8s/deployment.yaml
kubectl apply -f deployment/k8s/service.yaml
```

#### Expose Service

**Option 1: LoadBalancer (Cloud)**
```bash
kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  name: mcp-image-server-lb
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: mcp-image-server
EOF
```

**Option 2: Ingress (Recommended)**
```bash
# Install ingress controller (if not present)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Create ingress
kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-image-server-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - mcp-image-server.yourdomain.com
    secretName: mcp-image-server-tls
  rules:
  - host: mcp-image-server.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-image-server
            port:
              number: 8000
EOF
```

### 4. OpenShift Deployment

**Use Case**: Red Hat OpenShift environments

```bash
# Login to OpenShift
oc login --token=your-token --server=https://api.cluster.com:6443

# Create project
oc new-project mcp-image-server

# Deploy
oc apply -f deployment/k8s/configmap.yaml
oc apply -f deployment/k8s/secret.yaml
oc apply -f deployment/k8s/deployment.yaml

# Create route for external access
oc expose service mcp-image-server --hostname=mcp-image-server.apps.cluster.com

# Check deployment
oc get pods
oc get route
```

#### OpenShift with GPU Support

```yaml
# Add to deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        resources:
          limits:
            nvidia.com/gpu: 1  # Request GPU
          requests:
            nvidia.com/gpu: 1
      nodeSelector:
        node.openshift.io/os_id: rhcos
        feature.node.kubernetes.io/pci-10de.present: "true"  # NVIDIA GPU
```

### 5. Cloud Provider Specific Deployments

#### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster --name mcp-image-server --region us-east-1

# Deploy with ALB ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json

# Use S3 storage with IAM roles
kubectl annotate serviceaccount mcp-image-server \
  eks.amazonaws.com/role-arn=arn:aws:iam::123456789012:role/mcp-image-server-s3-role
```

#### Azure AKS

```bash
# Create AKS cluster
az aks create --resource-group myResourceGroup --name mcp-image-server

# Use Azure Blob Storage
kubectl create secret generic mcp-image-server-secrets \
  --from-literal=azure_storage_account="mystorageaccount" \
  --from-literal=azure_storage_key="storage-key"
```

#### Google GKE

```bash
# Create GKE cluster
gcloud container clusters create mcp-image-server --zone us-central1-a

# Use Google Cloud Storage
kubectl create secret generic mcp-image-server-secrets \
  --from-file=service-account-key=/path/to/service-account.json
```

## Configuration Management

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SERVICE_NAME` | Service identifier | `mcp-image-server` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `HOST` | Bind host | `0.0.0.0` | No |
| `PORT` | Bind port | `8000` | No |
| `WORKERS` | Number of workers | `4` | No |
| `STORAGE_BACKEND` | Storage type | `file` | No |
| `STORAGE_PATH` | File storage path | `/tmp/mcp-images` | No |
| `S3_BUCKET` | S3 bucket name | - | For S3 |
| `S3_PREFIX` | S3 key prefix | `mcp-images/` | No |
| `KSERVE_ENDPOINT` | KServe endpoint URL | - | Yes |
| `KSERVE_MODEL_NAME` | Model name | `stable-diffusion` | No |
| `IMAGE_TTL` | Image lifetime (seconds) | `3600` | No |

### ConfigMap Management

```bash
# View current config
kubectl get configmap mcp-image-server-config -o yaml

# Update configuration
kubectl patch configmap mcp-image-server-config \
  --patch '{"data":{"log_level":"DEBUG"}}'

# Restart deployment to pick up changes
kubectl rollout restart deployment/mcp-image-server
```

### Secret Management

**Create secrets manually**:
```bash
# S3 credentials
kubectl create secret generic mcp-image-server-secrets \
  --from-literal=aws_access_key_id="AKIAIOSFODNN7EXAMPLE" \
  --from-literal=aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# TLS certificate
kubectl create secret tls mcp-image-server-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

**Using external secret management**:
```yaml
# External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mcp-image-server-external
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: mcp-image-server-secrets
  data:
  - secretKey: aws_access_key_id
    remoteRef:
      key: mcp-image-server/s3
      property: access_key_id
```

## Monitoring and Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health information
curl http://localhost:8000/health | jq .
```

### Logging

```bash
# View application logs
kubectl logs -f deployment/mcp-image-server

# View logs from all pods
kubectl logs -f -l app=mcp-image-server

# View logs with structured output
kubectl logs deployment/mcp-image-server | jq .
```

### Metrics (Optional)

If metrics are enabled:
```bash
# View metrics
curl http://localhost:8000/metrics

# Prometheus configuration
- job_name: 'mcp-image-server'
  static_configs:
  - targets: ['mcp-image-server:8000']
  metrics_path: /metrics
```

## Scaling and Performance Tuning

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-image-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-image-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Resource Optimization

**Memory-optimized**:
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "50m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**CPU-optimized**:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "2000m"
```

### Performance Tuning

```bash
# Increase worker processes
export WORKERS=8

# Adjust timeouts
export KSERVE_TIMEOUT=120.0

# Optimize cleanup
export IMAGE_CLEANUP_INTERVAL=1800
export IMAGE_TTL=7200
```

## Security Best Practices

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  fsGroup: 1001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-image-server-netpol
spec:
  podSelector:
    matchLabels:
      app: mcp-image-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 8080  # KServe
```

### Secret Management

- Use Kubernetes secrets for sensitive data
- Consider external secret management (Vault, AWS Secrets Manager)
- Rotate credentials regularly
- Use service accounts with minimal permissions

## Backup and Disaster Recovery

### File Storage Backup

```bash
# Backup PVC data
kubectl exec -it pod-name -- tar czf - /app/storage | \
  kubectl cp pod-name:/tmp/storage-backup.tar.gz ./storage-backup.tar.gz

# Restore PVC data
kubectl cp ./storage-backup.tar.gz pod-name:/tmp/
kubectl exec -it pod-name -- tar xzf /tmp/storage-backup.tar.gz -C /
```

### S3 Storage Backup

```bash
# S3 backup is handled by AWS
# Enable versioning and cross-region replication
aws s3api put-bucket-versioning \
  --bucket my-image-bucket \
  --versioning-configuration Status=Enabled
```

### Configuration Backup

```bash
# Backup all configurations
kubectl get configmaps,secrets -o yaml > mcp-image-server-config-backup.yaml

# Restore configurations
kubectl apply -f mcp-image-server-config-backup.yaml
```

## Migration Guide

### Upgrading the Application

```bash
# Rolling update
kubectl set image deployment/mcp-image-server \
  mcp-server=mcp-image-server:v2.0.0

# Check rollout status
kubectl rollout status deployment/mcp-image-server

# Rollback if needed
kubectl rollout undo deployment/mcp-image-server
```

### Migrating Storage Backends

**File to S3**:
```bash
# 1. Scale down to prevent new writes
kubectl scale deployment mcp-image-server --replicas=0

# 2. Copy data to S3
aws s3 sync /app/storage s3://my-bucket/mcp-images/

# 3. Update configuration to use S3
kubectl patch configmap mcp-image-server-config \
  --patch '{"data":{"storage_backend":"s3"}}'

# 4. Scale back up
kubectl scale deployment mcp-image-server --replicas=3
```

## Troubleshooting

For detailed troubleshooting information, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

Common issues:
- Check health endpoint: `curl http://localhost:8000/health`
- Verify environment variables are set correctly
- Ensure KServe endpoint is accessible
- Check storage permissions and connectivity
- Review application logs for error messages

## Next Steps

1. **Customize Configuration**: Update ConfigMaps for your environment
2. **Set up Monitoring**: Deploy Prometheus and Grafana for observability
3. **Configure CI/CD**: Set up automated deployment pipelines
4. **Security Hardening**: Implement additional security measures
5. **Performance Testing**: Load test your deployment
6. **Backup Strategy**: Implement regular backup procedures
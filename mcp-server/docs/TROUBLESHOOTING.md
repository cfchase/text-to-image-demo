# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the MCP Image Generation Server.

## Quick Diagnostics

### Health Check

First, check if the service is running and healthy:

```bash
# Basic health check
curl -f http://localhost:8000/health

# Detailed health information
curl http://localhost:8000/health | jq .
```

Expected healthy response:
```json
{
  "service": "healthy",
  "kserve": "healthy",
  "storage": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "version": "0.1.0"
}
```

### Service Logs

Check application logs for error messages:

```bash
# Docker
docker logs mcp-image-server

# Kubernetes
kubectl logs -f deployment/mcp-image-server

# Local development
python -m mcp_server.main dev
```

## Common Issues and Solutions

### 1. Service Won't Start

#### Symptoms
- Container exits immediately
- Pod restarts continuously
- Health check fails on startup

#### Troubleshooting Steps

**Check Configuration**:
```bash
# Verify environment variables
env | grep -E "(KSERVE|STORAGE|AWS)"

# Check configuration in Kubernetes
kubectl describe configmap mcp-image-server-config
kubectl describe secret mcp-image-server-secrets
```

**Check Dependencies**:
```bash
# Test KServe endpoint
curl -X POST http://your-kserve-endpoint/v1/models/stable-diffusion:predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [{"prompt": "test"}]}'

# Test S3 connectivity (if using S3)
aws s3 ls s3://your-bucket/ --region us-east-1
```

**Common Fixes**:
- Ensure `KSERVE_ENDPOINT` is accessible from the container
- Verify S3 credentials and bucket permissions
- Check file storage directory permissions
- Validate environment variable formats

#### Error: "Failed to connect to KServe endpoint"

```bash
# Check if KServe service is running
kubectl get pods -l app=diffusers-runtime

# Test connectivity from within the cluster
kubectl run debug --rm -it --image=curlimages/curl -- /bin/sh
curl http://diffusers-runtime.default.svc.cluster.local:8080/health
```

**Solutions**:
- Update `KSERVE_ENDPOINT` to use cluster DNS name
- Check network policies blocking connections
- Verify KServe service is deployed and healthy

#### Error: "Permission denied accessing storage path"

```bash
# Check file permissions
ls -la /app/storage/

# Check PVC mount
kubectl describe pvc mcp-image-server-storage
```

**Solutions**:
- Ensure storage directory is writable by user ID 1001
- Fix PVC permissions: `chown -R 1001:1001 /app/storage`
- Check storage class supports ReadWriteMany access

### 2. Image Generation Failures

#### Symptoms
- Generation requests timeout
- KServe returns errors
- Images are corrupted or empty

#### Troubleshooting Steps

**Check KServe Health**:
```bash
# Test KServe directly
curl -X POST $KSERVE_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "a beautiful sunset",
      "width": 512,
      "height": 512,
      "num_inference_steps": 20
    }]
  }'
```

**Monitor Resource Usage**:
```bash
# Check pod resources
kubectl top pods -l app=mcp-image-server

# Check node resources
kubectl top nodes

# Check for OOM kills
kubectl describe pod <pod-name> | grep -i "killed\|oom"
```

#### Error: "Request timeout"

**Symptoms**: Requests timeout after 60 seconds

**Solutions**:
```bash
# Increase timeout in configuration
export KSERVE_TIMEOUT=300.0

# Or update ConfigMap
kubectl patch configmap mcp-image-server-config \
  --patch '{"data":{"kserve_timeout":"300.0"}}'

# Restart deployment
kubectl rollout restart deployment/mcp-image-server
```

#### Error: "CUDA out of memory"

**Symptoms**: KServe returns GPU memory errors

**Solutions**:
- Reduce image dimensions in requests
- Lower batch size in KServe runtime
- Add more GPU nodes or use larger GPU instances
- Implement request queuing

#### Error: "Model not found"

**Symptoms**: KServe returns model not found errors

**Solutions**:
```bash
# Check model name configuration
echo $KSERVE_MODEL_NAME

# List available models in KServe
curl $KSERVE_ENDPOINT | jq .

# Update model name if needed
kubectl patch configmap mcp-image-server-config \
  --patch '{"data":{"kserve_model_name":"your-model-name"}}'
```

### 3. Storage Issues

#### File Storage Problems

**Error: "No space left on device"**
```bash
# Check disk usage
df -h /app/storage

# Check PVC size
kubectl describe pvc mcp-image-server-storage

# Clean up old images manually
find /app/storage -name "*.png" -mtime +1 -delete
```

**Solutions**:
- Increase PVC size
- Reduce image TTL
- Implement more aggressive cleanup
- Monitor storage usage

**Error: "Permission denied"**
```bash
# Check ownership and permissions
ls -la /app/storage/
kubectl exec -it <pod-name> -- ls -la /app/storage/

# Fix permissions
kubectl exec -it <pod-name> -- chown -R 1001:1001 /app/storage
kubectl exec -it <pod-name> -- chmod 755 /app/storage
```

#### S3 Storage Problems

**Error: "Access denied"**
```bash
# Test S3 credentials
aws s3 ls s3://$S3_BUCKET --region $AWS_REGION

# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:user/username \
  --action-names s3:GetObject,s3:PutObject,s3:DeleteObject \
  --resource-arns arn:aws:s3:::bucket-name/*
```

**Solutions**:
- Verify AWS credentials are correct
- Check S3 bucket policy
- Ensure IAM user has required permissions
- Test with different endpoint URL for MinIO/other S3-compatible storage

**Error: "Bucket does not exist"**
```bash
# Check if bucket exists
aws s3 ls s3://$S3_BUCKET

# Create bucket if needed
aws s3 mb s3://$S3_BUCKET --region $AWS_REGION
```

### 4. Network and Connectivity

#### Cannot Access Service

**Symptoms**: HTTP requests to service fail

**Troubleshooting**:
```bash
# Check service status
kubectl get svc mcp-image-server

# Test service from within cluster
kubectl run debug --rm -it --image=curlimages/curl -- /bin/sh
curl http://mcp-image-server:8000/health

# Check ingress/route
kubectl get ingress mcp-image-server-ingress
kubectl describe ingress mcp-image-server-ingress
```

**Solutions**:
- Verify service selector matches pod labels
- Check ingress controller is running
- Verify DNS resolution
- Check firewall rules

#### Network Policy Issues

**Symptoms**: Services can't communicate

**Troubleshooting**:
```bash
# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy mcp-image-server-netpol

# Test connectivity
kubectl exec -it <pod-name> -- nc -zv diffusers-runtime 8080
```

**Solutions**:
- Update network policy to allow required traffic
- Check namespace labels match policy selectors
- Temporarily disable network policies for testing

### 5. Performance Issues

#### Slow Response Times

**Symptoms**: Requests take longer than expected

**Diagnosis**:
```bash
# Check application metrics
curl http://localhost:8000/metrics | grep -E "(request_duration|generation_time)"

# Monitor resource usage
kubectl top pods
kubectl top nodes

# Check storage performance
kubectl exec -it <pod-name> -- dd if=/dev/zero of=/app/storage/test bs=1M count=100
```

**Solutions**:
- Increase resource limits
- Use faster storage class
- Scale up replicas
- Optimize KServe model serving

#### High Memory Usage

**Symptoms**: Pods getting OOMKilled

**Diagnosis**:
```bash
# Check memory usage
kubectl top pods
kubectl describe pod <pod-name> | grep -A5 -B5 "OOMKilled"

# Check memory limits
kubectl describe deployment mcp-image-server | grep -A5 -B5 "limits"
```

**Solutions**:
```yaml
# Increase memory limits
resources:
  limits:
    memory: "2Gi"
  requests:
    memory: "1Gi"
```

### 6. Image Cleanup Issues

#### Images Not Being Cleaned Up

**Symptoms**: Storage fills up with old images

**Diagnosis**:
```bash
# Check cleanup configuration
echo $IMAGE_CLEANUP_INTERVAL
echo $IMAGE_TTL

# Check cleanup logs
kubectl logs deployment/mcp-image-server | grep cleanup

# Manual cleanup trigger
curl -X POST http://localhost:8000/images/cleanup
```

**Solutions**:
- Reduce cleanup interval
- Reduce image TTL
- Increase storage capacity
- Check cleanup task is running

### 7. Authentication and Authorization

#### MCP Client Cannot Connect

**Symptoms**: MCP protocol authentication fails

**Troubleshooting**:
```bash
# Check MCP server logs
kubectl logs deployment/mcp-image-server | grep -i mcp

# Test MCP endpoint directly
curl -X POST http://localhost:8000/mcp/v1/tools/generate_image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test image"}'
```

#### S3 Access Denied

**Symptoms**: Cannot write to or read from S3

**Diagnosis**:
```bash
# Test AWS CLI access
aws s3 cp test.txt s3://$S3_BUCKET/test.txt
aws s3 rm s3://$S3_BUCKET/test.txt

# Check credentials in secret
kubectl get secret mcp-image-server-secrets -o yaml | \
  grep -E "(aws_access_key_id|aws_secret_access_key)" | \
  head -1 | cut -d: -f2 | tr -d ' ' | base64 -d
```

## Debugging Tools and Commands

### Kubernetes Debugging

```bash
# Get detailed pod information
kubectl describe pod <pod-name>

# Get pod logs with previous container
kubectl logs <pod-name> --previous

# Execute commands in pod
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for local testing
kubectl port-forward deployment/mcp-image-server 8000:8000

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Debug network connectivity
kubectl run debug --rm -it --image=nicolaka/netshoot -- /bin/bash
```

### Application Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test individual components
python -c "
from mcp_server.storage import create_storage
from mcp_server.config.settings import Settings
settings = Settings()
storage = create_storage(settings)
print('Storage created successfully')
"

# Test KServe connectivity
python -c "
import asyncio
from mcp_server.kserve.client import KServeClient
async def test():
    client = KServeClient('http://localhost:8080', 'stable-diffusion')
    health = await client.health_check()
    print(f'KServe health: {health}')
asyncio.run(test())
"
```

### Performance Debugging

```bash
# Profile application
py-spy top --pid $(pgrep -f "mcp_server.main")

# Monitor file descriptor usage
lsof -p $(pgrep -f "mcp_server.main")

# Check network connections
netstat -tulpn | grep :8000

# Monitor disk I/O
iotop -p $(pgrep -f "mcp_server.main")
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Service Health**: `/health` endpoint status
2. **Request Rate**: Number of image generation requests per minute
3. **Success Rate**: Percentage of successful generations
4. **Response Time**: Average generation time
5. **Storage Usage**: Disk/S3 storage utilization
6. **Memory Usage**: Container memory consumption
7. **KServe Health**: Upstream service availability

### Sample Alerts

```yaml
# Prometheus alert rules
groups:
- name: mcp-image-server
  rules:
  - alert: MCPImageServerDown
    expr: up{job="mcp-image-server"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "MCP Image Server is down"
      
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  - alert: StorageSpaceLow
    expr: (storage_free_bytes / storage_total_bytes) < 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Storage space is running low"
```

## Getting Help

### Log Collection

When reporting issues, collect relevant information:

```bash
# Create debug bundle
mkdir debug-bundle
cd debug-bundle

# Application logs
kubectl logs deployment/mcp-image-server > app-logs.txt

# Configuration
kubectl get configmap mcp-image-server-config -o yaml > configmap.yaml
kubectl get secret mcp-image-server-secrets -o yaml > secrets.yaml

# Pod status
kubectl describe pod -l app=mcp-image-server > pod-status.txt

# Events
kubectl get events --sort-by=.metadata.creationTimestamp > events.txt

# Resource usage
kubectl top pods > resource-usage.txt

# Create archive
tar czf debug-bundle.tar.gz .
```

### Support Channels

1. **GitHub Issues**: Report bugs and feature requests
2. **Documentation**: Check latest documentation
3. **Community Forums**: Ask questions and share solutions
4. **Slack/Discord**: Real-time help from community

### Before Reporting Issues

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Verify you're using the latest version
4. Test with minimal configuration
5. Collect debug information

## Preventive Measures

### Health Monitoring

```bash
# Set up continuous health monitoring
while true; do
  if ! curl -f http://localhost:8000/health; then
    echo "Health check failed at $(date)"
    # Add notification logic here
  fi
  sleep 30
done
```

### Resource Monitoring

```bash
# Monitor resource usage
kubectl top pods -l app=mcp-image-server
kubectl describe hpa mcp-image-server-hpa
```

### Regular Maintenance

1. **Update Dependencies**: Keep base images and dependencies current
2. **Monitor Storage**: Set up alerts for storage usage
3. **Review Logs**: Regularly check for warnings and errors
4. **Test Backups**: Verify backup and restore procedures
5. **Performance Testing**: Regular load testing to catch issues early

This troubleshooting guide should help you quickly identify and resolve most common issues with the MCP Image Generation Server. For complex issues, consider enabling debug logging and collecting comprehensive diagnostic information before seeking support.
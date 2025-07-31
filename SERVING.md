# Model Serving Guide

This guide explains how to deploy and serve your fine-tuned Stable Diffusion models using KServe in OpenShift AI.

## Overview

Model serving in OpenShift AI provides:
- **REST/gRPC APIs** for model inference
- **Auto-scaling** based on demand
- **GPU acceleration** for fast inference
- **Multiple model versions** with traffic splitting
- **Custom runtimes** for any framework

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Client     │────▶│  Route/Ingress  │────▶│ InferenceService │
│ Application  │     │   (External)    │     │    (KServe)      │
└──────────────┘     └─────────────────┘     └────────┬─────────┘
                                                       │
                           ┌───────────────────────────┴────────────┐
                           │                                        │
                     ┌─────▼──────┐                          ┌─────▼──────┐
                     │ Predictor  │                          │Transformer │
                     │   (GPU)    │                          │ (Optional) │
                     └─────┬──────┘                          └────────────┘
                           │
                     ┌─────▼──────┐
                     │   Model    │
                     │    (S3)    │
                     └────────────┘
```

## Prerequisites

1. **Trained Model**: Saved in S3-compatible storage
2. **Custom Runtime**: Deployed (diffusers-runtime)
3. **GPU Resources**: Available in cluster
4. **Data Connection**: Configured for model access

## Step 1: Deploy the Custom Runtime

### Build the Runtime Container

```bash
cd diffusers-runtime

# Build the container
make build

# Or manually:
podman build -t quay.io/your-org/diffusers-runtime:latest -f docker/Dockerfile .
```

### Push to Registry

```bash
# Push to registry
make push

# Or manually:
podman push quay.io/your-org/diffusers-runtime:latest
```

### Deploy ServingRuntime

```bash
# Apply the serving runtime
oc apply -f templates/serving-runtime.yaml
```

Example ServingRuntime:
```yaml
apiVersion: serving.kserve.io/v1alpha1
kind: ServingRuntime
metadata:
  name: diffusers-runtime
spec:
  supportedModelFormats:
    - name: pytorch
      version: "1"
      autoSelect: true
  protocolVersions:
    - v1
    - v2
  containers:
    - name: kserve-container
      image: quay.io/your-org/diffusers-runtime:latest
      env:
        - name: STORAGE_URI
          value: "pvc://model-cache/"
      resources:
        requests:
          cpu: "2"
          memory: "8Gi"
          nvidia.com/gpu: "1"
        limits:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: "1"
```

## Step 2: Create InferenceService

### Via Dashboard

1. Navigate to your Data Science Project
2. Click "Models" → "Deploy model"
3. Configure:
   - **Model name**: `stable-diffusion-teddy`
   - **Serving runtime**: `diffusers-runtime`
   - **Model framework**: `pytorch`
   - **Model location**: `s3://models/notebook-output/redhat-dog/`
   - **Compute resources**: Select GPU

### Via YAML

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: stable-diffusion-teddy
  annotations:
    serving.kserve.io/deploymentMode: "Serverless"
spec:
  predictor:
    serviceAccountName: sa-with-s3-access
    model:
      modelFormat:
        name: pytorch
      runtime: diffusers-runtime
      storageUri: s3://models/notebook-output/redhat-dog/
      resources:
        requests:
          cpu: "2"
          memory: "8Gi"
          nvidia.com/gpu: "1"
        limits:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: "1"
    minReplicas: 0
    maxReplicas: 3
    scaleTarget: 5
    scaleMetric: concurrency
```

Apply the configuration:
```bash
oc apply -f inference-service.yaml
```

## Step 3: Configure Route (Optional)

For external access, create a route:

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: stable-diffusion-teddy
spec:
  to:
    kind: Service
    name: stable-diffusion-teddy-predictor
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

## Step 4: Test the Deployment

### Check Status

```bash
# Check InferenceService status
oc get inferenceservice stable-diffusion-teddy

# Expected output:
NAME                     URL                                               READY   
stable-diffusion-teddy   http://stable-diffusion-teddy-predictor:8080    True

# Check pods
oc get pods -l serving.kserve.io/inferenceservice=stable-diffusion-teddy
```

### Test Inference

Internal test:
```bash
# Port-forward for testing
oc port-forward service/stable-diffusion-teddy-predictor 8080:80

# Test request
curl -X POST http://localhost:8080/v1/models/model:predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "a photo of rhteddy dog",
      "num_inference_steps": 50
    }]
  }'
```

External test:
```bash
# Get route URL
ROUTE_URL=$(oc get route stable-diffusion-teddy -o jsonpath='{.spec.host}')

# Test request
curl -X POST https://${ROUTE_URL}/v1/models/model:predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "a photo of rhteddy dog wearing sunglasses"
    }]
  }'
```

## Advanced Configuration

### Auto-scaling

Configure Knative auto-scaling:

```yaml
metadata:
  annotations:
    autoscaling.knative.dev/target: "10"
    autoscaling.knative.dev/targetBurstCapacity: "20"
    autoscaling.knative.dev/minScale: "1"
    autoscaling.knative.dev/maxScale: "5"
    autoscaling.knative.dev/scaleToZeroPodRetentionPeriod: "5m"
```

### GPU Selection

Specify GPU type:

```yaml
spec:
  predictor:
    nodeSelector:
      nvidia.com/gpu.product: NVIDIA-L40S
    tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
```

### Model Caching

Enable local model caching:

```yaml
spec:
  predictor:
    model:
      storageUri: s3://models/stable-diffusion/
      storage:
        key: localModelCache
        parameters:
          cacheSize: "20Gi"
```

### Multi-Model Serving

Serve multiple models from one runtime:

```yaml
apiVersion: serving.kserve.io/v1alpha1
kind: InferenceGraph
metadata:
  name: stable-diffusion-graph
spec:
  nodes:
    teddy:
      routerType: Sequence
      routes:
        - serviceName: stable-diffusion-teddy
          weight: 100
    general:
      routerType: Sequence  
      routes:
        - serviceName: stable-diffusion-general
          weight: 100
```

## Monitoring

### Metrics

KServe exposes Prometheus metrics:

```bash
# Key metrics to monitor
kserve_inference_request_count
kserve_inference_request_duration_seconds
kserve_model_loading_time_seconds
kserve_gpu_memory_usage_bytes
kserve_gpu_utilization_percentage
```

### Logging

View predictor logs:

```bash
# Get logs
oc logs -l serving.kserve.io/inferenceservice=stable-diffusion-teddy -c kserve-container

# Follow logs
oc logs -f deployment/stable-diffusion-teddy-predictor-00001-deployment
```

### Dashboards

Create Grafana dashboards for:
- Request rate and latency
- GPU utilization
- Memory usage
- Error rates
- Model loading times

## Troubleshooting

### Model Won't Load

1. **Check S3 Access**
   ```bash
   # Verify service account has S3 secret
   oc describe sa sa-with-s3-access
   
   # Check secret is mounted
   oc describe pod <predictor-pod>
   ```

2. **Verify Model Path**
   ```bash
   # List S3 contents
   aws s3 ls s3://models/notebook-output/redhat-dog/ --endpoint-url=$AWS_S3_ENDPOINT
   ```

3. **Check Container Logs**
   ```bash
   oc logs <predictor-pod> -c storage-initializer
   ```

### Out of Memory

1. **Increase Memory Limits**
   ```yaml
   resources:
     limits:
       memory: "24Gi"
   ```

2. **Reduce Batch Size**
   ```python
   # In model.py
   self.pipe.enable_attention_slicing()
   self.pipe.enable_vae_slicing()
   ```

### Slow Inference

1. **Check GPU Usage**
   ```bash
   oc exec <predictor-pod> -- nvidia-smi
   ```

2. **Enable Optimizations**
   - TensorRT conversion
   - Model quantization
   - Batch processing

3. **Scale Horizontally**
   ```bash
   oc scale inferenceservice stable-diffusion-teddy --replicas=3
   ```

## Best Practices

### 1. Resource Management
- Start with conservative limits
- Monitor actual usage
- Scale based on metrics

### 2. Model Versioning
```bash
# Version in S3 path
s3://models/stable-diffusion/v1/
s3://models/stable-diffusion/v2/

# Update InferenceService
oc patch inferenceservice stable-diffusion-teddy \
  --type merge \
  -p '{"spec":{"predictor":{"model":{"storageUri":"s3://models/stable-diffusion/v2/"}}}}'
```

### 3. Canary Deployments
```yaml
spec:
  predictor:
    canaryTrafficPercent: 20
    canary:
      model:
        storageUri: s3://models/stable-diffusion/v2/
```

### 4. Security
- Use network policies
- Enable authentication
- Implement rate limiting
- Validate inputs

## Integration Examples

### Python Client
```python
import requests
import base64
from PIL import Image
import io

class StableDiffusionClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        
    def generate(self, prompt, steps=50):
        url = f"{self.endpoint}/v1/models/model:predict"
        payload = {
            "instances": [{
                "prompt": prompt,
                "num_inference_steps": steps
            }]
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        img_b64 = response.json()['predictions'][0]['image']['b64']
        img_bytes = base64.b64decode(img_b64)
        return Image.open(io.BytesIO(img_bytes))

# Usage
client = StableDiffusionClient("https://model.apps.cluster.com")
image = client.generate("a photo of rhteddy dog in space")
image.save("teddy_space.png")
```

### Node.js Client
```javascript
const axios = require('axios');
const fs = require('fs');

class StableDiffusionClient {
  constructor(endpoint) {
    this.endpoint = endpoint;
  }
  
  async generate(prompt, steps = 50) {
    const url = `${this.endpoint}/v1/models/model:predict`;
    const payload = {
      instances: [{
        prompt: prompt,
        num_inference_steps: steps
      }]
    };
    
    const response = await axios.post(url, payload);
    const imgB64 = response.data.predictions[0].image.b64;
    const imgBuffer = Buffer.from(imgB64, 'base64');
    
    return imgBuffer;
  }
}

// Usage
const client = new StableDiffusionClient('https://model.apps.cluster.com');
const image = await client.generate('a photo of rhteddy dog');
fs.writeFileSync('teddy.png', image);
```

## Next Steps

1. **Production Hardening**
   - Add authentication
   - Implement caching
   - Set up monitoring

2. **Performance Optimization**
   - Try TensorRT conversion
   - Implement batching
   - Optimize model loading

3. **Advanced Features**
   - A/B testing
   - Multi-model serving
   - Custom transformers

4. **Integration**
   - Build UI applications
   - Create API gateways
   - Implement webhooks
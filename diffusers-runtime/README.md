# Diffusers Custom Runtime for KServe

This custom runtime enables serving Hugging Face Diffusers models (like Stable Diffusion) on KServe in OpenShift AI.

## Overview

The runtime implements:
- KServe V1 prediction protocol
- Stable Diffusion model loading from S3
- GPU-accelerated inference
- Base64 image encoding for REST transport
- Automatic model caching

## Architecture

```
┌─────────────────────────────────────────┐
│          KServe Runtime Container        │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │         FastAPI Server             │ │
│  │  ┌──────────────────────────────┐  │ │
│  │  │   /v1/models/model:predict   │  │ │
│  │  └──────────────┬───────────────┘  │ │
│  │                 ▼                   │ │
│  │  ┌──────────────────────────────┐  │ │
│  │  │    DiffusersModel Class      │  │ │
│  │  │  - load_model()              │  │ │
│  │  │  - predict()                 │  │ │
│  │  └──────────────┬───────────────┘  │ │
│  │                 ▼                   │ │
│  │  ┌──────────────────────────────┐  │ │
│  │  │   DiffusionPipeline (HF)     │  │ │
│  │  │  - StableDiffusion           │  │ │
│  │  │  - GPU Acceleration          │  │ │
│  │  └──────────────────────────────┘  │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Environment Variables:                  │
│  - STORAGE_URI: S3 model path           │
│  - MODEL_NAME: Model identifier         │
│  └──────────────────────────────────────┘
```

## Quick Start

### Build and Push

```bash
# Build the container
make build

# Push to your registry
make push
```

### Deploy Runtime

```bash
# Deploy the ServingRuntime to OpenShift
oc apply -f templates/serving-runtime.yaml
```

### Deploy Model

```bash
# Update the S3 path in inference-service.yaml
vi templates/inference-service.yaml

# Deploy the InferenceService
make deploy
```

### Test

```bash
# Test the deployed model
make test-v1

# Or manually:
curl -X POST http://your-model-endpoint/v1/models/model:predict \
  -H "Content-Type: application/json" \
  -d @scripts/v1_input.json
```

## Development

### Project Structure

```
diffusers-runtime/
├── docker/
│   └── Dockerfile          # Container definition
├── src/
│   └── model.py           # KServe predictor implementation
├── templates/
│   ├── serving-runtime.yaml    # ServingRuntime CR
│   ├── inference-service.yaml  # InferenceService CR
│   └── route.yaml             # OpenShift Route
├── scripts/
│   └── v1_input.json      # Test input
├── requirements.txt       # Python dependencies
├── Makefile              # Build automation
└── README.md             # This file
```

### Key Files

#### model.py
The main predictor implementation:

```python
class DiffusersModel(Model):
    def __init__(self, name: str):
        super().__init__(name)
        self.pipeline = None
        self.ready = False
        
    def load(self):
        # Load model from STORAGE_URI
        model_path = os.environ.get('STORAGE_URI', '/mnt/models')
        self.pipeline = DiffusionPipeline.from_pretrained(model_path)
        self.pipeline.to("cuda")
        self.ready = True
        
    def predict(self, request: Dict) -> Dict:
        instances = request.get("instances", [])
        predictions = []
        
        for instance in instances:
            prompt = instance.get("prompt")
            negative_prompt = instance.get("negative_prompt", "")
            num_steps = instance.get("num_inference_steps", 50)
            
            # Generate image
            image = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_steps
            ).images[0]
            
            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            predictions.append({"image": {"b64": img_b64}})
            
        return {"predictions": predictions}
```

#### Dockerfile
Multi-stage build for efficiency:

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 as base

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy model code
COPY src/model.py /app/model.py
WORKDIR /app

# Set entrypoint
ENTRYPOINT ["python3", "-m", "model"]
```

### Configuration

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_URI` | S3 path to model | `/mnt/models` |
| `MODEL_NAME` | Model identifier | `model` |
| `PORT` | Server port | `8080` |
| `WORKERS` | Number of workers | `1` |
| `MAX_BATCH_SIZE` | Max batch size | `1` |

#### GPU Requirements

- CUDA 11.8+ compatible GPU
- Minimum 16GB VRAM for SD 2.1
- Recommended: NVIDIA A10G or better

### API Specification

#### Request Format

```json
{
  "instances": [
    {
      "prompt": "a photo of a dog",
      "negative_prompt": "blurry, low quality",
      "num_inference_steps": 50,
      "guidance_scale": 7.5,
      "height": 512,
      "width": 512
    }
  ]
}
```

#### Response Format

```json
{
  "predictions": [
    {
      "image": {
        "b64": "<base64-encoded-png>"
      }
    }
  ]
}
```

#### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `prompt` | string | Text description | Required |
| `negative_prompt` | string | What to avoid | `""` |
| `num_inference_steps` | int | Denoising steps | `50` |
| `guidance_scale` | float | Prompt adherence | `7.5` |
| `height` | int | Image height | `512` |
| `width` | int | Image width | `512` |

## Deployment Options

### Option 1: Serverless (Scale to Zero)

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  annotations:
    serving.kserve.io/deploymentMode: "Serverless"
spec:
  predictor:
    minReplicas: 0
    maxReplicas: 5
```

### Option 2: Always On

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  annotations:
    serving.kserve.io/deploymentMode: "RawDeployment"
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 10
```

### Option 3: Multi-Model Serving

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
spec:
  predictor:
    model:
      modelFormat:
        name: pytorch
      runtime: diffusers-runtime
      storageUri: s3://models/
      storage:
        key: multi-model
        parameters:
          modelDir: "models/"
```

## Performance Optimization

### 1. Model Loading
- Models are cached after first load
- Use PVC for faster subsequent loads
- Consider model sharding for large models

### 2. Inference Optimization
```python
# Enable memory efficient attention
pipeline.enable_xformers_memory_efficient_attention()

# Enable CPU offload for low VRAM
pipeline.enable_model_cpu_offload()

# Use half precision
pipeline = pipeline.to(torch.float16)
```

### 3. Batching
```python
# Process multiple prompts
images = pipeline(
    prompt=[prompt1, prompt2, prompt3],
    num_images_per_prompt=1
).images
```

### 4. Caching
Implement result caching for repeated prompts:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def generate_cached(prompt, negative_prompt, steps):
    return pipeline(prompt, negative_prompt, steps).images[0]
```

## Monitoring

### Metrics Exposed

- `inference_request_count`: Total requests
- `inference_request_duration_seconds`: Request latency
- `model_load_time_seconds`: Model loading time
- `gpu_memory_usage_bytes`: GPU memory usage
- `gpu_utilization_percent`: GPU utilization

### Health Checks

```bash
# Liveness probe
curl http://model:8080/v1/models/model

# Readiness probe  
curl http://model:8080/v1/models/model/ready
```

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   ```python
   # Reduce memory usage
   pipeline.enable_attention_slicing()
   pipeline.enable_vae_slicing()
   ```

2. **Model Not Found**
   ```bash
   # Check S3 access
   aws s3 ls $STORAGE_URI --endpoint-url $AWS_S3_ENDPOINT
   ```

3. **Slow Inference**
   ```python
   # Reduce steps for faster generation
   num_inference_steps = 30  # Instead of 50
   ```

4. **Import Errors**
   ```bash
   # Verify all dependencies
   pip freeze | grep -E "diffusers|transformers|torch"
   ```

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd diffusers-runtime

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run locally
python src/model.py
```

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests
./scripts/test_integration.sh

# Load testing
locust -f tests/load_test.py
```

### Code Style

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

## License

This project is licensed under the Apache License 2.0. See LICENSE for details.

## Support

For issues and questions:
1. Check the troubleshooting guide
2. Review OpenShift AI documentation
3. Open an issue in this repository
4. Contact Red Hat support (for customers)

## Roadmap

- [ ] TensorRT optimization
- [ ] Multi-GPU support
- [ ] LoRA adapter loading
- [ ] ONNX export support
- [ ] Prometheus metrics enhancement
- [ ] Request batching optimization
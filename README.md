# OpenShift AI Demo: Text-to-Image Generation

This demonstration showcases the complete machine learning workflow in Red Hat OpenShift AI, taking you from initial experimentation to production deployment. Using Stable Diffusion for text-to-image generation, you'll learn how to experiment with models, fine-tune them with custom data, create automated pipelines, and deploy models as scalable services.

## What You'll Learn

- **Data Science Projects**: Creating and managing ML workspaces in OpenShift AI
- **GPU-Accelerated Workbenches**: Leveraging NVIDIA GPUs for model training and inference
- **Model Experimentation**: Working with pre-trained models from Hugging Face
- **Fine-Tuning**: Customizing models with your own data using Dreambooth
- **Pipeline Automation**: Building repeatable ML workflows with Data Science Pipelines
- **Model Serving**: Deploying models as REST APIs using KServe
- **Production Integration**: Connecting served models to applications

## Prerequisites

### Platform Requirements
- Red Hat OpenShift cluster (4.12+)
- Red Hat OpenShift AI installed (2.9+)
  - For managed service: Available as add-on for OpenShift Dedicated or ROSA
  - For self-managed: Install from OperatorHub
- GPU node with at least 45GB memory (NVIDIA L40S recommended, A10G minimum for smaller models)

### Storage Requirements
- S3-compatible object storage (MinIO, AWS S3, or Ceph)
- Two buckets configured:
  - `pipeline-artifacts`: For pipeline execution artifacts
  - `models`: For storing trained models

### Access Requirements
- OpenShift AI Dashboard access
- Ability to create Data Science Projects
- (Optional) Hugging Face account with API token for model downloads

## Quick Start

1. **Access OpenShift AI Dashboard**
   - Navigate to your OpenShift console
   - Click the application launcher (9-dot grid)
   - Select "Red Hat OpenShift AI"

2. **Create a Data Science Project**
   - Click "Data Science Projects"
   - Create a new project named `image-generation`

3. **Set Up Storage**
   - Import `setup/setup-s3.yaml` to create local S3 storage (for demos)
   - Or configure your own S3-compatible storage connections

4. **Create a Workbench**
   - Select PyTorch notebook image
   - Allocate GPU resources
   - Add environment variables (including `HF_TOKEN` if available)
   - Attach data connections

5. **Clone This Repository**
   ```bash
   git clone https://github.com/cfchase/text-to-image-demo.git
   cd text-to-image-demo
   ```

6. **Follow the Notebooks**
   - `1_experimentation.ipynb`: Initial model testing
   - `2_fine_tuning.ipynb`: Training with custom data
   - `3_remote_inference.ipynb`: Testing deployed models

## Key Components

- **Workbenches**: Jupyter notebook environments for development
- **Pipelines**: Automated ML workflows
- **Model Serving**: Deploy models as REST APIs
- **Storage**: S3-compatible object storage for data and models

## Detailed Setup Instructions

### 1. Storage Configuration

#### Option A: Demo Setup (Local S3)
```bash
oc apply -f setup/setup-s3.yaml
```

This creates:
- MinIO deployment for S3-compatible storage
- Two PVCs for buckets
- Data connections for workbench and pipeline access

#### Option B: Production Setup (External S3)
Create data connections with your S3 credentials:
- Connection 1: "My Storage" - for workbench access
- Connection 2: "Pipeline Artifacts" - for pipeline server

### 2. Workbench Configuration

When creating your workbench:

**Notebook Image**: Choose based on your needs
- Standard Data Science: Basic Python environment
- PyTorch: Includes PyTorch, CUDA support (recommended for this demo)
- TensorFlow: For TensorFlow-based workflows
- Custom: Use your own image with specific dependencies

**Resources**:
- Small: 2 CPUs, 8Gi memory
- Medium: 7 CPUs, 24Gi memory  
- Large: 14 CPUs, 56Gi memory
- GPU: Add 1-2 NVIDIA GPUs (required for this demo)

**Environment Variables**:
```
HF_TOKEN=<your-huggingface-token>  # For model downloads
AWS_S3_ENDPOINT=<s3-endpoint-url>   # Auto-configured if using data connections
AWS_ACCESS_KEY_ID=<access-key>      # Auto-configured if using data connections
AWS_SECRET_ACCESS_KEY=<secret-key>  # Auto-configured if using data connections
AWS_S3_BUCKET=<bucket-name>         # Auto-configured if using data connections
```

### 3. Pipeline Server Setup

1. In your Data Science Project, go to "Pipelines" → "Create pipeline server"
2. Select the "Pipeline Artifacts" data connection
3. Wait for the server to be ready (2-3 minutes)

### 4. Model Serving Configuration

After training your model:

1. Deploy the custom Diffusers runtime:
   ```bash
   cd diffusers-runtime
   make build
   make push
   oc apply -f templates/serving-runtime.yaml
   ```

2. Create a model server in the OpenShift AI dashboard:
   - Model framework: "Custom"
   - Model location: S3 path to your trained model
   - Select the Diffusers serving runtime

## Project Structure

```
text-to-image-demo/
├── README.md                    # This file
├── ARCHITECTURE.md              # Technical architecture details
├── PIPELINES.md                 # Pipeline automation guide
├── SERVING.md                   # Model serving guide
├── DEMO_SCRIPT.md              # Step-by-step demo script
│
├── 1_experimentation.ipynb      # Initial model testing
├── 2_fine_tuning.ipynb         # Custom training workflow
├── 3_remote_inference.ipynb    # Testing served models
│
├── requirements-base.txt        # Base Python dependencies
├── requirements-gpu.txt         # GPU-specific packages
│
├── finetuning_pipeline/        # Kubeflow pipeline components
│   ├── Dreambooth.pipeline     # Pipeline definition
│   ├── get_data.ipynb         # Data preparation step
│   ├── train.ipynb            # Training execution step
│   └── upload.ipynb           # Model upload step
│
├── diffusers-runtime/          # Custom KServe runtime
│   ├── Dockerfile             # Runtime container definition
│   ├── model.py              # KServe predictor implementation
│   └── templates/            # Kubernetes manifests
│
└── setup/                     # Deployment configurations
    └── setup-s3.yaml         # Demo S3 storage setup
```

## Workflow Overview

### 1. Experimentation Phase
- Load pre-trained Stable Diffusion model
- Test basic text-to-image generation
- Identify limitations with generic models

### 2. Training Phase
- Prepare custom training data (images of "Teddy")
- Fine-tune model using Dreambooth technique
- Save trained weights to S3 storage

### 3. Pipeline Automation
- Convert notebooks to pipeline steps
- Create repeatable training workflow
- Enable parameter tuning and experimentation

### 4. Model Serving
- Deploy custom KServe runtime
- Create inference service
- Expose REST API endpoint

### 5. Application Integration
- Test model via REST API
- Integrate with applications
- Monitor performance

## Troubleshooting

### GPU Issues
- **No GPU detected**: Ensure your node has GPU support and correct drivers
- **Out of memory**: Reduce batch size or use gradient checkpointing
- **CUDA errors**: Verify PyTorch and CUDA versions match

### Storage Issues
- **S3 connection failed**: Check credentials and endpoint URL
- **Permission denied**: Verify bucket policies and access keys
- **Upload timeouts**: Check network connectivity and proxy settings

### Pipeline Issues
- **Pipeline server not starting**: Check data connection configuration
- **Pipeline runs failing**: Review logs in pipeline run details
- **Missing artifacts**: Verify S3 bucket permissions

### Serving Issues
- **Model not loading**: Check S3 path and model format
- **Inference errors**: Review KServe pod logs
- **Timeout errors**: Increase resource limits or timeout values

## Additional Resources

- [Red Hat OpenShift AI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)
- [OpenShift AI Learning Resources](https://developers.redhat.com/products/red-hat-openshift-ai/overview)
- [KServe Documentation](https://kserve.github.io/website/)
- [Hugging Face Diffusers](https://huggingface.co/docs/diffusers)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to improve this demo.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
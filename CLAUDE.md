# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Stable Diffusion 3.5 and Dreambooth demonstration project for Red Hat OpenShift AI (formerly RHODS). It demonstrates text-to-image generation, model fine-tuning, and serving using KServe with universal pipeline support for multiple Stable Diffusion model versions.

## Key Commands

### Model Serving (from diffusers-runtime/)
```bash
make help                             # Show all available targets and usage
make build                            # Build KServe runtime container (linux/amd64)
make run                              # Build and run container with segmind/tiny-sd
make push                             # Push both latest and v0.2 tags to registry
make dev                              # Test runtime locally with Python (fast iteration)
make test-v1                          # Test deployed model endpoint (requires port-forward)

# Container runtime options:
make build CONTAINER_RUNTIME=docker   # Use docker instead of podman
make run CONTAINER_RUNTIME=docker     # Run with docker instead of podman

# Available deployment templates:
oc apply -f templates/redhat-dog.yaml      # S3 storage-based deployment
oc apply -f templates/redhat-dog-pvc.yaml  # PVC storage-based deployment  
oc apply -f templates/redhat-dog-hf.yaml   # HuggingFace Hub direct loading
oc apply -f templates/tiny-sd-gpu.yaml     # Lightweight test deployment
```

### MCP Server (from mcp-server/)
```bash
# Development
make install                          # Install dependencies
make test                             # Run unit tests
make lint                             # Run linting checks
make format                           # Format code
make run                              # Run server in development mode

# Docker
make docker-build                     # Build Docker image
make docker-run                       # Run Docker container
make docker-push                      # Push to registry

# Kubernetes
make k8s-deploy                       # Deploy to Kubernetes
make k8s-logs                         # View pod logs
make k8s-port-forward                 # Port forward to service
```

### Python Dependencies
```bash
# Two-stage installation to handle flash-attn build dependencies
pip install -r requirements-base.txt
pip install -r requirements-gpu.txt

# Alternative: Install all at once (if PyTorch is already available)
pip install -r requirements-base.txt && pip install -r requirements-gpu.txt
```

### Initial Setup
```bash
./setup.sh    # Create OpenShift resources and configure the environment
```

### Running Notebooks
Notebooks should be run in sequence:
1. `1_experimentation.ipynb` - Basic text-to-image generation
2. `2_fine_tuning.ipynb` - Fine-tune with Dreambooth
3. `3_remote_inference.ipynb` - Test model serving

## Architecture

### Core Components
- **Jupyter Notebooks**: Interactive ML experimentation in root directory
- **finetuning_pipeline/**: Kubeflow pipeline for automated Dreambooth training
  - Pipeline steps: get_data.ipynb → train.ipynb → upload.ipynb
  - Core training logic: train_dreambooth.py
- **diffusers-runtime/**: Custom KServe runtime for serving Diffusers models
  - model.py: Main KServe predictor implementation (refactored for modularity)
  - device_manager.py: Hardware detection and device management
  - dtype_selector.py: Intelligent dtype selection with hardware-aware fallbacks
  - optimization_manager.py: Memory optimization and pipeline configuration
  - pipeline_loader.py: Universal DiffusionPipeline loading for any Stable Diffusion model
  - Handles v1 inference protocol with configurable optimizations
  - Supports multiple deployment modes (S3, PVC, HuggingFace Hub)
- **mcp-server/**: Model Context Protocol (MCP) server for AI tool integration
  - FastMCP-based server exposing image generation as an AI tool
  - Dual storage backends (file and S3) with automatic cleanup
  - HTTP API for image serving with URL-based delivery
  - Full async/await implementation with comprehensive error handling
- **setup/**: OpenShift/Kubernetes manifests for deployment

### Data Flow
1. Models and data stored in S3-compatible object storage
2. Training pipelines use Data Science Pipelines (Kubeflow)
3. Trained models served via KServe with custom runtime
4. Inference requests handled through REST/gRPC endpoints

## Environment Requirements

- GPU with 45GB+ memory (NVIDIA L40S recommended, A10G minimum for smaller models)
- S3-compatible storage with configured credentials
- OpenShift AI 2.9+ with GPU support
- Key environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_S3_BUCKET

## Development Notes

- The project uses PyTorch with CUDA support for GPU acceleration
- Hugging Face Diffusers library with universal DiffusionPipeline for broad model compatibility
- Primary model: Stable Diffusion 3.5 Medium (also supports SD 1.5, 2.x, XL)
- Container builds target linux/amd64 with configurable runtime (podman/docker)
- Model versions tracked through S3 paths, PVC mounts, or HuggingFace Hub repositories
- Modular architecture for better maintainability and testing
- No automated tests or linting configured - manual testing through notebooks and make dev

### Custom Runtime Features
- **Memory Optimizations**: Configurable attention slicing, VAE slicing, CPU offload
- **DTYPE Management**: Intelligent dtype selection (auto, bfloat16, float16, float32, native)
- **Hardware Detection**: Automatic CUDA/MPS/CPU detection with capability assessment
- **Universal Loading**: Supports loading from S3, PVC, or HuggingFace Hub
- **Environment Configuration**: All optimizations controlled via environment variables

### Environment Variables for Runtime Optimization
```bash
# Data type selection (hardware-aware fallback)
DTYPE=auto                    # Options: auto, bfloat16, float16, float32, native

# Memory optimization toggles
ENABLE_LOW_CPU_MEM=true       # Use accelerate for memory-efficient loading
ENABLE_ATTENTION_SLICING=true # Reduce memory usage during attention computation
ENABLE_VAE_SLICING=true       # Slice VAE computation to reduce memory
ENABLE_CPU_OFFLOAD=true       # Offload model components to CPU when not in use

# Model source configuration
MODEL_ID=/mnt/models          # Local path, S3 path, or HuggingFace model ID
```

### Dependency Installation Issues
- `flash-attn` and `bitsandbytes` require PyTorch to be installed before they can build
- Use split requirements files (`requirements-base.txt` then `requirements-gpu.txt`) to avoid build failures
- If you encounter "ModuleNotFoundError: No module named 'torch'" during pip install, use the two-stage approach

## Git Commit Guidelines

When creating commits in this repository:
- **DO NOT** include Claude Code attribution in commit messages
- **DO NOT** include Claude-specific references in commit messages
- **DO NOT** mention "Generated with Claude Code" or similar attributions
- **DO NOT** add Co-Authored-By references to Claude
- Focus commit messages on the technical changes made
- Use conventional commit format when appropriate (feat:, fix:, docs:, etc.)
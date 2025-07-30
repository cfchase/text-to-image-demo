# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Stable Diffusion and Dreambooth demonstration project for Red Hat OpenShift AI (formerly RHODS). It demonstrates text-to-image generation, model fine-tuning, and serving using KServe.

## Key Commands

### Model Serving (from diffusers-runtime/)
```bash
make build    # Build the KServe runtime container
make push     # Push container to registry
make deploy   # Deploy model to OpenShift
make test-v1  # Test the deployed model endpoint
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
  - model.py: KServe predictor implementation
  - Handles both v1 and v2 inference protocols
- **setup/**: OpenShift/Kubernetes manifests for deployment

### Data Flow
1. Models and data stored in S3-compatible object storage
2. Training pipelines use Data Science Pipelines (Kubeflow)
3. Trained models served via KServe with custom runtime
4. Inference requests handled through REST/gRPC endpoints

## Environment Requirements

- GPU with 24GB+ memory (A10G or better)
- S3-compatible storage with configured credentials
- OpenShift AI 2.9+ with GPU support
- Key environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_S3_BUCKET

## Development Notes

- The project uses PyTorch with CUDA support for GPU acceleration
- Hugging Face Diffusers library for Stable Diffusion models
- No automated tests or linting configured - manual testing through notebooks
- Container builds use podman/docker via Makefile targets
- Model versions tracked through S3 paths and KServe configurations

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
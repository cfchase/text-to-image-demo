# Text-to-Image Demo Architecture

This demo showcases a complete MLOps pipeline for AI-powered text-to-image generation and conversational AI on Red Hat OpenShift AI.

## Architecture Overview

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                       |
|                                                                                                                       |
|              OpenShift Cluster                                                                                        |
|                                                                                                                       |
|   +---------------------------------------------------------------------------+                                       |
|   |                                                                           |                                       |
|   |                                                                           |                                       |
|   |                                  OpenShift AI                             |                                       |
|   |                                                                           |                                       |
|   |   +---------------+     +--------------+         +-------------------+    |           +--------------------+      |
|   |   |               |     |              |         |                   |    |           |  Applications      |      |
|   |   |  Workbenches  |     |  Pipelines   |         |  Model Serving    |    |           |                    |      |
|   |   |               |     |              |         |                   |    |           |                    |      |
|   |   |  Fine Tuning  |     |  Fine Tuning |         | +--------------+  |    |           |  +--------------+  |      |
|   |   |               |     |              |         | |              |  |    |           |  |              |  |      |
|   |   |               |     |              |         | |    Llama 4   |  |    |           |  |  Chatbot UI  |  |      |
|   |   +-------+-------+     +-------+------+    +----+->              <--+----+-----------+-->              |  |      |
|   |           |                     |           |    | |     vLLM     |  |    |           |  |              |  |      |
|   |           +----------+----------+           |    | |              |  |    |           |  |              |  |      |
|   |                      |                      |    | +--------------+  |    |           |  +-------^------+  |      |
|   |                      |                      |    |                   |    |           |          |         |      |
|   |                      |                      |    |                   |    |           |          |         |      |
|   |              +-------v-------+              |    | +---------------+ |    |           |  +-------v------+  |      |
|   |              |               |              |    | |               | |    |           |  |              |  |      |
|   |              |    Storage    |              |    | | Image Gen API | |    |           |  |  Image Gen   |  |      |
|   |              |               |              |    | |               <-+----+-----------+-->  MCP Server  |  |      |
|   |              |    Object     +--------------+----+->   Diffusers   | |    |           |  |              |  |      |
|   |              |    Storage    |                   | |   Custom      | |    |           |  |              |  |      |
|   |              |       or      |                   | |   Runtime     | |    |           |  +--------------+  |      |
|   |              |    PVC RWX    |                   | |               | |    |           |                    |      |
|   |              |               |                   | +---------------+ |    |           |                    |      |
|   |              +---------------+                   |                   |    |           |                    |      |
|   |                                                  |                   |    |           |                    |      |
|   |                                                  +-------------------+    |           +--------------------+      |
|   |                                                                           |                                       |
|   |                                                                           |                                       |
|   |                                                                           |                                       |
|   |                                                                           |                                       |
|   |                                                                           |                                       |
|   +---------------------------------------------------------------------------+                                       |
|                                                                                                                       |
|                                                                                                                       |
+-----------------------------------------------------------------------------------------------------------------------+
```

## Components

### OpenShift AI Platform

#### 1. Workbenches
- **Purpose**: Interactive development environment for model experimentation and fine-tuning
- **Components**: Jupyter notebooks for Stable Diffusion 3.5 exploration and Dreambooth training
- **Key Features**: GPU-enabled workbenches for model development and testing

#### 2. Pipelines  
- **Purpose**: Automated MLOps workflows using Kubeflow Pipelines
- **Components**: 
  - Data preparation pipeline
  - Dreambooth fine-tuning pipeline  
  - Model upload and versioning pipeline
- **Integration**: Seamless handoff from experimentation to production

#### 3. Model Serving
Dual-model serving architecture supporting both text and image generation:

**a) Llama 4 + vLLM Runtime**
- **Purpose**: Conversational AI and text generation
- **Runtime**: vLLM for high-performance LLM inference
- **Integration**: REST API for chatbot interactions

**b) Image Generation API (Custom Diffusers Runtime)**
- **Purpose**: Text-to-image generation using Stable Diffusion models
- **Runtime**: Custom KServe runtime with optimized diffusers pipeline
- **Models Supported**: 
  - Stable Diffusion 3.5 Medium (base model)
  - Fine-tuned Red Hat dog model (cfchase/redhat-dog-sd3)
- **Features**:
  - Configurable memory optimizations (attention slicing, VAE slicing, CPU offload)
  - Multi-dtype support (bfloat16, float16, float32, auto-detection)
  - Universal pipeline loading for multiple SD model versions
  - HuggingFace Hub integration

#### 4. Storage
- **Options**: S3-compatible object storage or PVC with RWX access
- **Purpose**: Model artifacts, training data, and pipeline outputs
- **Integration**: Shared across workbenches, pipelines, and serving components

### External Applications

#### 1. Chatbot UI
- **Purpose**: Unified interface for both text and image generation
- **Integrations**:
  - Direct connection to Llama 4 for conversational AI
  - Connection to Image Gen MCP Server for image requests
- **Features**: Multi-modal AI experience in a single interface

#### 2. Image Gen MCP Server
- **Purpose**: Model Context Protocol server bridging external applications to diffusers runtime
- **Architecture**:
  - FastMCP-based server exposing image generation as AI tool
  - Dual storage backends (file system and S3) with automatic cleanup
  - HTTP API endpoints for image serving with URL-based delivery
  - Full async/await implementation with retry logic
- **Function**: Translates MCP tool calls to KServe inference requests
- **Benefits**: 
  - Modern tooling approach for AI application integration
  - Standardized protocol for AI assistants and agents
  - Efficient image delivery via HTTP URLs instead of base64
  - Automatic cleanup of expired images based on TTL

## Data Flow

### Training Workflow
1. **Experimentation**: Interactive development in Workbenches
2. **Pipeline Execution**: Automated fine-tuning via Kubeflow Pipelines
3. **Model Storage**: Trained models saved to object storage or PVC
4. **Model Serving**: Deployment via KServe with custom runtime

### Inference Workflow
1. **User Request**: Via Chatbot UI for text or image generation
2. **Request Routing**: 
   - Text requests → Llama 4 (vLLM)
   - Image requests → Image Gen MCP Server → Diffusers Runtime
3. **Response Delivery**: Generated content returned to user interface

## Key Technologies

- **Platform**: Red Hat OpenShift AI
- **ML Framework**: PyTorch, Diffusers, Transformers
- **Serving**: KServe with vLLM and custom runtimes
- **Pipelines**: Kubeflow Pipelines
- **Models**: Stable Diffusion 3.5, Llama 4, custom Dreambooth fine-tuned models
- **Integration**: Model Context Protocol (MCP) with FastMCP 2.10.6
- **Container**: Podman/Docker with GPU support
- **API Framework**: FastAPI for HTTP endpoints, httpx for async clients
- **Storage**: S3-compatible (boto3/aioboto3) and local file system

## Deployment Templates

The project includes multiple deployment templates for different use cases:

### Diffusers Runtime Templates
- `redhat-dog.yaml` - S3 storage-based deployment
- `redhat-dog-pvc.yaml` - PVC storage-based deployment  
- `redhat-dog-hf.yaml` - HuggingFace Hub direct loading
- `tiny-sd.yaml/tiny-sd-gpu.yaml` - Lightweight test deployments

### MCP Server Deployment
- `mcp-server/deployment/k8s/deployment.yaml` - Main MCP server deployment
- `mcp-server/deployment/k8s/service.yaml` - Service exposing HTTP endpoints
- `mcp-server/deployment/k8s/configmap.yaml` - Configuration management
- `mcp-server/deployment/k8s/secret.yaml` - Credentials for S3/KServe

This architecture demonstrates a complete MLOps pipeline from research through production, showcasing modern AI application development practices on enterprise Kubernetes platforms with cutting-edge AI tool integration.
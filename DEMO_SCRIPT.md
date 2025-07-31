# Demo Script: OpenShift AI Text-to-Image Workflow

This script guides you through demonstrating the complete ML workflow in OpenShift AI, from experimentation to production deployment.

## Demo Overview

**Duration**: 20-30 minutes  
**Audience**: Developers, Data Scientists, ML Engineers  
**Goal**: Show how OpenShift AI accelerates ML development from notebook to production

## Pre-Demo Setup

### Required Resources
- [ ] OpenShift cluster with OpenShift AI installed
- [ ] GPU node (NVIDIA L40S or A10G)
- [ ] S3 storage configured
- [ ] Demo repository cloned
- [ ] HuggingFace token (optional)

### Pre-staged Assets
- [ ] Data Science Project created: "image-generation"
- [ ] S3 buckets created with demo data
- [ ] Custom runtime container built and pushed
- [ ] (Optional) Pre-trained model in S3 for faster demo

## Demo Flow

### 1. Introduction (2 minutes)

**Script**:
> "Hi, I'm [Name], and today I'll show you Red Hat OpenShift AI - a powerful platform that takes AI/ML projects from experimentation to production. We'll walk through a complete workflow using text-to-image generation as our example."

**Actions**:
- Show OpenShift AI dashboard
- Highlight key sections: Projects, Workbenches, Pipelines, Models

**Key Points**:
- Enterprise-ready ML platform
- Integrated development to deployment
- Based on open source (Kubeflow, KServe)

### 2. Create Workbench (3 minutes)

**Script**:
> "Let's start by creating a development environment. OpenShift AI provides pre-built notebook images with popular ML frameworks."

**Actions**:
1. Navigate to Data Science Projects
2. Click "Create workbench"
3. Show notebook image options
4. Select PyTorch with CUDA
5. Configure resources (GPU, memory)
6. Add environment variables (HF_TOKEN)
7. Attach data connection

**Key Points**:
- GPU-enabled environments
- Pre-installed ML libraries
- Integrated storage connections
- Environment isolation

### 3. Experimentation Phase (5 minutes)

**Script**:
> "Now let's explore our first notebook. We'll use Stable Diffusion, a popular text-to-image model."

**Actions**:
1. Open Notebook 1
2. Check GPU availability
3. Install dependencies
4. Load pre-trained model
5. Generate a generic dog image
6. Try to generate "rhteddy dog" - fails

**Key Points**:
- Easy model exploration
- GPU acceleration
- Foundation models are general
- Need for customization

**Show Result**: Generic dog, not Teddy

### 4. Fine-Tuning Phase (5 minutes)

**Script**:
> "The model doesn't know our specific subject. Let's fine-tune it using Dreambooth with just a few images of Teddy."

**Actions**:
1. Open Notebook 2
2. Show training data (5-10 images)
3. Configure training parameters
4. Start training (mention 15-minute duration)
5. (Skip ahead) Show completed training
6. Save model to S3

**Key Points**:
- Fine-tuning with minimal data
- GPU memory management
- S3 integration for persistence
- Environment variables for configuration

**Show Result**: Model saved to S3

### 5. Test Fine-Tuned Model (2 minutes)

**Script**:
> "Let's test our fine-tuned model to see if it learned about Teddy."

**Actions**:
1. Load fine-tuned model
2. Generate "rhteddy dog" image
3. Show successful generation

**Key Points**:
- Model now recognizes "rhteddy"
- Maintains general capabilities
- Ready for deployment

**Show Result**: Actual Teddy images!

### 6. Pipeline Creation (3 minutes)

**Script**:
> "For production, we need repeatable workflows. Let's create a pipeline to automate this training."

**Actions**:
1. Show pipeline interface
2. Explain DAG structure
3. Show parameterization
4. Demonstrate scheduling options

**Key Points**:
- Reproducible workflows
- Parameter optimization
- Scheduled retraining
- Artifact tracking

### 7. Model Serving (5 minutes)

**Script**:
> "Now let's deploy our model as a REST API that applications can use."

**Actions**:
1. Navigate to Models section
2. Click "Deploy model"
3. Select custom runtime
4. Configure S3 model location
5. Allocate GPU resources
6. Show deployment status
7. Get inference endpoint URL

**Key Points**:
- KServe for model serving
- Auto-scaling capabilities
- GPU acceleration
- REST API interface

### 8. Test Deployment (3 minutes)

**Script**:
> "Let's test our deployed model using the REST API."

**Actions**:
1. Open Notebook 3
2. Configure endpoint URL
3. Send test request
4. Show generated image
5. Run performance benchmark

**Key Points**:
- Standard inference protocol
- Sub-minute response times
- Production-ready API
- Easy integration

### 9. Application Integration (2 minutes)

**Script**:
> "Here's how applications can use our model."

**Actions**:
1. Show Python client code
2. Show curl command
3. Mention other integration options

**Key Points**:
- Language-agnostic REST API
- Simple integration
- Scalable architecture

### 10. Conclusion (2 minutes)

**Script**:
> "We've taken a journey from experimentation to production - all within OpenShift AI. We explored models, fine-tuned with our data, created pipelines, and deployed a production API."

**Summary Points**:
- Complete ML lifecycle
- GPU acceleration throughout
- Enterprise features (security, scaling)
- Open source foundation

**Call to Action**:
> "OpenShift AI makes AI/ML accessible and production-ready. I can't wait to see what you'll build!"

## Demo Variations

### Short Version (10 minutes)
1. Skip pipeline creation
2. Use pre-trained model
3. Focus on workbench → serving flow

### Technical Deep Dive (45 minutes)
1. Show architecture diagrams
2. Examine custom runtime code
3. Demonstrate monitoring
4. Discuss scaling strategies

### Executive Version (15 minutes)
1. Focus on business value
2. Emphasize ease of use
3. Show cost optimization (GPU sharing)
4. Highlight security features

## Common Questions & Answers

**Q: How long does training take?**
> A: "With our GPU-enabled nodes, fine-tuning takes about 15 minutes. Without GPU, it could take hours."

**Q: Can this work with other models?**
> A: "Absolutely! OpenShift AI supports any framework - PyTorch, TensorFlow, scikit-learn, and custom frameworks."

**Q: What about data privacy?**
> A: "Everything runs in your OpenShift cluster. Data never leaves your environment, and we support air-gapped deployments."

**Q: How does this compare to cloud AI services?**
> A: "OpenShift AI gives you the flexibility of open source with enterprise support, runs anywhere, and avoids vendor lock-in."

**Q: What about costs?**
> A: "GPU resources are shared efficiently, models auto-scale to zero when not used, and you only pay for what you consume."

## Troubleshooting

### GPU Not Available
- Check node labels
- Verify GPU operator installed
- Ensure sufficient quota

### Model Won't Load
- Verify S3 credentials
- Check model path
- Ensure sufficient memory

### Slow Performance
- Confirm GPU is being used
- Check resource limits
- Verify model is cached

### Pipeline Fails
- Check data connection
- Verify container images
- Review step logs

## Post-Demo Resources

Share these with attendees:
1. This GitHub repository
2. OpenShift AI documentation
3. Trial/sandbox environment
4. Community forums
5. Training materials

## Tips for Success

### Do's
- ✅ Test everything beforehand
- ✅ Have backup plans
- ✅ Keep energy high
- ✅ Encourage questions
- ✅ Show real results

### Don'ts
- ❌ Don't skip GPU check
- ❌ Don't rush training
- ❌ Don't assume knowledge
- ❌ Don't hide failures
- ❌ Don't forget to summarize

## Customization Options

### Industry-Specific Demos
- **Healthcare**: X-ray analysis
- **Manufacturing**: Defect detection  
- **Retail**: Product recognition
- **Finance**: Document processing

### Model Alternatives
- **LLMs**: Fine-tune for chatbots
- **Vision**: Object detection
- **Time Series**: Forecasting
- **Audio**: Speech recognition

Remember: The goal is to inspire and educate. Show the art of the possible with OpenShift AI!
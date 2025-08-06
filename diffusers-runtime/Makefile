# Include environment files if they exist
-include .env
-include .env.local

# Container configuration
CONTAINER_RUNTIME ?= podman
IMAGE_REGISTRY ?= quay.io/cfchase
IMAGE_NAME ?= diffusers-runtime
IMAGE_TAG ?= latest

# Model configuration
MODEL_ID ?= segmind/tiny-sd
PORT ?= 8080

# Deployment configuration
DEPLOY_TEMPLATE ?= redhat-dog-hf

# Computed image name
IMAGE_FULL = $(IMAGE_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: help build push run dev test-v1 deploy undeploy

help: ## Show this help message
	@echo "Diffusers Runtime - Custom KServe runtime for Stable Diffusion models"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment variables:"
	@echo "  CONTAINER_RUNTIME  Container runtime to use (default: podman)"
	@echo "  IMAGE_REGISTRY     Container registry (default: quay.io/cfchase)"
	@echo "  IMAGE_TAG          Image tag (default: latest)"
	@echo "  MODEL_ID           Model to use (default: segmind/tiny-sd)"
	@echo "  PORT               Port to expose (default: 8080)"
	@echo "  DEPLOY_TEMPLATE    Template to deploy (default: redhat-dog-hf)"
	@echo ""
	@echo "Available templates:"
	@echo "  tiny-sd            Basic tiny-sd deployment"
	@echo "  tiny-sd-gpu        Tiny-sd with GPU support"
	@echo "  redhat-dog         Redhat dog model deployment"
	@echo "  redhat-dog-pvc     Redhat dog with PVC storage"
	@echo "  redhat-dog-hf      Redhat dog from HuggingFace"
	@echo "  diffusers-serving-runtime  Generic serving runtime"
	@echo ""
	@echo "Examples:"
	@echo "  make build && make run      # Build and run container"
	@echo "  make deploy                 # Deploy redhat-dog-hf (default)"
	@echo "  make deploy DEPLOY_TEMPLATE=redhat-dog  # Deploy redhat-dog"
	@echo "  make undeploy DEPLOY_TEMPLATE=redhat-dog  # Remove redhat-dog"
	@echo "  make build CONTAINER_RUNTIME=docker  # Use docker instead of podman"

build: ## Build the container image
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t $(IMAGE_FULL) -f docker/Dockerfile .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) tag $(IMAGE_FULL) $(IMAGE_REGISTRY)/$(IMAGE_NAME):v0.2
	$(CONTAINER_RUNTIME) push $(IMAGE_FULL)
	$(CONTAINER_RUNTIME) push $(IMAGE_REGISTRY)/$(IMAGE_NAME):v0.2

run: ## Run container with configured model
	$(CONTAINER_RUNTIME) run --rm -ePORT=$(PORT) -eMODEL_ID=$(MODEL_ID) -p$(PORT):$(PORT) $(IMAGE_FULL)

deploy: ## Deploy InferenceService to OpenShift (use DEPLOY_TEMPLATE to specify)
	@if [ ! -f templates/$(DEPLOY_TEMPLATE).yaml ]; then \
		echo "Error: Template 'templates/$(DEPLOY_TEMPLATE).yaml' not found"; \
		echo "Available templates:"; \
		ls -1 templates/*.yaml | sed 's|templates/||' | sed 's|\.yaml||'; \
		exit 1; \
	fi
	@echo "Deploying $(DEPLOY_TEMPLATE) InferenceService..."
	oc apply -f templates/$(DEPLOY_TEMPLATE).yaml

undeploy: ## Remove InferenceService from OpenShift (use DEPLOY_TEMPLATE to specify)
	@if [ ! -f templates/$(DEPLOY_TEMPLATE).yaml ]; then \
		echo "Error: Template 'templates/$(DEPLOY_TEMPLATE).yaml' not found"; \
		exit 1; \
	fi
	@echo "Removing $(DEPLOY_TEMPLATE) InferenceService..."
	oc delete -f templates/$(DEPLOY_TEMPLATE).yaml

dev: ## Run locally with Python for development
	MODEL_ID=$(MODEL_ID) PORT=$(PORT) python model.py --model_name model

test-v1: ## Test the running service with a sample request
	curl -H "Content-Type: application/json" localhost:$(PORT)/v1/models/model:predict -d @./scripts/v1_input.json | jq -r '.predictions[0].image.b64' | base64 -d > "example_output.png"

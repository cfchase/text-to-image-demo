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
	@echo ""
	@echo "Examples:"
	@echo "  make build && make run      # Build and run container with tiny-sd model"
	@echo "  make run                    # Run existing container with tiny-sd model" 
	@echo "  make dev                    # Run locally with Python for development"
	@echo "  make build CONTAINER_RUNTIME=docker  # Use docker instead of podman"

build: ## Build the container image
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t $(IMAGE_FULL) -f docker/Dockerfile .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) tag $(IMAGE_FULL) $(IMAGE_REGISTRY)/$(IMAGE_NAME):v0.2
	$(CONTAINER_RUNTIME) push $(IMAGE_FULL)
	$(CONTAINER_RUNTIME) push $(IMAGE_REGISTRY)/$(IMAGE_NAME):v0.2

run: ## Run container with configured model
	$(CONTAINER_RUNTIME) run --rm -ePORT=$(PORT) -eMODEL_ID=$(MODEL_ID) -p$(PORT):$(PORT) $(IMAGE_FULL)

deploy: ## Deploy tiny-sd InferenceService to OpenShift
	oc apply -f templates/tiny-sd.yaml

undeploy: ## Remove tiny-sd InferenceService from OpenShift
	oc delete -f templates/tiny-sd.yaml

dev: ## Run locally with Python for development
	MODEL_ID=$(MODEL_ID) PORT=$(PORT) python model.py --model_name model

test-v1: ## Test the running service with a sample request
	curl -H "Content-Type: application/json" localhost:$(PORT)/v1/models/model:predict -d @./scripts/v1_input.json | jq -r '.predictions[0].image.b64' | base64 -d > "example_output.png"

CONTAINER_RUNTIME ?= podman

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
	@echo ""
	@echo "Examples:"
	@echo "  make build && make run      # Build and run container with tiny-sd model"
	@echo "  make run                    # Run existing container with tiny-sd model" 
	@echo "  make dev                    # Run locally with Python for development"
	@echo "  make build CONTAINER_RUNTIME=docker  # Use docker instead of podman"

build: ## Build the container image
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t quay.io/cfchase/diffusers-runtime:latest -f docker/Dockerfile .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) tag quay.io/cfchase/diffusers-runtime:latest quay.io/cfchase/diffusers-runtime:v0.2
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:latest
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:v0.2

run: ## Run container with segmind/tiny-sd model
	$(CONTAINER_RUNTIME) run --rm -ePORT=8080 -eMODEL_ID=segmind/tiny-sd -p8080:8080 quay.io/cfchase/diffusers-runtime:latest

deploy: ## Deploy tiny-sd InferenceService to OpenShift
	oc apply -f templates/tiny-sd.yaml

undeploy: ## Remove tiny-sd InferenceService from OpenShift
	oc delete -f templates/tiny-sd.yaml

dev: ## Run locally with Python for development (segmind/tiny-sd)
	MODEL_ID=segmind/tiny-sd python model.py --model_name model

test-v1: ## Test the running service with a sample request
	curl -H "Content-Type: application/json" localhost:8080/v1/models/model:predict -d @./scripts/v1_input.json | jq -r '.predictions[0].image.b64' | base64 -d > "example_output.png"

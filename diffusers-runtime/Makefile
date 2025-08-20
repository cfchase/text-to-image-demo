CONTAINER_RUNTIME ?= podman
TEMPLATE ?= redhat-dog-hf
NAMESPACE ?= $(shell oc project -q 2>/dev/null || echo "default")

.PHONY: help build push run dev test-v1 deploy undeploy status logs

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
	@echo "  TEMPLATE          Template to deploy (default: redhat-dog-hf)"
	@echo "  NAMESPACE         Target namespace (current: $(NAMESPACE))"
	@echo ""
	@echo "Available templates:"
	@ls templates/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml//' | sed 's/^/  - /'
	@echo ""
	@echo "Examples:"
	@echo "  make deploy                 # Deploy redhat-dog-hf (default)"
	@echo "  make deploy TEMPLATE=tiny-sd-gpu  # Deploy tiny-sd GPU model"
	@echo "  make build && make run      # Build and run container with tiny-sd model"
	@echo "  make dev                    # Run locally with Python for development"

build: ## Build the container image
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t quay.io/cfchase/diffusers-runtime:latest -f docker/Dockerfile .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) tag quay.io/cfchase/diffusers-runtime:latest quay.io/cfchase/diffusers-runtime:v0.2
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:latest
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:v0.2

run: ## Run container with segmind/tiny-sd model
	$(CONTAINER_RUNTIME) run --rm -ePORT=8080 -eMODEL_ID=segmind/tiny-sd -p8080:8080 quay.io/cfchase/diffusers-runtime:latest

deploy: ## Deploy InferenceService to OpenShift
	@echo "🚀 Deploying $(TEMPLATE) to namespace $(NAMESPACE)..."
	@if [ ! -f "templates/$(TEMPLATE).yaml" ]; then \
		echo "❌ Error: templates/$(TEMPLATE).yaml not found"; \
		echo "Available templates:"; \
		ls templates/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml//' | sed 's/^/  - /'; \
		exit 1; \
	fi
	@oc apply -f templates/$(TEMPLATE).yaml
	@echo "⏳ Waiting for deployment to be ready..."
	@sleep 3
	@echo "✅ Deployment initiated. Check status with 'make status'"

undeploy: ## Remove InferenceService from OpenShift
	@echo "🗑️  Removing $(TEMPLATE) deployment..."
	@if [ -f "templates/$(TEMPLATE).yaml" ]; then \
		oc delete -f templates/$(TEMPLATE).yaml --ignore-not-found=true; \
	else \
		echo "⚠️  templates/$(TEMPLATE).yaml not found"; \
	fi
	@echo "✅ Deployment removed"

status: ## Show deployment status
	@echo "📊 Diffusers Runtime Status"
	@echo "=========================="
	@echo ""
	@echo "InferenceServices:"
	@oc get inferenceservice -o wide 2>/dev/null || echo "  None found"
	@echo ""
	@echo "ServingRuntimes:"
	@oc get servingruntime 2>/dev/null || echo "  None found"
	@echo ""
	@echo "Pods:"
	@oc get pods | grep -E "redhat-dog|tiny-sd" 2>/dev/null || echo "  No diffusers pods found"

logs: ## Show deployment logs
	@echo "📝 Fetching logs for diffusers runtime pods..."
	@POD=$$(oc get pods -o name 2>/dev/null | grep -E "redhat-dog|tiny-sd" | head -1); \
	if [ -n "$$POD" ]; then \
		oc logs $$POD -c kserve-container --tail=100 -f; \
	else \
		echo "❌ No diffusers runtime pods found"; \
	fi

dev: ## Run locally with Python for development (segmind/tiny-sd)
	MODEL_ID=segmind/tiny-sd python model.py --model_name model

test-v1: ## Test the running service with a sample request
	curl -H "Content-Type: application/json" localhost:8080/v1/models/model:predict -d @./scripts/v1_input.json | jq -r '.predictions[0].image.b64' | base64 -d > "example_output.png"

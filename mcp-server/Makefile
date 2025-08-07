# MCP Server Deployment Makefile
CONTAINER_RUNTIME ?= docker
REGISTRY ?= quay.io/cfchase
IMAGE_NAME ?= image-generation-mcp
IMAGE_TAG ?= latest
IMAGE := $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# Deployment variables
MCP_SERVER_NAME ?= image-generation-mcp
DIFFUSERS_RUNTIME_URL ?= http://redhat-dog-predictor:8080
DIFFUSERS_MODEL_ID ?= model

.PHONY: help build push deploy undeploy test test-local clean

help: ## Show this help message
	@echo "MCP Server - Simple deployment for OpenShift"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment Variables:"
	@echo "  CONTAINER_RUNTIME       Container runtime (default: docker)"
	@echo "  REGISTRY               Container registry (default: quay.io/cfchase)"
	@echo "  IMAGE_TAG              Image tag (default: latest)"
	@echo "  DIFFUSERS_RUNTIME_URL  Diffusers runtime URL (default: http://redhat-dog-predictor)"
	@echo ""
	@echo "Example:"
	@echo "  make build push deploy  # Build, push, and deploy to OpenShift"

build: ## Build container image
	$(CONTAINER_RUNTIME) build -t $(IMAGE) .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) push $(IMAGE)

deploy: ## Deploy to OpenShift
	@echo "Deploying MCP Server to OpenShift..."
	@export MCP_SERVER_NAME=$(MCP_SERVER_NAME) \
		MCP_IMAGE=$(IMAGE) \
		DIFFUSERS_RUNTIME_URL=$(DIFFUSERS_RUNTIME_URL) \
		DIFFUSERS_MODEL_ID=$(DIFFUSERS_MODEL_ID) && \
	envsubst < templates/mcp-server.yaml | oc apply -f -
	@echo ""
	@echo "Deployment complete. To access the MCP server:"
	@echo "  oc get route $(MCP_SERVER_NAME)"

undeploy: ## Remove deployment from OpenShift
	@echo "Removing MCP Server from OpenShift..."
	@export MCP_SERVER_NAME=$(MCP_SERVER_NAME) \
		MCP_IMAGE=$(IMAGE) \
		DIFFUSERS_RUNTIME_URL=$(DIFFUSERS_RUNTIME_URL) \
		DIFFUSERS_MODEL_ID=$(DIFFUSERS_MODEL_ID) && \
	envsubst < templates/mcp-server.yaml | oc delete -f -

test: ## Test deployed MCP server on OpenShift
	@echo "Testing MCP Server on OpenShift..."
	@./scripts/test_with_port_forward.sh

test-local: ## Test local MCP server
	@echo "Testing local MCP Server..."
	MCP_URL="http://127.0.0.1:8000/mcp" .venv/bin/python scripts/test_generate.py

clean: ## Clean generated images and temp files
	rm -rf images/
	rm -rf test_output/
	rm -f example_output.png
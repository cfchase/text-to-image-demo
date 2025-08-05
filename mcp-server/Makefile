# Include environment files if they exist
-include .env
-include .env.local

.PHONY: help install test test-diffusers run clean build push deploy deploy-dev deploy-staging deploy-prod undeploy undeploy-dev undeploy-staging undeploy-prod list-storage-classes kustomize-build kustomize-diff

help: ## Show this help message
	@echo "MCP Server - Image Generation Server using diffusers-runtime"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment Variables:"
	@echo "  DIFFUSERS_RUNTIME_URL   URL of diffusers-runtime (default: http://0.0.0.0:8080)"
	@echo "  DIFFUSERS_MODEL_ID      Model ID to use (default: model)"
	@echo "  IMAGE_OUTPUT_PATH       Directory to save images (default: /tmp/image-generator)"
	@echo ""
	@echo "Quick Start:"
	@echo "  make run           # Starts unified server with MCP on /mcp and images on /images"
	@echo ""
	@echo "Deployment Options (using Kustomize):"
	@echo "  make deploy-dev    # Deploy development environment (PVC, HTTP, debug logging)"
	@echo "  make deploy-staging # Deploy staging environment (ephemeral storage, HTTPS)"
	@echo "  make deploy-prod   # Deploy production environment (PVC, HPA, security policies)"
	@echo "  make kustomize-build ENV=<env>  # Build manifests for environment (dev/staging/production)"
	@echo "  make kustomize-diff ENV=<env>   # Show diff between current and new manifests"
	@echo "  make list-storage-classes       # Show available storage classes in cluster"
	@echo ""
	@echo "Integrated Deployment (MCP + Diffusers-Runtime):"
	@echo "  make deploy-with-diffusers-dev  # Deploy complete development stack"
	@echo "  make deploy-with-diffusers-prod # Deploy complete production stack"
	@echo "  make test-connectivity ENV=<env> # Test MCP<->diffusers connectivity"
	@echo "  make test-integration ENV=<env>  # Test end-to-end image generation"
	@echo "  make check-services ENV=<env>    # Check status of all services"

install: ## Install dependencies using uv
	uv pip install -e .

test: ## Test the generate_image function directly
	.venv/bin/python test_generate.py

test-diffusers: ## Test connection to diffusers-runtime service
	@echo "Testing diffusers-runtime at http://0.0.0.0:8080..."
	@curl -s -X POST http://0.0.0.0:8080/v1/models/model:predict \
		-H "Content-Type: application/json" \
		-d '{"instances": [{"prompt": "test image", "num_inference_steps": 20}]}' \
		| jq -r '.predictions[0].model_name' || echo "Error: Is diffusers-runtime running? (make dev in diffusers-runtime/)"

run: ## Run unified server with MCP on /mcp and images on /images
	.venv/bin/python main.py --port 8000

clean: ## Clean generated images
	rm -rf images/
	rm -rf /tmp/image-generator/
	rm -rf test_output/
	rm -f example_output.png

# Container and OpenShift deployment targets
CONTAINER_RUNTIME ?= podman
IMAGE_REGISTRY ?= quay.io/cfchase
IMAGE_NAME ?= mcp-server
IMAGE_TAG ?= latest

build: ## Build container image for OpenShift deployment
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t $(IMAGE_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) .

push: ## Push container image to registry
	$(CONTAINER_RUNTIME) push $(IMAGE_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

deploy: deploy-staging ## Deploy MCP server to OpenShift (default: staging environment)

deploy-dev: ## Deploy MCP server development environment (PVC, HTTP, debug logging)
	@echo "Deploying MCP server development environment..."
	@if ! oc get project > /dev/null 2>&1; then \
		echo "Error: Not logged into OpenShift or no project selected"; \
		echo "Run: oc login <cluster-url> && oc project <your-project>"; \
		exit 1; \
	fi
	@echo "Current project: $$(oc project -q)"
	@echo "🚀 Deploying development environment with:"
	@echo "   - Persistent storage (5Gi PVC)"
	@echo "   - HTTP (no TLS for easier debugging)"
	@echo "   - DEBUG logging"
	@echo "   - Minimal resources"
	kustomize build kustomize/overlays/dev | oc apply -f -
	@echo "Waiting for deployment to be ready..."
	oc rollout status deployment/mcp-server -n mcp-server-dev --timeout=300s
	@echo "Development MCP Server deployed successfully!"
	@echo "MCP endpoint: http://$$(oc get route mcp-server -n mcp-server-dev -o jsonpath='{.spec.host}')/mcp"
	@echo "Images endpoint: http://$$(oc get route mcp-server -n mcp-server-dev -o jsonpath='{.spec.host}')/images"
	@echo "Health check: http://$$(oc get route mcp-server -n mcp-server-dev -o jsonpath='{.spec.host}')/health"
	@echo "PVC Status: $$(oc get pvc mcp-server-images -n mcp-server-dev -o jsonpath='{.status.phase}' 2>/dev/null || echo 'Not found')"

deploy-staging: ## Deploy MCP server staging environment (ephemeral storage, HTTPS)
	@echo "Deploying MCP server staging environment..."
	@if ! oc get project > /dev/null 2>&1; then \
		echo "Error: Not logged into OpenShift or no project selected"; \
		echo "Run: oc login <cluster-url> && oc project <your-project>"; \
		exit 1; \
	fi
	@echo "Current project: $$(oc project -q)"
	@echo "🔄 Deploying staging environment with:"
	@echo "   - Ephemeral storage (emptyDir)"
	@echo "   - HTTPS with TLS termination"
	@echo "   - INFO logging"
	@echo "   - Standard resources"
	kustomize build kustomize/overlays/staging | oc apply -f -
	@echo "Waiting for deployment to be ready..."
	oc rollout status deployment/mcp-server -n mcp-server-staging --timeout=300s
	@echo "Staging MCP Server deployed successfully!"
	@echo "MCP endpoint: https://$$(oc get route mcp-server -n mcp-server-staging -o jsonpath='{.spec.host}')/mcp"
	@echo "Images endpoint: https://$$(oc get route mcp-server-images -n mcp-server-staging -o jsonpath='{.spec.host}')/images"
	@echo "Health check: https://$$(oc get route mcp-server -n mcp-server-staging -o jsonpath='{.spec.host}')/health"

deploy-prod: ## Deploy MCP server production environment (PVC, HPA, security policies)
	@echo "Deploying MCP server production environment..."
	@if ! oc get project > /dev/null 2>&1; then \
		echo "Error: Not logged into OpenShift or no project selected"; \
		echo "Run: oc login <cluster-url> && oc project <your-project>"; \
		exit 1; \
	fi
	@echo "Current project: $$(oc project -q)"
	@echo "⚠️  This will deploy production environment with:"
	@echo "   - High availability (2+ replicas with anti-affinity)"
	@echo "   - Horizontal Pod Autoscaler (2-5 replicas)"
	@echo "   - Persistent storage (50Gi PVC)"
	@echo "   - Network policies for security"
	@echo "   - Pod disruption budget"
	@echo "   - Enhanced resource limits"
	@read -p "Continue with production deployment? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		kustomize build kustomize/overlays/production | oc apply -f -; \
		echo "Waiting for deployment to be ready..."; \
		oc rollout status deployment/mcp-server -n mcp-server-production --timeout=600s; \
		echo "Production MCP Server deployed successfully!"; \
		echo "MCP endpoint: https://$$(oc get route mcp-server -n mcp-server-production -o jsonpath='{.spec.host}')/mcp"; \
		echo "Health check: https://$$(oc get route mcp-server -n mcp-server-production -o jsonpath='{.spec.host}')/health"; \
		echo "Scaling: 2-5 replicas based on CPU/Memory usage"; \
		echo "PVC Status: $$(oc get pvc mcp-server-images -n mcp-server-production -o jsonpath='{.status.phase}' 2>/dev/null || echo 'Not found')"; \
	else \
		echo "Production deployment cancelled."; \
	fi

list-storage-classes: ## List available storage classes in OpenShift cluster
	@echo "=== Available Storage Classes ==="
	@if ! oc get project > /dev/null 2>&1; then \
		echo "Error: Not logged into OpenShift or no project selected"; \
		echo "Run: oc login <cluster-url> && oc project <your-project>"; \
		exit 1; \
	fi
	@echo "Cluster: $$(oc whoami --show-server)"
	@echo "Project: $$(oc project -q)"
	@echo ""
	@oc get storageclass -o custom-columns="NAME:.metadata.name,PROVISIONER:.provisioner,RECLAIM POLICY:.reclaimPolicy,VOLUME BINDING:.volumeBindingMode,ALLOW EXPANSION:.allowVolumeExpansion,DEFAULT:.metadata.annotations.storageclass\.kubernetes\.io/is-default-class" 2>/dev/null || \
		(echo "Could not retrieve storage classes. You may not have sufficient permissions." && \
		 echo "Try: oc get storageclass" && \
		 echo "Or contact your cluster administrator.")
	@echo ""
	@echo "To use a specific storage class in your deployment:"
	@echo "1. Edit the PVC configuration in kustomize/overlays/production/pvc.yaml"
	@echo "2. Uncomment and set the storageClassName field"
	@echo "3. Deploy using: make deploy-pvc"

undeploy: undeploy-staging ## Remove MCP server from OpenShift (default: staging environment)

undeploy-dev: ## Remove MCP server development environment
	@echo "Removing MCP server development environment..."
	@echo "⚠️  This will also delete the PVC and all stored images in development!"
	@read -p "Continue with removal? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		kustomize build kustomize/overlays/dev | oc delete -f - --ignore-not-found=true; \
		echo "Development MCP server removed successfully!"; \
	else \
		echo "Removal cancelled."; \
	fi

undeploy-staging: ## Remove MCP server staging environment
	@echo "Removing MCP server staging environment..."
	kustomize build kustomize/overlays/staging | oc delete -f - --ignore-not-found=true
	@echo "Staging MCP server removed successfully!"

undeploy-prod: ## Remove MCP server production environment
	@echo "Removing MCP server production environment..."
	@echo "⚠️  This will also delete the PVC and all stored images in production!"
	@read -p "Continue with removal? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		kustomize build kustomize/overlays/production | oc delete -f - --ignore-not-found=true; \
		echo "Production MCP server removed successfully!"; \
	else \
		echo "Removal cancelled."; \
	fi

build-and-deploy-dev: ## Build, push, and deploy MCP server (development)
	$(MAKE) build
	$(MAKE) push
	$(MAKE) deploy-dev

build-and-deploy-staging: ## Build, push, and deploy MCP server (staging)
	$(MAKE) build
	$(MAKE) push
	$(MAKE) deploy-staging

build-and-deploy-prod: ## Build, push, and deploy MCP server (production)
	$(MAKE) build
	$(MAKE) push
	$(MAKE) deploy-prod

kustomize-build: ## Build Kustomize manifests for specified environment (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make kustomize-build ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ ! -d "kustomize/overlays/$(ENV)" ]; then \
		echo "Error: Environment '$(ENV)' not found. Available: dev, staging, production"; \
		exit 1; \
	fi
	@echo "Building Kustomize manifests for $(ENV) environment..."
	kustomize build kustomize/overlays/$(ENV)

kustomize-diff: ## Show diff between current deployment and Kustomize manifests (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make kustomize-diff ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ ! -d "kustomize/overlays/$(ENV)" ]; then \
		echo "Error: Environment '$(ENV)' not found. Available: dev, staging, production"; \
		exit 1; \
	fi
	@echo "Showing diff for $(ENV) environment..."
	kustomize build kustomize/overlays/$(ENV) | oc diff -f - || true

status: ## Show deployment status across all environments
	@echo "=== MCP Server Deployment Status Across All Environments ==="
	@for ns in mcp-server-dev mcp-server-staging mcp-server-production; do \
		echo ""; \
		echo "=== Environment: $$ns ==="; \
		if oc get namespace $$ns > /dev/null 2>&1; then \
			echo "Pods:"; \
			oc get pods -l app=mcp-server -n $$ns -o wide 2>/dev/null || echo "No MCP server pods found"; \
			echo "Services:"; \
			oc get svc -l app=mcp-server -n $$ns 2>/dev/null || echo "No MCP server services found"; \
			echo "Routes:"; \
			oc get routes -l app=mcp-server -n $$ns 2>/dev/null || echo "No MCP server routes found"; \
			echo "PVCs:"; \
			oc get pvc -l app=mcp-server -n $$ns 2>/dev/null || echo "No PVCs found"; \
		else \
			echo "Namespace $$ns not found - environment not deployed"; \
		fi; \
	done

logs: ## Show MCP server logs (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make logs ENV=dev|staging|production"; \
		exit 1; \
	fi
	@ns="mcp-server-$(ENV)"; \
	echo "=== MCP Server Logs from $$ns ==="; \
	if oc get deployment mcp-server -n $$ns > /dev/null 2>&1; then \
		oc logs -l app=mcp-server -n $$ns --tail=100 -f; \
	else \
		echo "MCP server deployment not found in $$ns. Run 'make deploy-$(ENV)' first."; \
	fi

# Integrated deployment targets for complete solution
deploy-with-diffusers-dev: ## Deploy both diffusers-runtime and MCP server for development
	@echo "🚀 Deploying complete development stack..."
	@echo "1. Deploying tiny-sd diffusers-runtime service..."
	@if [ ! -f ../diffusers-runtime/templates/tiny-sd.yaml ]; then \
		echo "Error: diffusers-runtime templates not found. Run from correct directory."; \
		exit 1; \
	fi
	oc apply -f ../diffusers-runtime/templates/tiny-sd.yaml
	@echo "2. Waiting for diffusers-runtime to be ready..."
	@echo "   (This may take several minutes for model download and loading)"
	oc wait --for=condition=Ready pod -l serving.kserve.io/inferenceservice=tiny-sd --timeout=600s || \
		(echo "Warning: Diffusers-runtime may still be starting up. Check with: oc get pods -l serving.kserve.io/inferenceservice=tiny-sd")
	@echo "3. Deploying MCP server..."
	$(MAKE) deploy-dev
	@echo "✅ Development stack deployed successfully!"
	@echo ""
	@echo "🔗 Service URLs:"
	@echo "   Diffusers API: http://$$(oc get route tiny-sd 2>/dev/null -o jsonpath='{.spec.host}' || echo 'tiny-sd.$(shell oc project -q).svc.cluster.local:8080')"
	@echo "   MCP Server: http://$$(oc get route mcp-server -n mcp-server-dev -o jsonpath='{.spec.host}')"

deploy-with-diffusers-prod: ## Deploy both diffusers-runtime and MCP server for production
	@echo "🚀 Deploying complete production stack..."
	@echo "⚠️  This will deploy production diffusers-runtime (redhat-dog) with GPU requirements"
	@read -p "Continue with production deployment? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "1. Deploying redhat-dog diffusers-runtime service..."; \
		if [ ! -f ../diffusers-runtime/templates/redhat-dog.yaml ]; then \
			echo "Error: diffusers-runtime templates not found. Run from correct directory."; \
			exit 1; \
		fi; \
		oc apply -f ../diffusers-runtime/templates/redhat-dog.yaml; \
		echo "2. Waiting for diffusers-runtime to be ready..."; \
		echo "   (This may take several minutes for model download and GPU initialization)"; \
		oc wait --for=condition=Ready pod -l serving.kserve.io/inferenceservice=redhat-dog --timeout=900s || \
			(echo "Warning: Diffusers-runtime may still be starting up. Check with: oc get pods -l serving.kserve.io/inferenceservice=redhat-dog"); \
		echo "3. Deploying MCP server..."; \
		$(MAKE) deploy-prod; \
		echo "✅ Production stack deployed successfully!"; \
		echo ""; \
		echo "🔗 Service URLs:"; \
		echo "   Diffusers API: https://$$(oc get route redhat-dog 2>/dev/null -o jsonpath='{.spec.host}' || echo 'redhat-dog.$(shell oc project -q).svc.cluster.local:8080')"; \
		echo "   MCP Server: https://$$(oc get route mcp-server -n mcp-server-production -o jsonpath='{.spec.host}')"; \
	else \
		echo "Production deployment cancelled."; \
	fi

undeploy-with-diffusers-dev: ## Remove both MCP server and diffusers-runtime (development)
	@echo "🗑️  Removing complete development stack..."
	@echo "⚠️  This will remove both MCP server and diffusers-runtime services"
	@read -p "Continue with removal? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "1. Removing MCP server..."; \
		$(MAKE) undeploy-dev; \
		echo "2. Removing diffusers-runtime..."; \
		oc delete -f ../diffusers-runtime/templates/tiny-sd.yaml --ignore-not-found=true; \
		echo "✅ Development stack removed successfully!"; \
	else \
		echo "Removal cancelled."; \
	fi

undeploy-with-diffusers-prod: ## Remove both MCP server and diffusers-runtime (production)
	@echo "🗑️  Removing complete production stack..."
	@echo "⚠️  This will remove both MCP server and diffusers-runtime services and ALL DATA"
	@read -p "Continue with removal? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "1. Removing MCP server..."; \
		$(MAKE) undeploy-prod; \
		echo "2. Removing diffusers-runtime..."; \
		oc delete -f ../diffusers-runtime/templates/redhat-dog.yaml --ignore-not-found=true; \
		echo "✅ Production stack removed successfully!"; \
	else \
		echo "Removal cancelled."; \
	fi

# Service connectivity and integration testing targets
test-connectivity: ## Test connectivity between MCP server and diffusers-runtime (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make test-connectivity ENV=dev|staging|production"; \
		exit 1; \
	fi
	@echo "🔍 Testing connectivity for $(ENV) environment..."
	@ns="mcp-server-$(ENV)"; \
	if [ "$(ENV)" = "dev" ] || [ "$(ENV)" = "staging" ]; then \
		service="tiny-sd"; \
	else \
		service="redhat-dog"; \
	fi; \
	echo "Environment: $$ns"; \
	echo "Expected diffusers service: $$service"; \
	echo ""; \
	echo "1. Checking if MCP server pod exists..."; \
	if ! oc get pods -l app=mcp-server -n $$ns -o name | head -1 > /dev/null 2>&1; then \
		echo "❌ No MCP server pods found in $$ns. Deploy first with: make deploy-$(ENV)"; \
		exit 1; \
	fi; \
	pod=$$(oc get pods -l app=mcp-server -n $$ns -o name | head -1 | cut -d/ -f2); \
	echo "✓ Found MCP server pod: $$pod"; \
	echo ""; \
	echo "2. Checking if diffusers-runtime service exists..."; \
	if ! oc get inferenceservice $$service > /dev/null 2>&1; then \
		echo "❌ Diffusers-runtime service '$$service' not found. Deploy with:"; \
		echo "   oc apply -f ../diffusers-runtime/templates/$$service.yaml"; \
		exit 1; \
	fi; \
	echo "✓ Found diffusers-runtime InferenceService: $$service"; \
	echo ""; \
	echo "3. Testing connectivity from MCP server to diffusers-runtime..."; \
	url="http://$$service.default.svc.cluster.local:8080"; \
	if oc exec -n $$ns $$pod -- curl -f --connect-timeout 10 --max-time 30 -s "$$url/v1/models" > /dev/null 2>&1; then \
		echo "✅ Connectivity test PASSED"; \
		echo "   MCP server can reach diffusers-runtime at $$url"; \
	else \
		echo "❌ Connectivity test FAILED"; \
		echo "   MCP server cannot reach diffusers-runtime at $$url"; \
		echo ""; \
		echo "🔧 Troubleshooting suggestions:"; \
		echo "   - Check if diffusers-runtime pod is ready: oc get pods -l serving.kserve.io/inferenceservice=$$service"; \
		echo "   - Check diffusers-runtime logs: oc logs -l serving.kserve.io/inferenceservice=$$service"; \
		echo "   - Check network policies: oc get networkpolicies -n $$ns"; \
		echo "   - Verify service endpoint: oc get endpoints $$service"; \
		exit 1; \
	fi

test-integration: ## Test end-to-end image generation through MCP server (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make test-integration ENV=dev|staging|production"; \
		exit 1; \
	fi
	@echo "🧪 Running integration test for $(ENV) environment..."
	@ns="mcp-server-$(ENV)"; \
	echo "Environment: $$ns"; \
	echo ""; \
	echo "1. Getting MCP server route..."; \
	if ! route=$$(oc get route mcp-server -n $$ns -o jsonpath='{.spec.host}' 2>/dev/null); then \
		echo "❌ MCP server route not found in $$ns. Deploy first with: make deploy-$(ENV)"; \
		exit 1; \
	fi; \
	if [ "$(ENV)" = "dev" ]; then \
		url="http://$$route"; \
	else \
		url="https://$$route"; \
	fi; \
	echo "✓ MCP server URL: $$url"; \
	echo ""; \
	echo "2. Testing health endpoint..."; \
	if curl -f --connect-timeout 10 --max-time 30 -s "$$url/health" > /dev/null; then \
		echo "✓ Health check passed"; \
	else \
		echo "❌ Health check failed - MCP server may not be ready"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "3. Testing image generation endpoint..."; \
	response=$$(curl -s -X POST "$$url/images/generate" \
		-H "Content-Type: application/json" \
		-d '{"prompt": "integration test image", "num_inference_steps": 1}' \
		-w "\nHTTP_CODE:%{http_code}"); \
	http_code=$$(echo "$$response" | grep "HTTP_CODE:" | cut -d: -f2); \
	if [ "$$http_code" = "200" ]; then \
		echo "✅ Integration test PASSED"; \
		echo "   Successfully generated image through MCP server"; \
		echo "   Response: $$(echo "$$response" | grep -v "HTTP_CODE:")"; \
	else \
		echo "❌ Integration test FAILED (HTTP $$http_code)"; \
		echo "   Response: $$(echo "$$response" | grep -v "HTTP_CODE:")"; \
		echo ""; \
		echo "🔧 Check the logs with: make logs ENV=$(ENV)"; \
		exit 1; \
	fi

check-services: ## Check status of all deployed services (ENV=dev|staging|production)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV variable is required. Use: make check-services ENV=dev|staging|production"; \
		exit 1; \
	fi
	@echo "🔍 Checking service status for $(ENV) environment..."
	@ns="mcp-server-$(ENV)"; \
	if [ "$(ENV)" = "dev" ] || [ "$(ENV)" = "staging" ]; then \
		service="tiny-sd"; \
	else \
		service="redhat-dog"; \
	fi; \
	echo "Environment: $$ns"; \
	echo "Expected diffusers service: $$service"; \
	echo ""; \
	echo "=== MCP Server Status ==="; \
	if oc get deployment mcp-server -n $$ns > /dev/null 2>&1; then \
		echo "Deployment:"; \
		oc get deployment mcp-server -n $$ns; \
		echo "Pods:"; \
		oc get pods -l app=mcp-server -n $$ns; \
		echo "Services:"; \
		oc get svc -l app=mcp-server -n $$ns; \
		echo "Routes:"; \
		oc get routes -l app=mcp-server -n $$ns; \
	else \
		echo "❌ MCP server not deployed in $$ns"; \
	fi; \
	echo ""; \
	echo "=== Diffusers-Runtime Status ==="; \
	if oc get inferenceservice $$service > /dev/null 2>&1; then \
		echo "InferenceService:"; \
		oc get inferenceservice $$service; \
		echo "Pods:"; \
		oc get pods -l serving.kserve.io/inferenceservice=$$service; \
		echo "Services:"; \
		oc get svc -l serving.kserve.io/inferenceservice=$$service; \
	else \
		echo "❌ Diffusers-runtime service '$$service' not found"; \
		echo "Deploy with: oc apply -f ../diffusers-runtime/templates/$$service.yaml"; \
	fi
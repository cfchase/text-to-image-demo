# Text-to-Image Demo - Top-Level Makefile
# Orchestrates deployment of all components

.PHONY: help create-namespace delete-namespace deploy-all undeploy-all deploy-llm deploy-diffusers deploy-mcp deploy-chatbot undeploy-llm undeploy-diffusers undeploy-mcp undeploy-chatbot status clean

# Project namespace for all components
NAMESPACE ?= text-to-image-demo

help: ## Show this help message
	@echo "Text-to-Image Demo - Component Deployment"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Main targets:"
	@echo "  make deploy-all    - Create namespace and deploy all components"
	@echo "  make undeploy-all  - Remove all components and namespace"
	@echo "  make status        - Show deployment status"
	@echo ""
	@echo "Namespace management:"
	@echo "  make create-namespace  - Create the project namespace"
	@echo "  make delete-namespace  - Delete the project namespace"
	@echo ""
	@echo "Individual components:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "deploy-|undeploy-" | grep -v "all"
	@echo ""
	@echo "Target namespace: $(NAMESPACE)"
	@echo "Override with: NAMESPACE=my-namespace make deploy-all"

# Namespace management
create-namespace: ## Create the project namespace
	@echo "📁 Creating Data Science Project namespace $(NAMESPACE)..."
	@oc new-project $(NAMESPACE) --display-name="Text to Image Demo" 2>/dev/null || oc project $(NAMESPACE) 2>/dev/null || true
	@echo "🏷️  Adding Data Science Project labels..."
	@oc label namespace $(NAMESPACE) opendatahub.io/dashboard=true --overwrite 2>/dev/null || true
	@oc annotate namespace $(NAMESPACE) openshift.io/display-name="Text to Image Demo" --overwrite 2>/dev/null || true
	@echo "✅ Using namespace: $(NAMESPACE)"

delete-namespace: ## Delete the project namespace
	@echo "🗑️  Deleting namespace $(NAMESPACE)..."
	@echo "⚠️  This will remove ALL resources in the namespace!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "Cancelled"; exit 1)
	@oc delete project $(NAMESPACE) --ignore-not-found=true
	@echo "✅ Namespace deleted"

# Main deployment targets
deploy-all: create-namespace deploy-llm deploy-diffusers deploy-mcp deploy-chatbot ## Create namespace and deploy all components
	@echo ""
	@echo "✅ All components deployed successfully in namespace $(NAMESPACE)!"
	@echo ""
	@$(MAKE) status

undeploy-all: undeploy-chatbot undeploy-mcp undeploy-diffusers undeploy-llm ## Remove all components
	@echo ""
	@echo "✅ All components removed successfully!"
	@echo ""
	@echo "💡 To delete the namespace, run: make delete-namespace"

# Individual component deployments
deploy-llm:  ## Deploy Phi-4 LLM (vLLM runtime)
	@cd llm-deployment && $(MAKE) deploy NAMESPACE=$(NAMESPACE)

deploy-diffusers: ## Deploy Stable Diffusion (redhat-dog model)
	@cd diffusers-runtime && $(MAKE) deploy TEMPLATE=redhat-dog-hf NAMESPACE=$(NAMESPACE)

deploy-mcp:  ## Deploy MCP server for image generation
	@oc project $(NAMESPACE) 2>/dev/null || true
	@cd mcp-server && $(MAKE) deploy DIFFUSERS_RUNTIME_URL=http://redhat-dog-predictor:8080 MCP_SERVER_NAME=image-generation-mcp

deploy-chatbot:  ## Deploy chatbot with MCP integration
	@echo "📝 Creating MCP configuration for chatbot..."
	@mkdir -p chatbot/k8s/overlays/deploy
	@echo '{"mcpServers": {"image-generation": {"transport": "http", "url": "http://image-generation-mcp:8080/mcp"}}}' > chatbot/k8s/overlays/deploy/mcp-config.json
	@if [ ! -f chatbot/k8s/overlays/deploy/.env ]; then \
		echo "⚠️  Creating default .env file for chatbot..."; \
		echo "API_KEY=EMPTY" > chatbot/k8s/overlays/deploy/.env; \
		echo "MODEL=llm-deployment" >> chatbot/k8s/overlays/deploy/.env; \
		echo "API_BASE_URL=http://llm-deployment-predictor.$(NAMESPACE).svc.cluster.local:8080/v1" >> chatbot/k8s/overlays/deploy/.env; \
		echo "✅ Configured to use local Phi-4 model"; \
	fi
	@cd chatbot && $(MAKE) deploy OVERLAY=deploy NAMESPACE=$(NAMESPACE)

# Individual component removals
undeploy-llm: ## Remove Phi-4 LLM deployment
	@cd llm-deployment && $(MAKE) undeploy NAMESPACE=$(NAMESPACE)

undeploy-diffusers: ## Remove Stable Diffusion deployment
	@cd diffusers-runtime && $(MAKE) undeploy TEMPLATE=redhat-dog-hf NAMESPACE=$(NAMESPACE)

undeploy-mcp: ## Remove MCP server deployment
	@oc project $(NAMESPACE) 2>/dev/null || true
	@cd mcp-server && $(MAKE) undeploy MCP_SERVER_NAME=image-generation-mcp

undeploy-chatbot: ## Remove chatbot deployment
	@cd chatbot && $(MAKE) undeploy OVERLAY=deploy NAMESPACE=$(NAMESPACE)

# Status and monitoring
status: ## Show deployment status of all components
	@echo "📊 Deployment Status in namespace: $(NAMESPACE)"
	@echo "================================================"
	@oc project $(NAMESPACE) 2>/dev/null || (echo "❌ Namespace $(NAMESPACE) not found"; exit 0)
	@echo ""
	@echo "LLM Deployment (Phi-4):"
	@oc get inferenceservice llm-deployment -n $(NAMESPACE) -o wide 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "Diffusers Runtime (Stable Diffusion):"
	@oc get inferenceservice redhat-dog -n $(NAMESPACE) -o wide 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "MCP Server:"
	@oc get deployment image-generation-mcp -n $(NAMESPACE) -o wide 2>/dev/null || echo "  Not deployed"
	@oc get route image-generation-mcp -n $(NAMESPACE) 2>/dev/null | grep -v NAME | awk '{if(NF>0) print "  URL: https://" $$2}' || true
	@echo ""
	@echo "Chatbot:"
	@oc get deployment backend frontend -n $(NAMESPACE) -o wide 2>/dev/null || echo "  Not deployed"
	@oc get route chatbot -n $(NAMESPACE) 2>/dev/null | grep -v NAME | awk '{if(NF>0) print "  URL: https://" $$2}' || true
	@echo ""
	@echo "Pods:"
	@oc get pods -n $(NAMESPACE) | grep -E "llm-deployment|redhat-dog|image-generation-mcp|backend|frontend" || echo "  No pods found"

logs-llm: ## Show LLM logs
	@oc logs -l app=llm-deployment -n $(NAMESPACE) --tail=50 -f

logs-diffusers: ## Show Diffusers runtime logs
	@oc logs -l app=redhat-dog -n $(NAMESPACE) --tail=50 -f

logs-mcp: ## Show MCP server logs
	@oc logs -l app=image-generation-mcp -n $(NAMESPACE) --tail=50 -f

logs-chatbot: ## Show chatbot backend logs
	@oc logs -l app=backend -n $(NAMESPACE) --tail=50 -f

test-components: ## Test deployed components
	@echo "🧪 Testing deployed components in namespace $(NAMESPACE)..."
	@echo ""
	@echo "Testing LLM..."
	@kubectl port-forward service/llm-deployment-predictor 8081:80 -n $(NAMESPACE) &
	@sleep 2
	@curl -X POST http://localhost:8081/v1/completions \
		-H "Content-Type: application/json" \
		-d '{"model": "llm-deployment", "prompt": "Hello", "max_tokens": 10}' 2>/dev/null || echo "LLM test failed"
	@pkill -f "port-forward.*8081" || true
	@echo ""
	@echo "Testing Diffusers..."
	@kubectl port-forward service/redhat-dog-predictor 8082:80 -n $(NAMESPACE) &
	@sleep 2
	@curl -X POST http://localhost:8082/v1/models/model:predict \
		-H "Content-Type: application/json" \
		-d '{"instances": [{"prompt": "test"}]}' 2>/dev/null || echo "Diffusers test failed"
	@pkill -f "port-forward.*8082" || true

clean: ## Clean temporary files
	@rm -f chatbot/k8s/overlays/deploy/mcp-config.json 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

# Deployment verification
verify: ## Verify all components are ready
	@echo "🔍 Verifying deployments in namespace $(NAMESPACE)..."
	@echo ""
	@echo -n "Namespace exists: "
	@oc get project $(NAMESPACE) >/dev/null 2>&1 && echo "✅" || echo "❌"
	@echo -n "LLM: "
	@oc get inferenceservice llm-deployment -n $(NAMESPACE) -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Not found"
	@echo ""
	@echo -n "Diffusers: "
	@oc get inferenceservice redhat-dog -n $(NAMESPACE) -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Not found"
	@echo ""
	@echo -n "MCP Server: "
	@oc get deployment image-generation-mcp -n $(NAMESPACE) -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Not found"
	@echo ""
	@echo -n "Chatbot Backend: "
	@oc get deployment backend -n $(NAMESPACE) -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Not found"
	@echo ""
	@echo -n "Chatbot Frontend: "
	@oc get deployment frontend -n $(NAMESPACE) -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Not found"
	@echo ""
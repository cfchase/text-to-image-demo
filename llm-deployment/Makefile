# LLM Deployment Makefile - Phi-4 Model Deployment

.PHONY: help deploy undeploy status logs test clean verify port-forward

# Default model configuration
MODEL ?= llama-3
NAMESPACE ?= $(shell oc project -q 2>/dev/null || echo "default")

help: ## Show this help message
	@echo "LLM Deployment - Phi-4 Model"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment Variables:"
	@echo "  MODEL      Model to deploy (default: phi-4-fp8)"
	@echo "  NAMESPACE  Target namespace (current: $(NAMESPACE))"
	@echo ""
	@echo "Available models:"
	@echo "  - phi-4-fp8 (default, single GPU)"
	@echo "  - llama-4-scout-17b-16e-w4a16 (multi-GPU)"
	@echo "  - llama-4-scout-17b-16e-w4a16-single-gpu"

deploy: ## Deploy Phi-4 model to cluster
	@echo "🚀 Deploying $(MODEL) to namespace $(NAMESPACE)..."
	@if [ ! -f "templates/$(MODEL).yaml" ]; then \
		echo "❌ Error: templates/$(MODEL).yaml not found"; \
		echo "Available models:"; \
		ls templates/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml//' | sed 's/^/  - /'; \
		exit 1; \
	fi
	@oc apply -f templates/$(MODEL).yaml
	@echo ""
	@echo "⏳ Waiting for ServingRuntime to be created..."
	@sleep 5
	@echo "⏳ Waiting for InferenceService to be ready (this may take several minutes)..."
	@oc wait --for=condition=Ready inferenceservice/llm-deployment --timeout=600s 2>/dev/null || \
		(echo "⚠️  Timeout waiting for deployment. Check status with 'make status'"; exit 0)
	@echo ""
	@echo "✅ Deployment complete!"
	@$(MAKE) status

undeploy: ## Remove LLM deployment from cluster
	@echo "🗑️  Removing $(MODEL) deployment..."
	@if [ -f "templates/$(MODEL).yaml" ]; then \
		oc delete -f templates/$(MODEL).yaml --ignore-not-found=true; \
	else \
		echo "⚠️  templates/$(MODEL).yaml not found, attempting to remove llm-deployment resources..."; \
		oc delete inferenceservice/llm-deployment --ignore-not-found=true; \
		oc delete servingruntime/llm-deployment --ignore-not-found=true; \
	fi
	@echo "✅ Deployment removed"

status: ## Show deployment status
	@echo "📊 LLM Deployment Status"
	@echo "========================"
	@echo ""
	@echo "ServingRuntime:"
	@oc get servingruntime llm-deployment 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "InferenceService:"
	@oc get inferenceservice llm-deployment -o wide 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Pods:"
	@oc get pods -l serving.kserve.io/inferenceservice=llm-deployment 2>/dev/null || echo "  No pods found"
	@echo ""
	@echo "Endpoints:"
	@oc get inferenceservice llm-deployment -o jsonpath='{.status.url}' 2>/dev/null || echo "  Not available"
	@echo ""

logs: ## Show deployment logs
	@echo "📝 Fetching logs for llm-deployment..."
	@POD=$$(oc get pods -l serving.kserve.io/inferenceservice=llm-deployment -o name 2>/dev/null | head -1); \
	if [ -n "$$POD" ]; then \
		oc logs $$POD -c kserve-container --tail=100 -f; \
	else \
		echo "❌ No pods found for llm-deployment"; \
	fi

verify: ## Verify deployment is ready and healthy
	@echo "🔍 Verifying LLM deployment..."
	@echo ""
	@echo -n "ServingRuntime exists: "
	@oc get servingruntime llm-deployment -o name >/dev/null 2>&1 && echo "✅" || echo "❌"
	@echo -n "InferenceService exists: "
	@oc get inferenceservice llm-deployment -o name >/dev/null 2>&1 && echo "✅" || echo "❌"
	@echo -n "InferenceService ready: "
	@STATUS=$$(oc get inferenceservice llm-deployment -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null); \
	if [ "$$STATUS" = "True" ]; then echo "✅"; else echo "❌ ($$STATUS)"; fi
	@echo -n "Pod running: "
	@POD_STATUS=$$(oc get pods -l serving.kserve.io/inferenceservice=llm-deployment -o jsonpath='{.items[0].status.phase}' 2>/dev/null); \
	if [ "$$POD_STATUS" = "Running" ]; then echo "✅"; else echo "❌ ($$POD_STATUS)"; fi
	@echo ""
	@echo "Model endpoint:"
	@oc get inferenceservice llm-deployment -o jsonpath='{.status.url}' 2>/dev/null || echo "  Not available"

port-forward: ## Create port-forward to access model locally
	@echo "🔌 Setting up port-forward to llm-deployment..."
	@echo "The model will be available at: http://localhost:8080"
	@echo "Press Ctrl+C to stop port forwarding"
	@echo ""
	@SERVICE=$$(oc get service -l serving.kserve.io/inferenceservice=llm-deployment -o name 2>/dev/null | grep predictor | head -1); \
	if [ -n "$$SERVICE" ]; then \
		oc port-forward $$SERVICE 8080:80; \
	else \
		echo "❌ No predictor service found. Is the deployment ready?"; \
		echo "Run 'make status' to check deployment status"; \
	fi

test: ## Test the deployed model
	@echo "🧪 Testing LLM deployment..."
	@echo ""
	@echo "Starting port-forward in background..."
	@SERVICE=$$(oc get service -l serving.kserve.io/inferenceservice=llm-deployment -o name 2>/dev/null | grep predictor | head -1); \
	if [ -z "$$SERVICE" ]; then \
		echo "❌ No predictor service found. Deploy first with 'make deploy'"; \
		exit 1; \
	fi; \
	oc port-forward $$SERVICE 8080:80 > /dev/null 2>&1 & \
	PF_PID=$$!; \
	sleep 3; \
	echo "Testing OpenAI-compatible endpoint..."; \
	curl -s -X POST http://localhost:8080/v1/completions \
		-H "Content-Type: application/json" \
		-d '{ \
			"model": "llm-deployment", \
			"prompt": "Hello, how are you?", \
			"max_tokens": 50, \
			"temperature": 0.7 \
		}' | python -m json.tool 2>/dev/null || echo "❌ Test failed"; \
	kill $$PF_PID 2>/dev/null || true; \
	echo ""; \
	echo "✅ Test complete"

test-chat: ## Test chat completion endpoint
	@echo "🧪 Testing chat completion endpoint..."
	@SERVICE=$$(oc get service -l serving.kserve.io/inferenceservice=llm-deployment -o name 2>/dev/null | grep predictor | head -1); \
	if [ -z "$$SERVICE" ]; then \
		echo "❌ No predictor service found. Deploy first with 'make deploy'"; \
		exit 1; \
	fi; \
	oc port-forward $$SERVICE 8080:80 > /dev/null 2>&1 & \
	PF_PID=$$!; \
	sleep 3; \
	curl -s -X POST http://localhost:8080/v1/chat/completions \
		-H "Content-Type: application/json" \
		-d '{ \
			"model": "llm-deployment", \
			"messages": [ \
				{"role": "system", "content": "You are a helpful assistant."}, \
				{"role": "user", "content": "What is the capital of France?"} \
			], \
			"max_tokens": 50 \
		}' | python -m json.tool 2>/dev/null || echo "❌ Test failed"; \
	kill $$PF_PID 2>/dev/null || true

describe: ## Describe the deployment details
	@echo "📋 Deployment Details"
	@echo "===================="
	@echo ""
	@echo "ServingRuntime Configuration:"
	@oc describe servingruntime llm-deployment 2>/dev/null || echo "Not found"
	@echo ""
	@echo "InferenceService Configuration:"
	@oc describe inferenceservice llm-deployment 2>/dev/null || echo "Not found"

events: ## Show deployment events
	@echo "📅 Recent Events for llm-deployment"
	@echo "===================================="
	@oc get events --field-selector involvedObject.name=llm-deployment --sort-by='.lastTimestamp' 2>/dev/null || \
	oc get events | grep llm-deployment | tail -20

clean: ## Clean up any temporary files
	@echo "🧹 Cleaning temporary files..."
	@rm -f port-forward.log 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Advanced deployment options
deploy-llama: ## Deploy Llama-4 Scout model (requires multi-GPU)
	@$(MAKE) deploy MODEL=llama-4-scout-17b-16e-w4a16

deploy-llama-single: ## Deploy Llama-4 Scout single-GPU variant
	@$(MAKE) deploy MODEL=llama-4-scout-17b-16e-w4a16-single-gpu

# Monitoring
watch-status: ## Watch deployment status (refreshes every 5 seconds)
	@watch -n 5 "oc get inferenceservice llm-deployment; echo ''; oc get pods -l serving.kserve.io/inferenceservice=llm-deployment"

resource-usage: ## Show resource usage for LLM pods
	@echo "📊 Resource Usage"
	@echo "================"
	@oc top pod -l serving.kserve.io/inferenceservice=llm-deployment 2>/dev/null || \
		echo "Metrics not available. Ensure metrics-server is installed."
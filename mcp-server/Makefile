.PHONY: help install test test-diffusers run clean

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
	@echo "  make run    # Starts unified server with MCP on /mcp and images on /images"

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
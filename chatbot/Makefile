# Include environment files if they exist
-include .env
-include .env.local

.PHONY: help install run server-status clean

help: ## Show this help message
	@echo "Chatbot - FastMCP client for interacting with MCP servers"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Prerequisites:"
	@echo "  - MCP server running on http://127.0.0.1:8000 (cd ../mcp-server && make run)"
	@echo "  - Diffusers runtime running on http://0.0.0.0:8080 (cd ../diffusers-runtime && make dev)"
	@echo "  - ANTHROPIC_API_KEY in .env file"

install: ## Install dependencies using uv
	uv pip install -e .

run: ## Run chatbot with config.json
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Create it with ANTHROPIC_API_KEY=your_key"; \
		exit 1; \
	fi
	python multi_client.py --config config.json

server-status: ## Check if required servers are running
	@echo "Checking MCP server at http://127.0.0.1:8000..."
	@curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 && echo "✅ MCP server is running" || echo "❌ MCP server is not running (run: cd ../mcp-server && make run)"
	@echo ""
	@echo "Checking diffusers-runtime at http://0.0.0.0:8080..."
	@curl -s http://0.0.0.0:8080/v2/health/ready >/dev/null 2>&1 && echo "✅ Diffusers runtime is running" || echo "❌ Diffusers runtime is not running (run: cd ../diffusers-runtime && make dev)"

clean: ## Clean generated files and cache
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
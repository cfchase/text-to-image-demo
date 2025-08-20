# React FastAPI Template Makefile

# Load environment variables from .env file if it exists
-include .env
export

# Load environment-specific .env files if specified
ifdef ENV
    -include .env.$(ENV).local
    export
endif

# Container Registry Operations
REGISTRY ?= quay.io/cfchase
TAG ?= latest

# Deployment Configuration
NAMESPACE ?= chatbot
OVERLAY ?= deploy


.PHONY: help setup dev build build-prod test clean push push-prod deploy deploy-dev deploy-prod undeploy undeploy-dev undeploy-prod kustomize kustomize-dev kustomize-prod env-setup env-check env-setup-k8s health-backend health-frontend fresh-start quick-start

# Default target
help: ## Show this help message
	@echo "React FastAPI Template - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Install all dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing backend dependencies..."
	cd backend && uv sync --extra dev
	@echo "Setup complete!"

setup-frontend: ## Install frontend dependencies only
	cd frontend && npm install

setup-backend: ## Install backend dependencies only
	cd backend && uv sync --extra dev

# Development
dev: ## Run both frontend and backend in development mode
	@echo "Starting development servers..."
	npx concurrently "make dev-backend" "make dev-frontend"

dev-frontend: ## Run frontend development server
	cd frontend && npm run dev -- --port $${FRONTEND_PORT:-8080}

dev-backend: ## Run backend development server
	cd backend && uv run python -m uvicorn main:app --reload --host 0.0.0.0 --port $${BACKEND_PORT:-8000}

# Building
build-frontend: ## Build frontend for production
	cd frontend && npm run build

build: build-frontend ## Build frontend and container images
	@echo "Building container images for $(REGISTRY) with tag $(TAG)..."
	./scripts/build-images.sh $(TAG) $(REGISTRY)


# Testing
test: ## Run all tests (frontend and backend)
	@echo "Running frontend tests..."
	cd frontend && npm run test
	@echo "Running backend tests..."
	cd backend && uv run pytest

test-frontend: ## Run frontend tests
	cd frontend && npm run test

test-backend: ## Run backend tests
	cd backend && uv run pytest

test-backend-verbose: ## Run backend tests with verbose output
	cd backend && uv run pytest -v

lint: ## Run linting on frontend
	cd frontend && npm run lint

push: ## Push container images to registry
	@echo "Pushing images to $(REGISTRY) with tag $(TAG)..."
	./scripts/push-images.sh $(TAG) $(REGISTRY)


# OpenShift/Kubernetes Deployment
kustomize: ## Preview deployment manifests (use OVERLAY=<name> to specify overlay)
	./scripts/kustomize.sh $(OVERLAY)


deploy: ## Deploy to Kubernetes/OpenShift (use NAMESPACE=<name> and OVERLAY=<name> to configure)
	@echo "Deploying to namespace $(NAMESPACE) using overlay $(OVERLAY)..."
	./scripts/deploy.sh $(OVERLAY) $(NAMESPACE)

undeploy: ## Remove deployment (use NAMESPACE=<name> and OVERLAY=<name> to configure)
	@echo "Removing deployment from namespace $(NAMESPACE) using overlay $(OVERLAY)..."
	./scripts/undeploy.sh $(OVERLAY) $(NAMESPACE)

# Environment Setup
env-setup: ## Copy environment example files
	@echo "Setting up environment files..."
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; echo "Created backend/.env"; fi
	@if [ ! -f frontend/.env ]; then cp frontend/.env.example frontend/.env; echo "Created frontend/.env"; fi
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env; echo "Created root .env"; fi

env-check: ## Display loaded environment variables (for debugging)
	@echo "Environment variables loaded:"
	@echo "REGISTRY: $(REGISTRY)"
	@echo "TAG: $(TAG)"
	@echo "NAMESPACE: $(NAMESPACE)"
	@echo "OVERLAY: $(OVERLAY)"
	@echo "FRONTEND_PORT: $${FRONTEND_PORT:-not set}"
	@echo "BACKEND_PORT: $${BACKEND_PORT:-not set}"
	@if [ -n "$(ENV)" ]; then echo "ENV: $(ENV) (loading .env.$(ENV).local)"; fi

env-setup-k8s: ## Copy Kubernetes example files for configuration
	@echo "Setting up Kubernetes configuration files..."
	@for overlay in $$(ls -d k8s/overlays/*/ 2>/dev/null | xargs -n1 basename); do \
		if [ -f k8s/overlays/$$overlay/.env.example ] && [ ! -f k8s/overlays/$$overlay/.env ]; then \
			cp k8s/overlays/$$overlay/.env.example k8s/overlays/$$overlay/.env; \
			echo "Created k8s/overlays/$$overlay/.env - EDIT THIS FILE with your API keys"; \
		fi; \
		if [ -f k8s/overlays/$$overlay/mcp-config.example.json ] && [ ! -f k8s/overlays/$$overlay/mcp-config.json ]; then \
			cp k8s/overlays/$$overlay/mcp-config.example.json k8s/overlays/$$overlay/mcp-config.json; \
			echo "Created k8s/overlays/$$overlay/mcp-config.json"; \
		fi; \
	done
	@echo "⚠️  IMPORTANT: Edit the .env files with your actual API keys before deploying!"

# Health Checks
health-backend: ## Check backend health
	@echo "Checking backend health..."
	@curl -f http://localhost:8000/api/health || echo "Backend not responding"

health-frontend: ## Check if frontend is running
	@echo "Checking frontend..."
	@curl -f http://localhost:8080 || echo "Frontend not responding"

# Cleanup
clean: ## Clean build artifacts and dependencies
	@echo "Cleaning build artifacts..."
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache

clean-all: clean ## Clean everything

# Development Workflow
fresh-start: clean setup env-setup ## Clean setup for new development
	@echo "Fresh development environment ready!"

quick-start: setup env-setup dev ## Quick start for development


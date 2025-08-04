# Makefile for MCP Image Generation Server

# Variables
PYTHON := python3
VENV := .venv
PYTHON_VENV := $(VENV)/bin/python
PIP_VENV := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
BLACK := $(VENV)/bin/black
ISORT := $(VENV)/bin/isort
FLAKE8 := $(VENV)/bin/flake8
MYPY := $(VENV)/bin/mypy

# Docker/Podman settings
CONTAINER_RUNTIME ?= podman
IMAGE_NAME := mcp-image-generation-server
IMAGE_TAG ?= latest
REGISTRY ?= quay.io/cfchase

# Server settings
HOST ?= 0.0.0.0
PORT ?= 8000
WORKERS ?= 1
LOG_LEVEL ?= INFO

# Storage settings
STORAGE_BACKEND ?= file
STORAGE_PATH ?= /tmp/mcp-images

# KServe settings
KSERVE_ENDPOINT ?= http://localhost:8080
KSERVE_MODEL_NAME ?= stable-diffusion

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)MCP Image Generation Server$(NC)"
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Environment variables:$(NC)"
	@echo "  $(YELLOW)CONTAINER_RUNTIME$(NC)    Container runtime (default: podman)"
	@echo "  $(YELLOW)REGISTRY$(NC)            Container registry (default: quay.io/cfchase)"
	@echo "  $(YELLOW)IMAGE_TAG$(NC)           Image tag (default: latest)"
	@echo "  $(YELLOW)STORAGE_BACKEND$(NC)     Storage backend: file or s3 (default: file)"
	@echo "  $(YELLOW)KSERVE_ENDPOINT$(NC)     KServe endpoint URL (default: http://localhost:8080)"

.PHONY: install
install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP_VENV) install -e ".[dev]"
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

.PHONY: install-prod
install-prod: ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP_VENV) install -e .
	@echo "$(GREEN)Production dependencies installed successfully$(NC)"

.PHONY: test
test: ## Run unit tests
	@echo "$(BLUE)Running unit tests...$(NC)"
	PYTHONPATH=src $(PYTEST) tests/unit -v

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	PYTHONPATH=src $(PYTEST) tests/integration -v

.PHONY: test-all
test-all: ## Run all tests with coverage
	@echo "$(BLUE)Running all tests with coverage...$(NC)"
	PYTHONPATH=src $(PYTEST) tests -v --cov=src --cov-report=html --cov-report=term

.PHONY: test-fast
test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running tests without coverage...$(NC)"
	PYTHONPATH=src $(PYTEST) tests/unit -v --no-cov

.PHONY: lint
lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	@echo "$(YELLOW)Running isort...$(NC)"
	$(ISORT) --check-only src tests
	@echo "$(YELLOW)Running black...$(NC)"
	$(BLACK) --check src tests
	@echo "$(YELLOW)Running flake8...$(NC)"
	$(FLAKE8) src tests
	@echo "$(GREEN)All linting checks passed$(NC)"

.PHONY: format
format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(ISORT) src tests
	$(BLACK) src tests
	@echo "$(GREEN)Code formatted successfully$(NC)"

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	$(MYPY) src
	@echo "$(GREEN)Type checks passed$(NC)"

.PHONY: clean
clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete$(NC)"

.PHONY: run
run: ## Run the server locally (development mode)
	@echo "$(BLUE)Starting MCP server in development mode...$(NC)"
	@echo "$(YELLOW)Host: $(HOST):$(PORT)$(NC)"
	@echo "$(YELLOW)Storage: $(STORAGE_BACKEND) ($(STORAGE_PATH))$(NC)"
	@echo "$(YELLOW)KServe: $(KSERVE_ENDPOINT)$(NC)"
	PYTHONPATH=src \
		HOST=$(HOST) \
		PORT=$(PORT) \
		LOG_LEVEL=$(LOG_LEVEL) \
		STORAGE_BACKEND=$(STORAGE_BACKEND) \
		STORAGE_PATH=$(STORAGE_PATH) \
		KSERVE_ENDPOINT=$(KSERVE_ENDPOINT) \
		KSERVE_MODEL_NAME=$(KSERVE_MODEL_NAME) \
		$(PYTHON_VENV) -m main dev

.PHONY: run-prod
run-prod: ## Run the server in production mode
	@echo "$(BLUE)Starting MCP server in production mode...$(NC)"
	PYTHONPATH=src \
		HOST=$(HOST) \
		PORT=$(PORT) \
		WORKERS=$(WORKERS) \
		LOG_LEVEL=$(LOG_LEVEL) \
		STORAGE_BACKEND=$(STORAGE_BACKEND) \
		STORAGE_PATH=$(STORAGE_PATH) \
		KSERVE_ENDPOINT=$(KSERVE_ENDPOINT) \
		KSERVE_MODEL_NAME=$(KSERVE_MODEL_NAME) \
		$(PYTHON_VENV) -m main prod

.PHONY: health
health: ## Check server health
	@echo "$(BLUE)Checking server health...$(NC)"
	PYTHONPATH=src $(PYTHON_VENV) -m main health

.PHONY: cleanup-images
cleanup-images: ## Manually trigger image cleanup
	@echo "$(BLUE)Triggering image cleanup...$(NC)"
	PYTHONPATH=src $(PYTHON_VENV) -m main cleanup

# Docker targets
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	$(CONTAINER_RUNTIME) build -f deployment/docker/Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "$(GREEN)Image built: $(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

.PHONY: docker-build-dev
docker-build-dev: ## Build development Docker image
	@echo "$(BLUE)Building development Docker image...$(NC)"
	$(CONTAINER_RUNTIME) build -f deployment/docker/Dockerfile --target development -t $(IMAGE_NAME):dev .
	@echo "$(GREEN)Development image built: $(IMAGE_NAME):dev$(NC)"

.PHONY: docker-run
docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	$(CONTAINER_RUNTIME) run --rm -it \
		-p $(PORT):$(PORT) \
		-e LOG_LEVEL=$(LOG_LEVEL) \
		-e STORAGE_BACKEND=$(STORAGE_BACKEND) \
		-e KSERVE_ENDPOINT=$(KSERVE_ENDPOINT) \
		-e KSERVE_MODEL_NAME=$(KSERVE_MODEL_NAME) \
		$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: docker-run-dev
docker-run-dev: ## Run development Docker container with volume mount
	@echo "$(BLUE)Running development Docker container...$(NC)"
	$(CONTAINER_RUNTIME) run --rm -it \
		-p $(PORT):$(PORT) \
		-v $(PWD)/src:/app/src:Z \
		-e LOG_LEVEL=DEBUG \
		-e STORAGE_BACKEND=$(STORAGE_BACKEND) \
		-e KSERVE_ENDPOINT=$(KSERVE_ENDPOINT) \
		-e KSERVE_MODEL_NAME=$(KSERVE_MODEL_NAME) \
		$(IMAGE_NAME):dev

.PHONY: docker-push
docker-push: ## Push Docker image to registry
	@echo "$(BLUE)Pushing Docker image to registry...$(NC)"
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "$(GREEN)Image pushed: $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

.PHONY: docker-shell
docker-shell: ## Open shell in Docker container
	@echo "$(BLUE)Opening shell in Docker container...$(NC)"
	$(CONTAINER_RUNTIME) run --rm -it \
		-v $(PWD):/app:Z \
		--entrypoint /bin/bash \
		$(IMAGE_NAME):$(IMAGE_TAG)

# Kubernetes targets
.PHONY: k8s-deploy
k8s-deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	kubectl apply -f deployment/k8s/configmap.yaml
	kubectl apply -f deployment/k8s/secret.yaml
	kubectl apply -f deployment/k8s/deployment.yaml
	kubectl apply -f deployment/k8s/service.yaml
	@echo "$(GREEN)Deployment complete$(NC)"

.PHONY: k8s-delete
k8s-delete: ## Delete Kubernetes deployment
	@echo "$(BLUE)Deleting Kubernetes deployment...$(NC)"
	kubectl delete -f deployment/k8s/service.yaml --ignore-not-found
	kubectl delete -f deployment/k8s/deployment.yaml --ignore-not-found
	kubectl delete -f deployment/k8s/secret.yaml --ignore-not-found
	kubectl delete -f deployment/k8s/configmap.yaml --ignore-not-found
	@echo "$(GREEN)Deployment deleted$(NC)"

.PHONY: k8s-logs
k8s-logs: ## View Kubernetes pod logs
	@echo "$(BLUE)Viewing pod logs...$(NC)"
	kubectl logs -l app=mcp-image-server -f

.PHONY: k8s-port-forward
k8s-port-forward: ## Port forward to Kubernetes service
	@echo "$(BLUE)Port forwarding to service...$(NC)"
	kubectl port-forward svc/mcp-image-server $(PORT):8000

.PHONY: k8s-status
k8s-status: ## Check Kubernetes deployment status
	@echo "$(BLUE)Checking deployment status...$(NC)"
	kubectl get deployments -l app=mcp-image-server
	kubectl get pods -l app=mcp-image-server
	kubectl get svc mcp-image-server

.PHONY: k8s-restart
k8s-restart: ## Restart Kubernetes deployment
	@echo "$(BLUE)Restarting deployment...$(NC)"
	kubectl rollout restart deployment/mcp-image-server
	kubectl rollout status deployment/mcp-image-server

# Development helpers
.PHONY: dev-setup
dev-setup: install ## Complete development environment setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@echo "$(GREEN)Development environment ready$(NC)"

.PHONY: dev-test
dev-test: format lint type-check test ## Run all development checks
	@echo "$(GREEN)All development checks passed$(NC)"

.PHONY: watch-tests
watch-tests: ## Watch for changes and run tests
	@echo "$(BLUE)Watching for changes...$(NC)"
	PYTHONPATH=src $(PYTEST) tests/unit -v --no-cov --tb=short -f

.PHONY: coverage-report
coverage-report: ## Generate and open coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	PYTHONPATH=src $(PYTEST) tests --cov=src --cov-report=html --quiet
	@echo "$(GREEN)Opening coverage report...$(NC)"
	open htmlcov/index.html || xdg-open htmlcov/index.html 2>/dev/null || echo "Please open htmlcov/index.html manually"

# Documentation
.PHONY: docs
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

# Version management
.PHONY: version
version: ## Show current version
	@grep "version = " pyproject.toml | cut -d'"' -f2

.PHONY: bump-patch
bump-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@echo "$(BLUE)Bumping patch version...$(NC)"
	@current=$$(grep "version = " pyproject.toml | cut -d'"' -f2); \
	new=$$(echo $$current | awk -F. '{print $$1"."$$2"."$$3+1}'); \
	sed -i '' "s/version = \"$$current\"/version = \"$$new\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$current -> $$new$(NC)"

.PHONY: bump-minor
bump-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@echo "$(BLUE)Bumping minor version...$(NC)"
	@current=$$(grep "version = " pyproject.toml | cut -d'"' -f2); \
	new=$$(echo $$current | awk -F. '{print $$1"."$$2+1".0"}'); \
	sed -i '' "s/version = \"$$current\"/version = \"$$new\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$current -> $$new$(NC)"

.PHONY: bump-major
bump-major: ## Bump major version (0.1.0 -> 1.0.0)
	@echo "$(BLUE)Bumping major version...$(NC)"
	@current=$$(grep "version = " pyproject.toml | cut -d'"' -f2); \
	new=$$(echo $$current | awk -F. '{print $$1+1".0.0"}'); \
	sed -i '' "s/version = \"$$current\"/version = \"$$new\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$current -> $$new$(NC)"

# Default target
.DEFAULT_GOAL := help
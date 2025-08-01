# Multi-stage Dockerfile for MCP Image Generation Server
# Supports both development and production builds

# Build stage - Install dependencies and build the application
FROM python:3.11-slim-bullseye AS builder

# Set build arguments
ARG BUILD_TYPE=production
ARG PIP_INDEX_URL=""
ARG PIP_TRUSTED_HOST=""

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create build directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install build dependencies
RUN pip install --upgrade pip setuptools wheel

# Install dependencies based on build type
RUN if [ "$BUILD_TYPE" = "development" ]; then \
        pip install -e ".[dev]"; \
    else \
        pip install .; \
    fi

# Copy source code
COPY src/ src/

# Install the application
RUN pip install -e .

# Production stage - Minimal runtime image
FROM python:3.11-slim-bullseye AS production

# Set runtime arguments
ARG USER_ID=1001
ARG GROUP_ID=1001
ARG APP_USER=mcp-server

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -g ${GROUP_ID} ${APP_USER} && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ${APP_USER}

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/${APP_USER}/.local/bin:$PATH"

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY --chown=${USER_ID}:${GROUP_ID} src/ /app/src/
COPY --chown=${USER_ID}:${GROUP_ID} pyproject.toml /app/

# Set working directory
WORKDIR /app

# Create directories for storage and logs
RUN mkdir -p /app/storage /app/logs && \
    chown -R ${USER_ID}:${GROUP_ID} /app

# Switch to non-root user
USER ${USER_ID}

# Install the application as the user
RUN pip install --user -e .

# Set default environment variables
ENV SERVICE_NAME=mcp-image-server \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=4 \
    STORAGE_BACKEND=file \
    STORAGE_PATH=/app/storage \
    IMAGE_CLEANUP_INTERVAL=300 \
    IMAGE_TTL=3600 \
    MAX_IMAGE_SIZE=10485760

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Default command
CMD ["python", "-m", "mcp_server.main"]

# Development stage - Includes development tools and volumes
FROM production AS development

# Switch back to root to install dev dependencies
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    git \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy dev dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Switch back to app user
USER ${USER_ID}

# Set development environment variables
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

# Override command for development with auto-reload
CMD ["python", "-m", "mcp_server.main", "dev"]

# Testing stage - Optimized for running tests
FROM builder AS testing

# Install test dependencies
RUN pip install -e ".[dev]"

# Copy test files
COPY tests/ tests/

# Set test environment
ENV ENVIRONMENT=testing \
    LOG_LEVEL=DEBUG \
    STORAGE_BACKEND=file \
    STORAGE_PATH=/tmp/test-images

# Create test user
RUN useradd -m -s /bin/bash test-user
USER test-user

# Default command for testing
CMD ["pytest", "-v", "--cov=src", "--cov-report=term-missing"]

# Minimal runtime stage - Smallest possible image
FROM python:3.11-alpine AS minimal

ARG USER_ID=1001
ARG GROUP_ID=1001
ARG APP_USER=mcp-server

# Install minimal runtime dependencies
RUN apk add --no-cache \
    curl \
    ca-certificates

# Create non-root user
RUN addgroup -g ${GROUP_ID} ${APP_USER} && \
    adduser -u ${USER_ID} -G ${APP_USER} -D -s /bin/sh ${APP_USER}

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy only the necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY --chown=${USER_ID}:${GROUP_ID} src/ /app/src/
COPY --chown=${USER_ID}:${GROUP_ID} pyproject.toml /app/

WORKDIR /app

# Create storage directory
RUN mkdir -p /app/storage && \
    chown -R ${USER_ID}:${GROUP_ID} /app

USER ${USER_ID}

# Install the application
RUN pip install --user -e .

# Set minimal environment
ENV SERVICE_NAME=mcp-image-server \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=1 \
    STORAGE_BACKEND=file \
    STORAGE_PATH=/app/storage

# Health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=2 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

CMD ["python", "-m", "mcp_server.main"]
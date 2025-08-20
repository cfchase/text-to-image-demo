# Multi-stage build for optimal caching and size
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Create and set work directory
WORKDIR /app

# Copy dependency files for caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY . .

# Install the project
RUN uv sync --frozen --no-dev


# Production stage
FROM python:3.11-slim AS runtime

# Install system dependencies for runtime including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create global npm cache directory with proper permissions for OpenShift
RUN mkdir -p /.npm && \
    chgrp -R 0 /.npm && \
    chmod -R g=u /.npm

# Create app user for security
RUN groupadd -r app && useradd -r -g app app

# Set up application directory
WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application code
COPY --chown=app:app . .

# Set permissions for OpenShift compatibility
RUN chgrp -R 0 /app && \
    chmod -R g=u /app

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Use non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
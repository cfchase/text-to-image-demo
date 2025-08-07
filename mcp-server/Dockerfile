# Use Red Hat UBI9 Python 3.11 base image
FROM registry.access.redhat.com/ubi9/python-311:1-1753713955

# Set labels for better image management
LABEL name="mcp-server" \
      version="1.0" \
      description="MCP Server with FastMCP framework for OpenShift" \
      maintainer="cfchase"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Set working directory (UBI image uses /opt/app-root/src by default)
WORKDIR /opt/app-root/src

# Install uv for fast dependency management
RUN pip install --upgrade pip && \
    pip install uv

# Copy dependency files as root
USER 0
COPY --chown=1001:0 pyproject.toml uv.lock ./

# Switch back to default user
USER 1001

# Create UV cache directory with proper permissions for OpenShift
RUN mkdir -p /opt/app-root/src/.cache/uv && \
    chmod -R g+rwX /opt/app-root/src/.cache

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=1001:0 main.py ./

# Create directories for image storage with proper permissions
RUN mkdir -p /opt/app-root/src/images && \
    chmod -R g+rwX /opt/app-root/src/images

# Fix permissions for OpenShift - ensure all files are group writable
RUN chgrp -R 0 /opt/app-root/src && \
    chmod -R g=u /opt/app-root/src

# Set default environment variables (can be overridden in deployment)
ENV IMAGE_OUTPUT_PATH=/opt/app-root/src/images \
    DIFFUSERS_RUNTIME_URL=http://tiny-sd:8080 \
    DIFFUSERS_MODEL_ID=model \
    PORT=8080

# Expose the application port (UBI convention is 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Start the MCP server
CMD ["uv", "run", "python", "main.py", "--port", "8080"]
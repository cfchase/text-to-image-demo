"""
Global pytest configuration and fixtures
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables before any imports
os.environ["MCP_CONFIG_PATH"] = "tests/fixtures/test-mcp-config.json"
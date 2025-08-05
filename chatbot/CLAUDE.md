# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python FastMCP client project that enables interaction with MCP servers through Claude AI. The codebase provides a multi-server client implementation:
- **multi_client.py**: Multi-server FastMCP client supporting both stdio and HTTP connections

## Architecture

### Core Components

1. **Client Class Structure**:
   - Uses FastMCP's Client class for simplified connection management
   - Anthropic integration for Claude AI interactions
   - Tool execution pipeline between Claude and MCP servers
   - Interactive REPL-like chat interface

2. **Connection Flow**:
   - Load environment variables (ANTHROPIC_API_KEY from .env)
   - Initialize Anthropic client
   - Connect to MCP server(s) using FastMCP Client
   - List available tools from server(s)
   - Process queries through Claude with tool access
   - Execute tool calls and return results

3. **Key Dependencies**:
   - `fastmcp>=2.9.2`: FastMCP library for MCP client/server interactions
   - `anthropic>=0.55.0`: Claude AI Python SDK
   - `python-dotenv>=1.1.1`: Environment variable management

## Common Development Commands

### Running the Client

```bash
# Run multi-server client
python multi_client.py --config config.json
```

### Package Management

This project uses `uv` as the package manager:

```bash
# Install dependencies
uv pip install -e .

# Update dependencies
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt
```

## Project Structure

- **Python 3.13** required (specified in .python-version)
- **Environment variables**: Store ANTHROPIC_API_KEY in .env file
- **Simplified architecture**: FastMCP handles connection management, session handling, and protocol details
- **No test infrastructure**: Tests need to be implemented
- **Minimal error handling**: Basic try-catch in chat loops only

## Key FastMCP Features Used

- **Single Server**: `Client(command_string)` for stdio connections
- **Multi-Server**: `Client(config_dict)` with `{"mcpServers": {...}}` format
- **Native Multi-Server Support**: FastMCP automatically handles tool prefixing and routing
- **Async Context Manager**: Uses `async with Client(...)` pattern for automatic cleanup
- **Direct Tool Access**: `client.list_tools()` and `client.call_tool()` methods
- **Tool Types**: Tools are returned as `mcp.types.Tool` objects with attributes (not dictionaries)

## Client Features

### multi_client.py
- Loads configuration from JSON file
- Supports multiple servers in one session
- Both stdio and HTTP server types
- FastMCP handles tool name prefixing with server names
- Tool calls automatically routed to correct server

## Configuration Format

The multi-server client uses FastMCP's native config format:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "command",
      "args": ["arg1", "arg2"]
    },
    "http_server": {
      "url": "http://example.com/mcp"
    }
  }
}
```

## Important Notes

- The project is in early development (v0.1.0) with minimal documentation
- The client handles both stdio and HTTP connections
- Tool schemas are automatically extracted from MCP servers and passed to Claude
- The chat loop runs continuously until user types 'quit'
- FastMCP handles all the complexity of multi-server connections internally

## Git Commit Guidelines

When creating commits in this repository:
- **DO NOT** include Claude-specific references in commit messages
- **DO NOT** mention "Generated with Claude Code" or similar attributions
- **DO NOT** add Co-Authored-By references to Claude
- Focus commit messages on the technical changes made
- Use conventional commit format when appropriate (feat:, fix:, docs:, etc.)
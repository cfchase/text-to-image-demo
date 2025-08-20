# MCP (Model Context Protocol) Integration Guide

## Overview

This document describes the MCP integration in the chatbot backend, which enables Claude to use external tools provided by MCP servers. The integration uses FastMCP v2.9.2 to connect to MCP servers and expose their tools to Claude.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Claude API    │────▶│  MCP Service │────▶│ MCP Servers │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   FastMCP    │
                        │   Client     │
                        └──────────────┘
```

## Configuration

### MCP Configuration File

The MCP service reads server configurations from `mcp-config.json` in the backend directory:

```json
{
  "mcpServers": {
    "weather-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["weather_server.py"],
      "env": {
        "API_KEY": "your-api-key"
      }
    },
    "calculator-server": {
      "transport": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Environment Variables

- `MCP_CONFIG_PATH`: Path to the MCP configuration file (default: `mcp-config.json`)

### Supported Transports

1. **stdio**: Launches a process and communicates via stdin/stdout
   - Required fields: `command`
   - Optional fields: `args`, `env`

2. **http/https**: Connects to an HTTP/HTTPS endpoint
   - Required fields: `url`
   - Optional fields: `headers`

3. **websocket**: Connects via WebSocket
   - Required fields: `url`
   - Optional fields: `headers`

## API Usage

### Service Initialization

The MCP service is automatically initialized when the FastAPI application starts:

```python
# In main.py lifespan
await mcp_service.initialize()
```

### Tool Discovery

Tools are discovered from all configured MCP servers at startup:

```python
tools = mcp_service.get_tools()
# Returns list of Anthropic-compatible tool definitions
```

### Tool Execution

Tools are executed through the Claude service when Claude decides to use them:

```python
result = await mcp_service.call_tool(
    name="get_weather",
    arguments={"location": "New York"}
)
# Returns tool execution result directly
```

## Security Features

### Input Validation

- **Tool Names**: Must match pattern `^[a-zA-Z0-9_\-\.]+$`, max 100 characters
- **Argument Keys**: Alphanumeric with `_`, `-`, `.`, max 100 characters
- **String Values**: Truncated to 10,000 characters, control characters removed

### Sanitization

All tool arguments are sanitized before execution:
- Control characters (except `\n`, `\r`, `\t`) are removed from strings
- Long strings are truncated to prevent memory issues
- Non-JSON-serializable data is rejected

### Configuration Validation

Server configurations are validated by FastMCP's internal validation:
- FastMCP handles transport type validation
- Required fields are determined based on the server configuration
- The `transport` field may be optional for some server types

## Error Handling

### Exception Types

- `MCPConfigError`: Configuration file issues
- `MCPConnectionError`: Server connection failures
- `MCPToolNotFoundError`: Tool doesn't exist
- `MCPToolExecutionError`: Tool execution failed
- `MCPValidationError`: Input validation failed
- `MCPTimeoutError`: Tool execution timeout

### Retry Logic

- **Max Retries**: 3 attempts
- **Retry Delay**: 1 second (exponential backoff for connection errors)
- **Timeout**: 30 seconds per tool execution
- **Non-Retryable**: Validation errors, tool not found errors

## Configuration Structure

### MCP Configuration Format

The `mcp-config.json` file should follow this structure:

```json
{
  "mcpServers": {
    "server-name": {
      // Server configuration
    }
  }
}
```

### Server Configuration Fields

- **transport** (optional): Transport type ("stdio", "http", "https", "websocket")
- **command**: Command to execute (for stdio transport)
- **args**: Array of command arguments
- **url**: Server URL (for http/https/websocket transports)
- **env**: Environment variables object

FastMCP will automatically determine the appropriate configuration based on the provided fields.

## Creating an MCP Server

### Example: Simple Calculator Server

```python
#!/usr/bin/env python3
from fastmcp import FastMCP

mcp = FastMCP("calculator")

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp.run()
```

### Configuration

Add to `mcp-config.json`:

```json
{
  "mcpServers": {
    "calculator": {
      "transport": "stdio",
      "command": "python",
      "args": ["path/to/calculator_server.py"]
    }
  }
}
```

## Testing

### Unit Tests

```python
# Test MCP service initialization
async def test_mcp_initialization():
    await mcp_service.initialize()
    assert mcp_service.is_available
    assert len(mcp_service.get_tools()) > 0

# Test tool execution
async def test_tool_execution():
    result = await mcp_service.call_tool("add", {"a": 2, "b": 3})
    assert result == "5"
```

### Mock MCP Server

A mock MCP server is provided for testing:

```bash
python backend/tests/mocks/mock_mcp_server.py
```

### Test Configuration

Use `tests/fixtures/test-mcp-config.json` for testing:

```json
{
  "mcpServers": {}
}
```

## Monitoring and Debugging

### Logging

The MCP service logs important events:

```python
# Initialization
INFO: MCP initialized with 5 tools from 2 servers

# Tool execution
INFO: Executing tool 'get_weather' with args: {'location': 'NYC'}
ERROR: Tool 'calculate' failed on attempt 2/3: Connection error

# Connection issues
WARNING: MCP server 'weather-server' is not responding
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("app.services.mcp_service").setLevel(logging.DEBUG)
```

## Performance Considerations

### Connection Pooling

- Each tool execution creates a new context with the MCP client
- Consider implementing connection pooling for high-traffic scenarios

### Caching

- Tools are discovered once at startup and cached
- No automatic refresh - restart required for configuration changes

### Concurrent Execution

- Multiple tools can be called concurrently
- Each tool execution is independent

## Troubleshooting

### Common Issues

1. **"MCP service not initialized"**
   - Ensure `mcp_service.initialize()` is called at startup
   - Check that configuration file exists and is valid

2. **"Tool not found"**
   - Verify tool name matches exactly (case-sensitive)
   - Check that MCP server is running and accessible
   - Review tool discovery logs

3. **"Connection timeout"**
   - Increase timeout in constants if needed
   - Check network connectivity to MCP servers
   - Verify server is responding

4. **"Invalid configuration"**
   - Validate JSON syntax in mcp-config.json
   - Ensure required fields for transport type
   - Check server names are valid

### Debug Checklist

1. Check configuration file is valid JSON
2. Verify MCP servers are running
3. Test servers manually with FastMCP client
4. Review logs for specific error messages
5. Enable debug logging if needed

## Best Practices

1. **Security**
   - Never expose sensitive data in tool responses
   - Validate all inputs before processing
   - Use environment variables for API keys

2. **Error Handling**
   - Return meaningful error messages
   - Handle edge cases gracefully
   - Log errors for debugging

3. **Performance**
   - Keep tool execution time under 30 seconds
   - Return concise responses
   - Avoid large data transfers

4. **Testing**
   - Test with mock servers during development
   - Include edge cases in tests
   - Verify error handling

## Future Enhancements

1. **Dynamic Tool Discovery**
   - Refresh tools without restart
   - Hot-reload configuration changes

2. **Connection Management**
   - Implement connection pooling
   - Add health checks for servers

3. **Metrics and Monitoring**
   - Track tool usage statistics
   - Monitor execution times
   - Alert on failures

4. **Advanced Features**
   - Tool versioning
   - Rate limiting per tool
   - Custom authentication
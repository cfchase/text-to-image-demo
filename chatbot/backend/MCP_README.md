# MCP Integration Setup Guide

This guide helps you set up MCP (Model Context Protocol) servers to extend Claude's capabilities with custom tools.

## Quick Start

1. **Create Configuration File**

   Create `mcp-config.json` in the backend directory:

   ```json
   {
     "mcpServers": {}
   }
   ```

2. **Add Your First MCP Server**

   Example configuration for a weather server:

   ```json
   {
     "mcpServers": {
       "weather": {
         "transport": "stdio",
         "command": "python",
         "args": ["servers/weather_server.py"]
       }
     }
   }
   ```

3. **Start the Application**

   ```bash
   make dev-backend
   ```

   Claude will now have access to tools from your MCP servers!

## Configuration Examples

### Python MCP Server (stdio)

```json
{
  "mcpServers": {
    "my-python-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### Node.js MCP Server (stdio)

```json
{
  "mcpServers": {
    "my-node-server": {
      "transport": "stdio",
      "command": "node",
      "args": ["path/to/server.js"]
    }
  }
}
```

### HTTP MCP Server

```json
{
  "mcpServers": {
    "my-http-server": {
      "transport": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Multiple Servers

```json
{
  "mcpServers": {
    "calculator": {
      "transport": "stdio",
      "command": "python",
      "args": ["servers/calculator.py"]
    },
    "database": {
      "transport": "http",
      "url": "http://localhost:9000/mcp"
    },
    "file-system": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    }
  }
}
```

**Note**: The `transport` field may be optional depending on your MCP server implementation. FastMCP will determine the appropriate transport based on the provided fields.

## Creating Your Own MCP Server

### Python Example

Create `my_server.py`:

```python
#!/usr/bin/env python3
from fastmcp import FastMCP

# Create server instance
mcp = FastMCP("my-server")

@mcp.tool()
def greet(name: str) -> str:
    """
    Greet someone by name
    
    Args:
        name: The name to greet
        
    Returns:
        A greeting message
    """
    return f"Hello, {name}! Welcome to MCP!"

@mcp.tool()
def calculate_age(birth_year: int) -> int:
    """
    Calculate age from birth year
    
    Args:
        birth_year: Year of birth
        
    Returns:
        Current age
    """
    from datetime import datetime
    current_year = datetime.now().year
    return current_year - birth_year

if __name__ == "__main__":
    mcp.run()
```

### Add to Configuration

```json
{
  "mcpServers": {
    "my-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["my_server.py"]
    }
  }
}
```

### Test Your Server

1. Start the backend: `make dev-backend`
2. Check logs for: `MCP initialized with X tools from Y servers`
3. Ask Claude to use your tools!

## Available Transports

### stdio (Recommended for local servers)
- Launches a process and communicates via stdin/stdout
- Best for Python, Node.js, or any executable
- Required: `command`
- Optional: `args`, `env`

### http/https
- Connects to HTTP endpoints
- Best for remote or containerized servers
- Required: `url`
- Optional: `headers`

### websocket
- Real-time bidirectional communication
- Best for streaming or long-running connections
- Required: `url`
- Optional: `headers`

## Environment Variables

Pass environment variables to your servers:

```json
{
  "mcpServers": {
    "api-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["api_server.py"],
      "env": {
        "API_KEY": "your-key-here",
        "API_URL": "https://api.example.com",
        "DEBUG": "true"
      }
    }
  }
}
```

## Troubleshooting

### Server Not Found

```
ERROR: Tool 'my_tool' not found
```

**Solutions:**
- Check server is in mcp-config.json
- Verify command/path is correct
- Ensure server file is executable
- Check server starts without errors

### Connection Failed

```
ERROR: Failed to initialize MCP tools: Connection error
```

**Solutions:**
- For stdio: Verify command exists in PATH
- For http: Check URL is accessible
- Review server logs for errors
- Try running server manually

### No Tools Available

```
INFO: MCP initialized with 0 tools from 1 servers
```

**Solutions:**
- Verify server has @mcp.tool() decorators
- Check tool functions have docstrings
- Ensure server runs without errors
- Review initialization logs

### Testing Your Setup

1. **Manual Test:**
   ```bash
   python your_server.py
   ```
   Should output: `Server started on stdio`

2. **Check Available Tools:**
   Look for log: `MCP initialized with X tools`

3. **Test with Claude:**
   Ask: "What tools do you have available?"

## Security Best Practices

1. **API Keys**: Use environment variables, never hardcode
2. **File Access**: Limit server permissions
3. **Network**: Use HTTPS for remote servers
4. **Validation**: Validate inputs in your tools
5. **Logging**: Don't log sensitive data

## Example Use Cases

### Weather Information
```python
@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city"""
    # Implementation here
```

### Database Queries
```python
@mcp.tool()
def query_database(sql: str) -> list:
    """Execute a read-only SQL query"""
    # Implementation here
```

### File Operations
```python
@mcp.tool()
def read_file(path: str) -> str:
    """Read contents of a file"""
    # Implementation here
```

### API Integration
```python
@mcp.tool()
def call_api(endpoint: str, method: str = "GET") -> dict:
    """Call an external API"""
    # Implementation here
```

## Need Help?

- Check the [detailed documentation](docs/MCP_INTEGRATION.md)
- Review [example servers](tests/mocks/mock_mcp_server.py)
- Enable debug logging in your server
- Check backend logs for detailed errors
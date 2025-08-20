# MCP Service API Reference

## Classes

### MCPService

Main service class for managing MCP servers and tools.

```python
from app.services.mcp_service import mcp_service
```

#### Properties

##### `is_available: bool`
Returns whether the MCP service has any tools available.

```python
if mcp_service.is_available:
    print("MCP tools are available")
```

#### Methods

##### `async initialize() -> None`
Initialize the MCP service by connecting to servers and discovering tools.

```python
await mcp_service.initialize()
```

**Raises:**
- `MCPConnectionError`: If connection to servers fails
- `MCPConfigError`: If configuration is invalid

##### `get_tools() -> List[Dict[str, Any]]`
Get the list of available tools in Anthropic format.

```python
tools = mcp_service.get_tools()
# Returns:
# [
#   {
#     "name": "get_weather",
#     "description": "Get weather for a location",
#     "input_schema": {
#       "type": "object",
#       "properties": {...},
#       "required": [...]
#     }
#   }
# ]
```

##### `async call_tool(name: str, arguments: Dict[str, Any]) -> Any`
Execute a tool and return the result.

```python
result = await mcp_service.call_tool(
    name="calculate",
    arguments={"expression": "2 + 2"}
)
print(f"Result: {result}")
```

**Parameters:**
- `name`: Tool name to execute
- `arguments`: Dictionary of arguments for the tool

**Returns:**
- Tool execution result (string or serialized data)

**Raises:**
- `MCPToolNotFoundError`: If tool doesn't exist
- `MCPValidationError`: If inputs are invalid
- `MCPToolExecutionError`: If execution fails after retries
- `MCPTimeoutError`: If execution exceeds timeout

##### `async shutdown() -> None`
Shutdown the MCP service and close all connections.

```python
await mcp_service.shutdown()
```

## Exceptions

### MCPError
Base exception for all MCP-related errors.

### MCPConfigError
Raised when configuration is invalid or cannot be loaded.

```python
try:
    mcp_service._load_config_and_client()
except MCPConfigError as e:
    print(f"Config error: {e}")
```

### MCPConnectionError
Raised when connection to MCP servers fails.

```python
try:
    await mcp_service.initialize()
except MCPConnectionError as e:
    print(f"Connection failed: {e}")
```

### MCPToolNotFoundError
Raised when requested tool doesn't exist.

```python
try:
    await mcp_service.call_tool("unknown_tool", {})
except MCPToolNotFoundError as e:
    print(f"Tool not found: {e.tool_name}")
    print(f"Available tools: {e.available_tools}")
```

### MCPValidationError
Raised when tool inputs fail validation.

```python
try:
    await mcp_service.call_tool("tool$invalid", {})
except MCPValidationError as e:
    print(f"Validation error: {e}")
```

### MCPToolExecutionError
Raised when tool execution fails after all retries.

```python
try:
    await mcp_service.call_tool("failing_tool", {})
except MCPToolExecutionError as e:
    print(f"Execution failed: {e}")
    print(f"Original error: {e.original_error}")
```

### MCPTimeoutError
Raised when tool execution exceeds timeout.

```python
try:
    await mcp_service.call_tool("slow_tool", {})
except MCPTimeoutError as e:
    print(f"Timeout after {e.timeout_seconds}s")
```

## Integration with Claude

### Automatic Tool Discovery

Tools are automatically discovered and provided to Claude:

```python
# In claude.py
tools = mcp_service.get_tools()
if tools:
    stream_params["tools"] = tools
```

### Tool Execution

Claude executes tools through the service:

```python
# In claude.py
async def _execute_tool(self, tool_use: ToolUseBlock) -> str:
    result = await mcp_service.call_tool(
        tool_use.name, 
        tool_use.input
    )
    return result
```

## Configuration Constants

```python
# Security
MAX_TOOL_NAME_LENGTH = 100
MAX_ARG_KEY_LENGTH = 100  
MAX_STRING_ARG_LENGTH = 10000
VALID_TOOL_NAME_PATTERN = r'^[a-zA-Z0-9_\-\.]+$'

# Retry
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
TOOL_TIMEOUT_SECONDS = 30.0
```

## Usage Examples

### Basic Tool Execution

```python
# Simple tool call
result = await mcp_service.call_tool(
    "greet",
    {"name": "Alice"}
)
print(result)  # "Hello, Alice!"
```

### Error Handling

```python
try:
    result = await mcp_service.call_tool(
        "risky_operation",
        {"param": "value"}
    )
    process_result(result)
except MCPTimeoutError:
    print("Operation timed out")
except MCPToolExecutionError as e:
    print(f"Failed after {MAX_RETRIES} attempts")
except Exception as e:
    print(f"Error: {str(e)}")
```

### Concurrent Tool Calls

```python
import asyncio

# Execute multiple tools concurrently
tasks = [
    mcp_service.call_tool("tool1", {"arg": "a"}),
    mcp_service.call_tool("tool2", {"arg": "b"}),
    mcp_service.call_tool("tool3", {"arg": "c"})
]

results = await asyncio.gather(*tasks)
for i, result in enumerate(results):
    print(f"Tool {i+1}: {result}")
```

### Custom Timeout

```python
# Temporarily override timeout
from app.services.mcp_service import TOOL_TIMEOUT_SECONDS
original_timeout = TOOL_TIMEOUT_SECONDS
try:
    TOOL_TIMEOUT_SECONDS = 60.0  # 1 minute
    result = await mcp_service.call_tool(
        "long_running_task",
        {"data": "large"}
    )
    print(f"Result: {result}")
finally:
    TOOL_TIMEOUT_SECONDS = original_timeout
```

## Testing

### Mock MCP Service

```python
from unittest.mock import patch, AsyncMock

@patch('app.services.mcp_service.mcp_service')
async def test_with_mock_mcp(mock_service):
    # Mock tool list
    mock_service.get_tools.return_value = [
        {
            "name": "test_tool",
            "description": "Test",
            "input_schema": {...}
        }
    ]
    
    # Mock tool execution
    mock_service.call_tool.return_value = "Test result"
    
    # Your test code here
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_mcp_integration():
    # Initialize with test config
    await mcp_service.initialize()
    
    # Verify tools loaded
    tools = mcp_service.get_tools()
    assert len(tools) > 0
    
    # Execute test tool
    result = await mcp_service.call_tool(
        "echo",
        {"message": "test"}
    )
    assert result == "Echo: test"
```
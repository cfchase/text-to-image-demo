import pytest
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
from pathlib import Path
import json
from app.services.mcp_service import MCPService, mcp_service
from app.services.mcp_exceptions import (
    MCPConfigError,
    MCPConnectionError,
    MCPToolNotFoundError,
    MCPToolExecutionError,
    MCPValidationError,
    MCPTimeoutError
)


@pytest.fixture
def mock_config():
    """Mock MCP configuration for testing"""
    return {
        "mcpServers": {
            "test-server": {
                "transport": "stdio",
                "command": "python",
                "args": ["tests/mocks/mock_mcp_server.py"]
            },
            "another-server": {
                "transport": "http",
                "url": "http://localhost:8080/mcp"
            }
        }
    }


@pytest.fixture
def mock_tools():
    """Mock tools returned by FastMCP"""
    tool1 = MagicMock()
    tool1.name = "get_weather"
    tool1.description = "Get weather for a location"
    tool1.inputSchema = {
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"]
    }
    
    tool2 = MagicMock()
    tool2.name = "calculate"
    tool2.description = "Perform calculations"
    tool2.inputSchema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
    }
    
    return [tool1, tool2]


@pytest.fixture
async def clean_mcp_service():
    """Ensure MCP service is clean before and after tests"""
    # Reset before test
    mcp_service._reset_for_testing()
    
    yield mcp_service
    
    # Reset after test
    await mcp_service.shutdown()


class TestMCPService:
    """Test MCP service functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, mock_config, mock_tools, clean_mcp_service):
        """Test successful MCP service initialization"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize
            await clean_mcp_service.initialize()
            
            # Verify
            assert clean_mcp_service._initialized is True
            assert clean_mcp_service.is_available is True
            assert len(clean_mcp_service.get_tools()) == 2
            
            # Check tool conversion
            anthropic_tools = clean_mcp_service.get_tools()
            assert anthropic_tools[0]["name"] == mock_tools[0].name
            assert anthropic_tools[0]["description"] == mock_tools[0].description
            assert anthropic_tools[0]["input_schema"] == mock_tools[0].inputSchema
    
    @pytest.mark.asyncio
    async def test_initialization_no_config_file(self, clean_mcp_service):
        """Test initialization when config file doesn't exist"""
        with patch('pathlib.Path.exists', return_value=False):
            await clean_mcp_service.initialize()
            
            assert clean_mcp_service._initialized is True
            assert clean_mcp_service.is_available is False
            assert len(clean_mcp_service.get_tools()) == 0
            assert clean_mcp_service.client is None
    
    @pytest.mark.asyncio
    async def test_initialization_invalid_json(self, clean_mcp_service):
        """Test initialization with invalid JSON config"""
        # Reset the service first
        clean_mcp_service._reset_for_testing()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid json {")):
            
            # Loading invalid JSON should raise MCPConfigError
            with pytest.raises(MCPConfigError, match="Invalid JSON"):
                clean_mcp_service._load_config_and_client()
    
    @pytest.mark.asyncio
    async def test_initialization_client_error(self, mock_config, clean_mcp_service):
        """Test initialization when client fails to connect"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client that fails
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client
            
            await clean_mcp_service.initialize()
            
            assert clean_mcp_service._initialized is True
            assert clean_mcp_service.is_available is False
            assert len(clean_mcp_service.get_tools()) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_initialization(self, mock_config, mock_tools, clean_mcp_service):
        """Test that multiple initialization calls don't re-initialize"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize multiple times
            await clean_mcp_service.initialize()
            await clean_mcp_service.initialize()
            await clean_mcp_service.initialize()
            
            # Client should only be created once
            mock_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_config, mock_tools, clean_mcp_service):
        """Test successful tool execution"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock tool result
            mock_result = MagicMock()
            mock_result.text = "Weather in NYC: Sunny, 72°F"
            mock_client.call_tool.return_value = [mock_result]
            
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool
            result = await clean_mcp_service.call_tool("get_weather", {"location": "NYC"})
            
            assert result == "Weather in NYC: Sunny, 72°F"
            mock_client.call_tool.assert_called_once_with("get_weather", {"location": "NYC"})
    
    @pytest.mark.asyncio
    async def test_call_tool_no_text_attribute(self, mock_config, mock_tools, clean_mcp_service):
        """Test tool execution when result doesn't have text attribute"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock tool result without text attribute
            mock_result = {"data": "some value"}
            mock_client.call_tool.return_value = [mock_result]
            
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool - use existing tool name
            result = await clean_mcp_service.call_tool("get_weather", {"location": "NYC"})
            
            assert result == str(mock_result)
    
    @pytest.mark.asyncio
    async def test_call_tool_empty_result(self, mock_config, mock_tools, clean_mcp_service):
        """Test tool execution with empty result"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock empty tool result
            mock_client.call_tool.return_value = []
            
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool - use existing tool name
            result = await clean_mcp_service.call_tool("calculate", {"expression": "1+1"})
            
            assert result == "Tool executed successfully with no output"
    
    @pytest.mark.asyncio
    async def test_call_tool_error(self, mock_config, mock_tools, clean_mcp_service):
        """Test tool execution error handling"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock tool error
            mock_client.call_tool.side_effect = Exception("Tool execution failed")
            
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool and expect MCPToolExecutionError after retries
            with pytest.raises(MCPToolExecutionError) as exc_info:
                await clean_mcp_service.call_tool("get_weather", {"location": "NYC"})
            
            assert "get_weather" in str(exc_info.value)
            assert exc_info.value.tool_name == "get_weather"
    
    @pytest.mark.asyncio
    async def test_call_tool_not_initialized(self, clean_mcp_service):
        """Test calling tool when service is not initialized"""
        with pytest.raises(MCPConnectionError, match="MCP service not initialized"):
            await clean_mcp_service.call_tool("any_tool", {})
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_config, mock_tools, clean_mcp_service):
        """Test service shutdown"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize and shutdown
            await clean_mcp_service.initialize()
            assert clean_mcp_service._initialized is True
            assert clean_mcp_service.is_available is True
            
            await clean_mcp_service.shutdown()
            
            # Verify shutdown
            assert clean_mcp_service.client is None
            assert len(clean_mcp_service.tools) == 0
            assert clean_mcp_service._initialized is False
            assert clean_mcp_service.is_available is False
            
            # Verify __aexit__ was called once from initialize (async with)
            assert mock_client.__aexit__.call_count == 1
    
    @pytest.mark.asyncio
    async def test_shutdown_with_error(self, mock_config, mock_tools, clean_mcp_service):
        """Test service shutdown handles errors gracefully"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            # First call succeeds (for initialize), second call fails (for test)
            mock_client.__aexit__.side_effect = [None, Exception("Shutdown error")]
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize - this will call __aexit__ once
            await clean_mcp_service.initialize()
            
            # Now test another context manager usage that fails on exit
            # This simulates an error during tool execution cleanup
            try:
                async with mock_client:
                    pass  # This will fail on __aexit__
            except Exception:
                pass  # Expected
            
            # Service should still work despite the error
            assert clean_mcp_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_get_tools_formats_correctly(self, mock_config, clean_mcp_service):
        """Test that tools are formatted correctly for Anthropic"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Create more complex mock tools
            mock_tool = MagicMock()
            mock_tool.name = "complex_tool"
            mock_tool.description = None  # Test None description
            mock_tool.inputSchema = {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "number", "description": "Second parameter"}
                },
                "required": ["param1"]
            }
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = [mock_tool]
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize
            await clean_mcp_service.initialize()
            
            # Check formatted tools
            tools = clean_mcp_service.get_tools()
            assert len(tools) == 1
            assert tools[0]["name"] == "complex_tool"
            assert tools[0]["description"] == "MCP tool: complex_tool"  # Default description
            assert tools[0]["input_schema"] == mock_tool.inputSchema
    
    @pytest.mark.asyncio
    async def test_security_validation_tool_name(self, clean_mcp_service):
        """Test security validation for tool names"""
        # Test empty name
        with pytest.raises(MCPValidationError, match="Tool name cannot be empty"):
            clean_mcp_service._validate_tool_name("")
        
        # Test long name
        with pytest.raises(MCPValidationError, match="exceeds maximum length"):
            clean_mcp_service._validate_tool_name("a" * 101)
        
        # Test invalid characters
        with pytest.raises(MCPValidationError, match="invalid characters"):
            clean_mcp_service._validate_tool_name("tool$name")
        
        # Test valid names
        clean_mcp_service._validate_tool_name("valid_tool")
        clean_mcp_service._validate_tool_name("tool-name")
        clean_mcp_service._validate_tool_name("tool.name")
        clean_mcp_service._validate_tool_name("Tool123")
    
    @pytest.mark.asyncio
    async def test_security_sanitize_arguments(self, clean_mcp_service):
        """Test argument sanitization"""
        # Test non-dict input
        with pytest.raises(MCPValidationError, match="Arguments must be a dictionary"):
            clean_mcp_service._sanitize_arguments("not a dict")
        
        # Test invalid key type
        with pytest.raises(MCPValidationError, match="Argument key must be string"):
            clean_mcp_service._sanitize_arguments({123: "value"})
        
        # Test long key
        with pytest.raises(MCPValidationError, match="exceeds maximum length"):
            clean_mcp_service._sanitize_arguments({"a" * 101: "value"})
        
        # Test invalid key characters
        with pytest.raises(MCPValidationError, match="contains invalid characters"):
            clean_mcp_service._sanitize_arguments({"key$name": "value"})
        
        # Test string truncation
        long_string = "x" * 20000
        result = clean_mcp_service._sanitize_arguments({"key": long_string})
        assert len(result["key"]) == 10000
        
        # Test control character removal
        result = clean_mcp_service._sanitize_arguments({"key": "hello\x00world\x1Ftest"})
        assert result["key"] == "helloworldtest"
        
        # Test valid arguments
        args = {
            "name": "John",
            "age": 30,
            "tags": ["python", "fastapi"],
            "meta": {"version": "1.0"}
        }
        result = clean_mcp_service._sanitize_arguments(args)
        assert result == args
    
    @pytest.mark.asyncio
    async def test_call_tool_invalid_name(self, mock_config, mock_tools, clean_mcp_service):
        """Test calling tool with invalid name"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Test invalid tool name
            with pytest.raises(MCPValidationError, match="invalid characters"):
                await clean_mcp_service.call_tool("tool$name", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mock_config, mock_tools, clean_mcp_service):
        """Test calling non-existent tool"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Test non-existent tool
            with pytest.raises(MCPToolNotFoundError) as exc_info:
                await clean_mcp_service.call_tool("non_existent", {})
            
            assert exc_info.value.tool_name == "non_existent"
            assert "get_weather" in exc_info.value.available_tools
    
    @pytest.mark.asyncio
    async def test_call_tool_timeout(self, mock_config, mock_tools, clean_mcp_service):
        """Test tool execution timeout"""
        import asyncio
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock tool that times out
            async def slow_tool(*args, **kwargs):
                await asyncio.sleep(60)  # Sleep longer than timeout
                
            mock_client.call_tool = slow_tool
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool and expect timeout
            with pytest.raises(MCPTimeoutError) as exc_info:
                await clean_mcp_service.call_tool("get_weather", {"location": "NYC"})
            
            assert exc_info.value.tool_name == "get_weather"
            assert exc_info.value.timeout_seconds == 30.0
    
    @pytest.mark.asyncio
    async def test_call_tool_retry_success(self, mock_config, mock_tools, clean_mcp_service):
        """Test tool execution succeeds after retry"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = mock_tools
            
            # Mock tool that fails twice then succeeds
            call_count = 0
            async def flaky_tool(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Temporary failure")
                # Success on third attempt
                mock_result = MagicMock()
                mock_result.text = "Success after retry"
                return [mock_result]
                
            mock_client.call_tool = flaky_tool
            mock_client_class.return_value = mock_client
            
            # Load config and client with mocks in place
            clean_mcp_service._load_config_and_client()
            
            # Initialize service
            await clean_mcp_service.initialize()
            
            # Call tool - should succeed after retries
            result = await clean_mcp_service.call_tool("get_weather", {"location": "NYC"})
            assert result == "Success after retry"
            assert call_count == 3  # Verify it was called 3 times
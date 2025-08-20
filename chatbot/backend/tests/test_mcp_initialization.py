import pytest
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
from pathlib import Path
import json
from app.services.mcp_service import mcp_service


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


@pytest.fixture(autouse=True)
async def reset_mcp_service():
    """Reset MCP service state before each test"""
    mcp_service._reset_for_testing()
    yield
    await mcp_service.shutdown()


class TestMCPInitialization:
    """Test MCP service initialization"""
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_with_tools(self, mock_config):
        """Test that MCP initialization loads servers and discovers tools correctly"""
        # Create mock tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "get_weather"
        mock_tool1.description = "Get weather information"
        mock_tool1.inputSchema = {"type": "object", "properties": {"location": {"type": "string"}}}
        
        mock_tool2 = MagicMock()
        mock_tool2.name = "calculate"
        mock_tool2.description = "Perform calculations"
        mock_tool2.inputSchema = {"type": "object", "properties": {"expression": {"type": "string"}}}
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.list_tools.return_value = [mock_tool1, mock_tool2]
            mock_client_class.return_value = mock_client
            
            # Load config and initialize
            mcp_service._load_config_and_client()
            await mcp_service.initialize()
            
            # Verify initialization
            assert mcp_service._initialized is True
            assert mcp_service.is_available is True
            
            # Verify tools were discovered and converted correctly
            tools = mcp_service.get_tools()
            assert len(tools) == 2
            
            # Check first tool
            assert tools[0]["name"] == "get_weather"
            assert tools[0]["description"] == "Get weather information"
            assert tools[0]["input_schema"] == {"type": "object", "properties": {"location": {"type": "string"}}}
            
            # Check second tool
            assert tools[1]["name"] == "calculate"
            assert tools[1]["description"] == "Perform calculations"
            assert tools[1]["input_schema"] == {"type": "object", "properties": {"expression": {"type": "string"}}}
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_no_config_file(self):
        """Test MCP initialization when config file doesn't exist"""
        with patch('pathlib.Path.exists', return_value=False):
            # Load config and initialize
            mcp_service._load_config_and_client()
            await mcp_service.initialize()
            
            # Verify initialization with no tools
            assert mcp_service._initialized is True
            assert mcp_service.is_available is False
            assert len(mcp_service.get_tools()) == 0
            assert mcp_service.client is None
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_empty_servers(self):
        """Test MCP initialization with empty server list"""
        empty_config = {"mcpServers": {}}
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(empty_config))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.list_tools.return_value = []
            mock_client_class.return_value = mock_client
            
            # Load config and initialize
            mcp_service._load_config_and_client()
            await mcp_service.initialize()
            
            # Verify initialization with no tools
            assert mcp_service._initialized is True
            assert mcp_service.is_available is False
            assert len(mcp_service.get_tools()) == 0
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_with_tool_discovery_error(self):
        """Test MCP initialization handles tool discovery errors gracefully"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps({"mcpServers": {"test": {}}}))), \
             patch('app.services.mcp_service.Client') as mock_client_class:
            
            # Setup mock client that raises error during tool discovery
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.list_tools.side_effect = Exception("Tool discovery failed")
            mock_client_class.return_value = mock_client
            
            # Load config and initialize
            mcp_service._load_config_and_client()
            await mcp_service.initialize()
            
            # Service should still be initialized but with no tools
            assert mcp_service._initialized is True
            assert mcp_service.is_available is False
            assert len(mcp_service.get_tools()) == 0
"""Custom exceptions for MCP service"""
from typing import Optional


class MCPError(Exception):
    """Base exception for MCP service errors"""
    pass


class MCPConfigError(MCPError):
    """Error loading or parsing MCP configuration"""
    pass


class MCPConnectionError(MCPError):
    """Error connecting to MCP servers"""
    def __init__(self, message: str, server_name: Optional[str] = None):
        super().__init__(message)
        self.server_name = server_name


class MCPToolNotFoundError(MCPError):
    """Tool not found in available tools"""
    def __init__(self, tool_name: str, available_tools: list[str]):
        super().__init__(f"Tool '{tool_name}' not found. Available tools: {available_tools}")
        self.tool_name = tool_name
        self.available_tools = available_tools


class MCPToolExecutionError(MCPError):
    """Error executing MCP tool"""
    def __init__(self, tool_name: str, original_error: Exception):
        super().__init__(f"Failed to execute tool '{tool_name}': {str(original_error)}")
        self.tool_name = tool_name
        self.original_error = original_error


class MCPValidationError(MCPError):
    """Input validation error"""
    pass


class MCPTimeoutError(MCPError):
    """Tool execution timeout"""
    def __init__(self, tool_name: str, timeout_seconds: float):
        super().__init__(f"Tool '{tool_name}' timed out after {timeout_seconds} seconds")
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
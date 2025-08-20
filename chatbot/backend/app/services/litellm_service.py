from typing import AsyncGenerator, Optional, List, Dict, Any
import logging
import json
import litellm
from litellm import acompletion, completion
from app.config import settings
from app.services.mcp_service import mcp_service

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging


class LiteLLMService:
    """Service for interacting with LLMs via LiteLLM"""
    
    def __init__(self):
        self.model_name: str = settings.model
        self.provider: str = settings.provider or self._detect_provider()
        self._configure_provider()
        
        # If using custom base URL with OpenAI-compatible endpoint
        if settings.api_base_url and self.provider == 'openai':
            self.model_name = f"openai/{self.model_name}"
            
        logger.info(f"LiteLLM service initialized with provider: {self.provider}, model: {self.model_name}")
    
    def _detect_provider(self) -> str:
        """Auto-detect provider from model name"""
        model_lower = self.model_name.lower()
        if 'claude' in model_lower:
            return 'anthropic'
        elif 'gpt' in model_lower:
            return 'openai'
        elif 'gemini' in model_lower:
            return 'google'
        else:
            return 'openai'  # Default to OpenAI
    
    def _configure_provider(self):
        """Configure provider-specific settings"""
        import os
        
        # API key is required for all providers
        if not settings.api_key:
            logger.warning(f"No API key configured for {self.provider}. Service may not be available.")
            return
        
        # Set the appropriate environment variable based on provider
        if self.provider == 'anthropic':
            os.environ["ANTHROPIC_API_KEY"] = settings.api_key
        elif self.provider == 'openai':
            os.environ["OPENAI_API_KEY"] = settings.api_key
            # Set custom base URL if provided (for OpenAI-compatible endpoints)
            if settings.api_base_url:
                os.environ["OPENAI_API_BASE"] = settings.api_base_url
                logger.info(f"Using custom OpenAI API base URL: {settings.api_base_url}")
        elif self.provider == 'google':
            os.environ["GEMINI_API_KEY"] = settings.api_key
        elif self.provider == 'azure':
            os.environ["AZURE_API_KEY"] = settings.api_key
        else:
            # For any other provider, set a generic API key
            os.environ["API_KEY"] = settings.api_key
            
        logger.info(f"Configured API key for provider: {self.provider}")
    
    
    @property
    def is_available(self) -> bool:
        """Check if LiteLLM service is available"""
        # All providers require an API key
        return bool(settings.api_key)
    
    async def get_completion(
        self, 
        message: str, 
        user_id: Optional[str] = None, 
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Get a non-streaming completion from LiteLLM
        
        Args:
            message: The user's message
            user_id: Optional user identifier for tracking
            conversation_history: Previous conversation messages
            
        Returns:
            The LLM response text
            
        Raises:
            Exception: If LLM is not available or API call fails
        """
        if not self.is_available:
            raise Exception("LiteLLM service is not available. Please configure an API key.")
        
        try:
            # Prepare messages
            messages = conversation_history if conversation_history else []
            # Only add user message if one was provided and it's different from the last message
            if message and (not conversation_history or conversation_history[-1].get("content") != message):
                messages.append({"role": "user", "content": message})
            
            # Get available MCP tools and convert to LiteLLM format
            mcp_tools = mcp_service.get_tools()
            tools = self._convert_tools_to_litellm_format(mcp_tools) if mcp_tools else None
            
            # Create message with or without tools
            create_params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
            }
            
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"
            
            # Make the API call
            response = await acompletion(**create_params)
            
            # Process response and handle tool use
            result_text = ""
            message_content = response.choices[0].message
            
            if hasattr(message_content, 'content') and message_content.content:
                result_text = message_content.content
            
            # Handle tool calls if present
            if hasattr(message_content, 'tool_calls') and message_content.tool_calls:
                # Add assistant's message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message_content.content,
                    "tool_calls": [tc.model_dump() for tc in message_content.tool_calls]
                })
                
                # Execute tools and collect results
                for tool_call in message_content.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    tool_result = await mcp_service.call_tool(tool_name, tool_args)
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Continue conversation with tool results
                continuation = await self.get_completion("", user_id, messages)
                result_text = continuation if not result_text else f"{result_text}\n{continuation}"
            
            return result_text if result_text else "No response generated"
            
        except Exception as e:
            logger.error(f"Error getting LiteLLM completion: {str(e)}")
            # Add more context to the error
            error_str = str(e).lower()
            if "api_key" in error_str or "authentication" in error_str:
                raise Exception("Invalid or missing API key")
            elif "rate" in error_str:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif "overloaded" in error_str or "timeout" in error_str:
                raise Exception("API is currently overloaded. Please try again in a few moments.")
            else:
                raise Exception(f"LLM API error: {str(e)}")
    
    async def get_streaming_completion(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Get a streaming completion from LiteLLM
        
        Args:
            message: The user's message
            user_id: Optional user identifier for tracking
            conversation_history: Previous conversation messages
            
        Yields:
            Chunks of text as they are generated
            
        Raises:
            Exception: If LLM is not available or API call fails
        """
        if not self.is_available:
            raise Exception("LiteLLM service is not available. Please configure an API key.")
        
        try:
            # Prepare messages
            messages = conversation_history if conversation_history else []
            # Only add user message if one was provided and it's different from the last message
            if message and (not conversation_history or conversation_history[-1].get("content") != message):
                messages.append({"role": "user", "content": message})
            
            # Get available MCP tools and convert to LiteLLM format
            mcp_tools = mcp_service.get_tools()
            tools = self._convert_tools_to_litellm_format(mcp_tools) if mcp_tools else None
            
            # Create stream parameters
            stream_params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "stream": True,
            }
            
            if tools:
                stream_params["tools"] = tools
                stream_params["tool_choice"] = "auto"
            
            # Stream the response
            tool_calls = {}
            current_tool_call = None
            
            response = await acompletion(**stream_params)
            
            async for chunk in response:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Handle text content
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
                
                # Handle tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        tool_id = tc_delta.id or current_tool_call
                        
                        if tool_id not in tool_calls:
                            tool_calls[tool_id] = {
                                "id": tool_id,
                                "name": tc_delta.function.name if tc_delta.function else None,
                                "arguments": ""
                            }
                            current_tool_call = tool_id
                        
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_calls[tool_id]["arguments"] += tc_delta.function.arguments
            
            # After streaming completes, handle any tool uses
            if tool_calls:
                # Add assistant's message (Anthropic requires non-empty content)
                messages.append({
                    "role": "assistant",
                    "content": "",  # Empty string instead of None for compatibility
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        }
                        for tc in tool_calls.values()
                    ]
                })
                
                # Execute tools and collect results
                for tool_call in tool_calls.values():
                    try:
                        tool_args = json.loads(tool_call["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    # Execute tool
                    tool_result = await mcp_service.call_tool(tool_call["name"], tool_args)
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result
                    })
                
                # Continue conversation with tool results
                # Don't pass a new message, just continue with existing conversation
                async for chunk in self.get_streaming_completion(None, user_id, messages):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error getting streaming LiteLLM completion: {str(e)}")
            # Add more context to the error
            error_str = str(e).lower()
            if "api_key" in error_str or "authentication" in error_str:
                raise Exception("Invalid or missing API key")
            elif "rate" in error_str:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif "overloaded" in error_str or "timeout" in error_str:
                raise Exception("API is currently overloaded. Please try again in a few moments.")
            else:
                raise Exception(f"LLM API error: {str(e)}")
    
    def _convert_tools_to_litellm_format(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to LiteLLM/OpenAI function calling format
        
        Args:
            mcp_tools: List of MCP tool definitions
            
        Returns:
            List of tools in LiteLLM format
        """
        litellm_tools = []
        
        for tool in mcp_tools:
            # MCP tools from claude.py are already in the correct format
            # but we'll ensure compatibility
            if "function" in tool:
                litellm_tools.append(tool)
            else:
                # Convert if needed
                litellm_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                }
                litellm_tools.append(litellm_tool)
        
        return litellm_tools


# Create a global instance
litellm_service = LiteLLMService()
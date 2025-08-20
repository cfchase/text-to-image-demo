#!/usr/bin/env python3
"""
Mock MCP server for testing
This creates a simple in-memory MCP server with test tools
"""
import json
from typing import Dict, Any
from fastmcp import FastMCP

# Create the mock server
mcp = FastMCP("test-server")


@mcp.tool()
def get_weather(location: str) -> str:
    """
    Get the current weather for a location
    
    Args:
        location: The city or location to get weather for
        
    Returns:
        A string describing the weather
    """
    # Mock weather responses
    weather_data = {
        "new york": "Sunny, 72°F",
        "london": "Cloudy, 61°F", 
        "tokyo": "Rainy, 68°F",
        "paris": "Partly cloudy, 65°F"
    }
    
    location_lower = location.lower()
    if location_lower in weather_data:
        return f"Weather in {location}: {weather_data[location_lower]}"
    else:
        return f"Weather in {location}: Sunny, 70°F (default)"


@mcp.tool()
def calculate(expression: str) -> str:
    """
    Perform a simple calculation
    
    Args:
        expression: A mathematical expression to evaluate
        
    Returns:
        The result of the calculation as a string
    """
    try:
        # Only allow safe mathematical operations
        allowed_names = {
            k: v for k, v in {"__builtins__": {}}.items()
        }
        # Add safe math functions
        import math
        allowed_names.update({
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'pi': math.pi, 'e': math.e
        })
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: Invalid expression - {str(e)}"


@mcp.tool()
def echo(message: str) -> str:
    """
    Echo back the provided message
    
    Args:
        message: The message to echo
        
    Returns:
        The same message prefixed with "Echo: "
    """
    return f"Echo: {message}"


@mcp.tool()
def get_time(timezone: str = "UTC") -> str:
    """
    Get the current time in a specified timezone
    
    Args:
        timezone: The timezone to get time for (default: UTC)
        
    Returns:
        Current time in the specified timezone
    """
    from datetime import datetime
    import pytz
    
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        return f"Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except Exception:
        # Fallback to UTC if timezone is invalid
        current_time = datetime.now(pytz.UTC)
        return f"Current time in UTC: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"


@mcp.tool()
def list_items(category: str) -> Dict[str, Any]:
    """
    List items in a category (mock data)
    
    Args:
        category: The category to list items for
        
    Returns:
        A dictionary containing the items
    """
    mock_data = {
        "fruits": ["apple", "banana", "orange", "grape", "mango"],
        "colors": ["red", "blue", "green", "yellow", "purple"],
        "animals": ["dog", "cat", "elephant", "lion", "penguin"],
        "programming_languages": ["Python", "JavaScript", "Java", "C++", "Go"]
    }
    
    if category.lower() in mock_data:
        return {
            "category": category,
            "items": mock_data[category.lower()],
            "count": len(mock_data[category.lower()])
        }
    else:
        return {
            "category": category,
            "items": [],
            "count": 0,
            "message": f"No items found for category: {category}"
        }


# Run the server if executed directly
if __name__ == "__main__":
    import asyncio
    
    # Run the FastMCP server
    mcp.run()
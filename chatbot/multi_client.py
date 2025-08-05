"""FastMCP Multi-Server Client"""

import asyncio
import argparse
import json

from fastmcp import Client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class MCPMultiClient:
    """FastMCP Client for interacting with multiple MCP servers"""

    def __init__(self):
        # Initialize Anthropic client for Claude AI
        self.anthropic = Anthropic()
        self.client = None
        self.tools = []
        self.messages = []  # Store conversation history

    async def initialize(self, config_path: str):
        """Load configuration and initialize multi-server client"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config file ({e}). Running without MCP servers.")
            config = {"mcpServers": {}}
        
        # Ensure mcpServers key exists
        if "mcpServers" not in config:
            config = {"mcpServers": {}}
        
        server_count = len(config.get('mcpServers', {}))
        print(f"Loaded configuration for {server_count} servers")
        
        # Always create a client, even with empty config
        self.client = Client(config)
        async with self.client:
            self.tools = await self.client.list_tools()
            
            # Convert tools to Anthropic format
            self.available_tools = [{ 
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema
            } for tool in self.tools]
            
            if len(self.tools) == 0:
                print("No MCP servers configured - running without tools")
            else:
                print(f"Connected to servers with {len(self.tools)} total tools")

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        # Use FastMCP client to connect and interact with the servers
        async with self.client:
            # Add user query to conversation history
            self.messages.append({
                "role": "user",
                "content": query
            })

            # Initial Claude API call with full conversation history
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=self.messages,
                tools=self.available_tools
            )

            # Process response and handle tool calls
            final_text = []
            assistant_content = []

            for content in response.content:
                if content.type == 'text':
                    final_text.append(content.text)
                    assistant_content.append({"type": "text", "text": content.text})
                elif content.type == 'tool_use':
                    tool_name = content.name
                    tool_args = content.input
                    
                    # Execute tool call using FastMCP client
                    result = await self.client.call_tool(tool_name, tool_args)
                    
                    # Display tool call and result
                    final_text.append(f"\n[Tool Call: {tool_name}]")
                    final_text.append(f"Arguments: {json.dumps(tool_args, indent=2)}")
                    
                    # Extract the actual result data
                    if hasattr(result, 'data'):
                        final_text.append(f"Result: {result.data}")
                    else:
                        final_text.append(f"Result: {result}")
                    final_text.append("")  # Add blank line for readability
                    
                    # Add tool use to assistant content
                    assistant_content.append({
                        "type": "tool_use",
                        "id": content.id,
                        "name": tool_name,
                        "input": tool_args
                    })

                    # Add assistant message with tool use
                    self.messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # Add tool result
                    self.messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": str(result)
                        }]
                    })

                    # Get next response from Claude with updated history
                    response = self.anthropic.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1000,
                        messages=self.messages,
                    )

                    # Reset assistant content for new response
                    assistant_content = []
                    for new_content in response.content:
                        if new_content.type == 'text':
                            final_text.append(new_content.text)
                            assistant_content.append({"type": "text", "text": new_content.text})

            # Add final assistant response to history
            if assistant_content:
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })

            return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nFastMCP Multi-Server Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Type 'list' to see all available tools.")
        print("Type 'clear' to clear conversation history.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                
                if query.lower() == 'list':
                    print("\nAvailable tools:")
                    for tool in self.tools:
                        print(f"  - {tool.name}: {tool.description}")
                    continue
                
                if query.lower() == 'clear':
                    self.messages = []
                    print("Conversation history cleared.")
                    continue
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")


async def main():
    """Main function to run the FastMCP multi-server client"""
    parser = argparse.ArgumentParser(description="Run FastMCP Multi-Server Client")
    parser.add_argument(
        "--config", type=str, default="config.json", 
        help="Path to configuration file (default: config.json)"
    )
    args = parser.parse_args()

    client = MCPMultiClient()
    await client.initialize(args.config)
    await client.chat_loop()


if __name__ == "__main__":
    asyncio.run(main())
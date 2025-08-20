from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # FastAPI Settings
    port: int = Field(default=8000, description="Port to run the application on")
    environment: str = Field(default="development", description="Environment (development, production)")
    
    # LiteLLM Configuration
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    model: str = Field(default="gpt-3.5-turbo", description="Model to use (e.g., 'gpt-4', 'claude-3-sonnet-20240229', 'gemini-pro')")
    provider: Optional[str] = Field(default=None, description="Optional: Override LLM provider (auto-detected from model by default)")
    api_base_url: Optional[str] = Field(default=None, description="Optional: Custom API base URL for OpenAI-compatible endpoints")
    
    # Model Settings
    max_tokens: int = Field(default=1024, description="Maximum tokens for LLM responses")
    temperature: float = Field(default=0.7, description="Temperature for LLM responses")
    
    # MCP Settings
    mcp_config_path: str = Field(default="mcp-config.json", description="Path to MCP configuration file")


# Create global settings instance
settings = Settings()
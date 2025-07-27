import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # AWS Bedrock Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    
    # Application Configuration
    max_pages: int = 100
    chunk_size: int = 1000
    log_level: str = "INFO"
    
    # Default LLM Configuration
    default_llm_provider: str = "openai"
    default_openai_model: str = "gpt-3.5-turbo"
    default_bedrock_model: str = "anthropic.claude-v2"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 
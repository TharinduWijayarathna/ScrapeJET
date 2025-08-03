import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Simplified application settings"""
    
    # Scraping Configuration
    max_pages: int = int(os.getenv("MAX_PAGES", "100"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "5"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    retry_count: int = int(os.getenv("RETRY_COUNT", "3"))
    request_delay: float = float(os.getenv("REQUEST_DELAY", "1.0"))
    
    # Advanced Scraping Features
    use_selenium: bool = os.getenv("USE_SELENIUM", "true").lower() == "true"
    use_playwright: bool = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"
    scroll_pages: bool = os.getenv("SCROLL_PAGES", "true").lower() == "true"
    screenshot_pages: bool = os.getenv("SCREENSHOT_PAGES", "false").lower() == "true"
    wait_for_js: int = int(os.getenv("WAIT_FOR_JS", "5"))
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # AWS Bedrock Configuration (optional)
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # LLM Configuration
    default_llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    default_openai_model: str = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")
    default_bedrock_model: str = os.getenv("DEFAULT_BEDROCK_MODEL", "anthropic.claude-v2")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 
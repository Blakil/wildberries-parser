import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Bot settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # LLM provider settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")  # openrouter or deepseek
    
    # OpenRouter settings
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku-20240229")
    OPENROUTER_USE_PROXY: bool = os.getenv("OPENROUTER_USE_PROXY", "False").lower() == "true"
    
    # DeepSeek settings
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_USE_PROXY: bool = os.getenv("DEEPSEEK_USE_PROXY", "False").lower() == "true"
    
    # Wildberries settings
    WB_REGION: str = os.getenv("WB_REGION", "ru")
    WB_USE_PROXY: bool = os.getenv("WB_USE_PROXY", "False").lower() == "true"
    
    # Search settings
    SEARCH_KEYWORDS_COUNT: int = int(os.getenv("SEARCH_KEYWORDS_COUNT", "5"))
    MAX_SEARCH_PAGES: int = int(os.getenv("MAX_SEARCH_PAGES", "5"))
    MAX_POSITION_LIMIT: int = int(os.getenv("MAX_POSITION_LIMIT", "500"))
    
    # Proxy settings
    PROXY_ENABLED: bool = os.getenv("PROXY_ENABLED", "False").lower() == "true"
    PROXY_TIMEOUT_MINUTES: int = int(os.getenv("PROXY_TIMEOUT_MINUTES", "2"))
    
    # Retry settings
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_INITIAL_BACKOFF: float = float(os.getenv("LLM_INITIAL_BACKOFF", "2.0"))
    LLM_MAX_BACKOFF: float = float(os.getenv("LLM_MAX_BACKOFF", "60.0"))
    LLM_BACKOFF_FACTOR: float = float(os.getenv("LLM_BACKOFF_FACTOR", "2.0"))
    
    # PIA Proxy settings
    PIA_BASE_HOST: str = os.getenv("PIA_BASE_HOST", "ms94o76z.proxy.piaproxy.co")
    PIA_PORT: int = int(os.getenv("PIA_PORT", "5000"))
    PIA_USERNAME: str = os.getenv("PIA_USERNAME", "")
    PIA_PASSWORD: str = os.getenv("PIA_PASSWORD", "")

config = Config()

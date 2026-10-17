import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


class Settings(BaseSettings):
    # NVIDIA API (build.nvidia.com - Primary Provider)
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Nebius Token Factory Configuration
    NEBIUS_API_KEY: Optional[str] = None
    NEBIUS_BASE_URL: str = "https://api.studio.nebius.com/v1"

    # OpenRouter API (Fallback Provider)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Tavily Web Search (Grounding & Reference Discovery)
    TAVILY_API_KEY: Optional[str] = None

    # Model Configuration (Nemotron 3 Family)
    MODEL_CLASSIFY: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    MODEL_ANALYZE: str = "nvidia/nemotron-3-ultra-550b-a55b"
    MODEL_FIX: str = "nvidia/nemotron-3-super-120b-a12b"
    MODEL_VALIDATE: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

    # Fallback model mappings (e.g. for OpenRouter or alternate providers)
    FALLBACK_MODEL_CLASSIFY: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    FALLBACK_MODEL_ANALYZE: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    FALLBACK_MODEL_FIX: str = "nvidia/nemotron-3-super-120b-a12b:free"

    # Escalating timeout sequence (seconds) - per provider
    LLM_TIMEOUT_SEQUENCE: str = "30,60,90"

    # Agent Loop Parameters
    MAX_RETRIES: int = 3
    SANDBOX_TIMEOUT: int = 30  # seconds
    MAX_CODE_LENGTH: int = 50000  # characters
    MAX_DOC_RESULTS: int = 3

    # Server Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()

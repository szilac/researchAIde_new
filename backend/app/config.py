# Application Configuration

# Session Timouts (in seconds)
SESSION_IDLE_TIMEOUT_SECONDS: int = 1800  # 30 minutes
SESSION_ABSOLUTE_TIMEOUT_SECONDS: int = 28800 # 8 hours 

from pydantic_settings import BaseSettings
from typing import List, Union, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "ResearchAIde Backend"
    API_V1_STR: str = "/api/v1"
    
    # CORS origins can be a list of strings
    # Example: BACKEND_CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
    # For now, let's default to allowing all (*) if not specified, or a sensible default.
    # For production, this should be explicitly set via environment variables.
    BACKEND_CORS_ORIGINS: List[str] = ["*"] # Default to all for dev, or specify

    # ChromaDB Settings
    CHROMA_DB_PATH: str = "data/chroma_db" # Path relative to workspace root for persistence
    DEFAULT_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2" # Example if needed later
    # DEFAULT_CHROMA_COLLECTION: str = "research_papers" # Example if needed later

    # Add other necessary settings here as the project grows
    # For example:
    # DATABASE_URL: Optional[str] = None
    # SECRET_KEY: str = "a_very_secret_key_that_should_be_in_env"

    class Config:
        case_sensitive = True
        # env_file = ".env" # Uncomment to load from .env file by default
        # env_file_encoding = 'utf-8'

settings = Settings() 
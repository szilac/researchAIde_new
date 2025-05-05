from dotenv import load_dotenv

# Load environment variables from .env file before anything else
load_dotenv()

from fastapi import FastAPI

# Import API routers
from app.api.v1.endpoints import llm as llm_router # Adjusted import path
# from .api.v1 import other_router # Example for future routers

app = FastAPI(
    title="ResearchAIde Backend",
    description="API for ResearchAIde features.",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to ResearchAIde API"}

# Include API routers
app.include_router(llm_router.router, prefix="/api/v1/llm", tags=["LLM"])
# app.include_router(other_router.router, prefix="/api/v1/other", tags=["Other"]) # Example

# Add other app configurations, middleware, event handlers etc. below

# Example: Add LLM Manager instantiation here if needed globally
# from .services.llm.llm_manager import LLMManager
# from .models.llm_config import LLMConfig
# try:
#     # Example: Load default config
#     default_llm_config = LLMConfig(model_name="gemini-1.5-flash-001") # API key loaded from env
#     llm_provider = LLMManager.get_provider(default_llm_config)
#     # You could store llm_provider in app.state or use dependency injection
#     app.state.llm_provider = llm_provider 
#     print("Default LLM provider initialized successfully.")
# except Exception as e:
#     print(f"ERROR: Failed to initialize default LLM provider: {e}") 
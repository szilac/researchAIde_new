from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file before anything else
load_dotenv()

# Import the main API router for v1 endpoints
from app.api.v1.api import api_router as api_v1_router # Updated import
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for ResearchAIde features.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the ResearchAIde API"}

# Include the main v1 API router
app.include_router(api_v1_router, prefix=settings.API_V1_STR) # Updated to include the consolidated router

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
"""
API Endpoints for LLM interactions.
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import json

# Assuming LLMManager and providers are accessible
# Adjust imports based on actual project structure
from ....services.llm.llm_manager import LLMManager
from ....models.llm_config import LLMConfig, SafetySetting # Import needed for request models
from ....services.llm.base_provider import GenerationResponse, EmbeddingResponse, LLMProvider

# --- Pydantic Models for API --- 

class LLMBaseConfig(BaseModel):
    """Base configuration for LLM requests, mirrors parts of LLMConfig."""
    model_name: Optional[str] = None # Allow override, else use provider default
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, gt=0)
    stop_sequences: Optional[List[str]] = Field(None, max_items=5)
    safety_settings: Optional[List[SafetySetting]] = None
    # Add other relevant config overrides here

class GenerateRequest(LLMBaseConfig):
    prompt: str
    provider: Optional[str] = "google" # Default to google

class EmbedRequest(LLMBaseConfig):
    texts: Union[str, List[str]]
    provider: Optional[str] = "google"
    embedding_model: Optional[str] = None # Allow specifying embedding model
    task_type: Optional[str] = None # e.g., RETRIEVAL_DOCUMENT, SEMANTIC_SIMILARITY
    title: Optional[str] = None

class ModelInfo(BaseModel):
    """Response model for listing models."""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    input_token_limit: Optional[int] = None
    output_token_limit: Optional[int] = None
    supported_generation_methods: Optional[List[str]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None

# --- Dependency for getting LLM Provider --- 

# This is a simplified dependency. In a real app, config might come 
# from a central config service, environment variables loaded at startup, etc.
# For now, we build a default config, assuming API key is in env.
async def get_llm_provider(provider_name: str = "google", model_name: Optional[str] = None) -> LLMProvider:
    """FastAPI dependency to get an initialized LLM provider."""
    # TODO: Replace with a more robust config loading mechanism
    default_model = model_name or "gemini-1.5-flash-latest" # Or load from central config
    try:
        config = LLMConfig(model_name=default_model) # API key loaded from env by dotenv in main.py
        provider = LLMManager.get_provider(config, provider_name=provider_name)
        return provider
    except (ValueError, ImportError) as e:
        raise HTTPException(status_code=500, detail=f"LLM Provider Initialization Error: {e}")
    except Exception as e:
        # Catch-all for unexpected errors during init
        raise HTTPException(status_code=500, detail=f"Unexpected LLM Error: {type(e).__name__} - {e}")

# --- Router --- 

router = APIRouter()

@router.post("/generate", response_model=GenerationResponse)
async def generate_text(
    request: GenerateRequest,
    provider: LLMProvider = Depends(lambda req: get_llm_provider(req.provider, req.model_name), use_cache=False) # Pass provider/model
):
    """
    Generates text based on a prompt using the specified provider.
    """
    try:
        # Pass relevant config overrides from request to provider method
        # The provider's internal config is used as default
        kwargs = request.model_dump(exclude={"prompt", "provider"}, exclude_none=True)
        response = await provider.generate(prompt=request.prompt, **kwargs)
        return response
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch provider-specific errors or unexpected issues
        raise HTTPException(status_code=500, detail=f"Generation Error: {type(e).__name__} - {e}")

@router.post("/generate-stream")
async def generate_text_stream(
    request: GenerateRequest,
    provider: LLMProvider = Depends(lambda req: get_llm_provider(req.provider, req.model_name), use_cache=False)
):
    """
    Generates text based on a prompt, streaming the response.
    """
    async def stream_generator():
        try:
            kwargs = request.model_dump(exclude={"prompt", "provider"}, exclude_none=True)
            async for chunk in provider.generate_stream(prompt=request.prompt, **kwargs):
                # Stream each validated GenerationResponse chunk as JSON line
                yield chunk.model_dump_json() + "\n" 
        except (ValueError, KeyError) as e:
            # Log error details
            print(f"Stream Error (Bad Request): {e}")
            # Need a way to signal error mid-stream if possible, otherwise client might timeout
            # Yielding an error object might be an option
            yield json.dumps({"error": str(e), "status_code": 400}) + "\n"
        except Exception as e:
            print(f"Stream Error (Server): {type(e).__name__} - {e}")
            yield json.dumps({"error": f"{type(e).__name__} - {e}", "status_code": 500}) + "\n"

    # Use StreamingResponse with a generator
    # Media type text/event-stream is also common for Server-Sent Events
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson") 

@router.post("/embed", response_model=EmbeddingResponse)
async def embed_texts(
    request: EmbedRequest,
    provider: LLMProvider = Depends(lambda req: get_llm_provider(req.provider, req.model_name), use_cache=False)
):
    """
    Generates embeddings for the provided text(s).
    """
    try:
        kwargs = request.model_dump(exclude={"texts", "provider"}, exclude_none=True)
        response = await provider.embed(texts=request.texts, **kwargs)
        return response
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding Error: {type(e).__name__} - {e}")

@router.get("/models", response_model=List[ModelInfo])
async def list_llm_models(
    provider_name: Optional[str] = "google", # Allow querying specific provider
    provider_dep: LLMProvider = Depends(lambda provider_name: get_llm_provider(provider_name), use_cache=False)
):
    """
    Lists available models for the specified provider.
    """
    try:
        models = await provider_dep.list_models()
        # Validate the structure against ModelInfo (optional but good practice)
        # validated_models = [ModelInfo(**model) for model in models]
        # return validated_models
        return models # Return raw list for now
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model Listing Error: {type(e).__name__} - {e}") 
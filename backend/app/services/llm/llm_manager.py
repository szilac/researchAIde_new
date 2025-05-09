"""
LLM Manager Factory

This module provides a factory class (`LLMManager`) to instantiate 
and return the appropriate LLM provider based on configuration.
"""

import os
import asyncio
from typing import Optional, Dict, Type

from app.models.llm_config import LLMConfig
from .base_provider import LLMProvider
from .google_provider import GoogleProvider
# Import other providers here as they are added
# from .anthropic_provider import AnthropicProvider
# from .openai_provider import OpenAIProvider

class LLMManager:
    """
    Factory class for creating LLM provider instances.
    """

    _providers: Dict[str, Type[LLMProvider]] = {
        "google": GoogleProvider,
        # "anthropic": AnthropicProvider, # Example for future providers
        # "openai": OpenAIProvider,      # Example for future providers
    }


    @classmethod
    def get_provider(cls, config: LLMConfig, provider_name: Optional[str] = "google") -> LLMProvider:
        """
        Gets an instance of the specified LLM provider.

        Args:
            config: The LLM configuration object (LLMConfig Pydantic model).
            provider_name: The name of the provider to instantiate (e.g., 'google'). 
                           Defaults to 'google'. This could also be derived from config 
                           if the config model included a provider field.

        Returns:
            An instance of the requested LLMProvider.

        Raises:
            ValueError: If the specified provider_name is not supported.
        """
        
        # Determine the provider key (case-insensitive check)
        provider_key = provider_name.lower() if provider_name else "google" 

        if provider_key not in cls._providers:
            raise ValueError(f"Unsupported LLM provider: '{provider_name}'. Supported providers: {list(cls._providers.keys())}")

        provider_class = cls._providers[provider_key]

        # Simple instantiation for now. 
        # Could add caching based on config hash later if needed.
        # config_tuple = tuple(sorted(config.dict().items())) # Example for caching key
        # if config_tuple not in cls._instances:
        #     cls._instances[config_tuple] = provider_class(config=config)
        # return cls._instances[config_tuple]

        try:
            instance = provider_class(config=config)
            print(f"Successfully instantiated LLM provider: {provider_key}")
            return instance
        except Exception as e:
            print(f"Error instantiating LLM provider '{provider_key}': {e}")
            # Re-raise the exception to be handled upstream
            raise

# --- Example Usage --- 
# Note: This block will only run if the script is executed directly (`python llm_manager.py`).
# Ensure GOOGLE_API_KEY environment variable is set for this example to run fully.
async def _run_example_provider_calls(provider: LLMProvider):
    """Internal async function to run example provider calls."""
    if not provider:
        print("Provider instance is None, skipping example calls.")
        return

    try:
        print("\n--- Testing Generation ---")
        response = await provider.generate("Explain the theory of relativity in simple terms.")
        print(f"Generation response: {response.text[:150]}...") # Truncate long responses
        
        print("\n--- Testing Model Listing ---")
        models = await provider.list_models()
        print(f"Available models (first 3): {models[:3]}")
            
        print("\n--- Testing Token Counting ---")
        tokens = await provider.count_tokens("How many tokens are in this specific sentence?")
        print(f"Token count: {tokens}")

        print("\n--- Testing Embedding ---")
        # Use a model known for embedding if needed, or rely on provider default
        embeddings = await provider.embed("This is a sample text for embedding.")
        print(f"Embeddings received (shape: 1x{len(embeddings.embeddings[0])}). First 5 dims: {embeddings.embeddings[0][:5]}...") 
        
        # Example of streaming (uncomment to test)
        # print("\n--- Testing Streaming Generation ---")
        # async for chunk in provider.generate_stream("Tell me a short story about a curious robot."):
        #     print(chunk.text, end="", flush=True)
        # print("\n--- End of Stream ---")
            
    except Exception as e:
        print(f"\nError during provider example calls: {e}")

if __name__ == "__main__":
    print("--- Running LLMManager Example --- ")
    # Ensure API key is available for the example to run
    api_key_from_env = os.getenv("GOOGLE_API_KEY")
    if not api_key_from_env:
        print("Warning: GOOGLE_API_KEY environment variable not set. Example usage will likely fail functional tests.")
        # Use a placeholder for basic instantiation testing
        api_key_from_env = "YOUR_PLACEHOLDER_API_KEY"

    # Define sample configuration data
    sample_config_data = {
        "model_name": "gemini-1.5-flash-001", # Ensure this model exists
        "api_key": api_key_from_env 
        # Add other config fields like temperature if needed
    }

    google_provider_instance = None
    try:
        print("Instantiating LLMConfig...")
        llm_config = LLMConfig(**sample_config_data)
        
        print("Getting Google provider instance via LLMManager...")
        google_provider_instance = LLMManager.get_provider(llm_config, provider_name="google")

        print("\nRunning example provider usage (async)...")
        # Run the async example function using asyncio.run
        asyncio.run(_run_example_provider_calls(google_provider_instance))

    except ValueError as e:
        print(f"\nERROR: Configuration or Provider error: {e}")
    except ImportError as e:
        print(f"\nERROR: Import error (likely missing 'google-generativeai' library): {e}")
    except Exception as e:
        # Catch potential API errors during instantiation or calls
        print(f"\nERROR: An unexpected error occurred: {type(e).__name__} - {e}")

    print("\n--- LLMManager Example Finished --- ") 
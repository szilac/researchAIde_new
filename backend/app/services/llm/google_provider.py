"""
Concrete implementation of the LLMProvider for Google Gemini API.
"""

import os
from typing import Any, Dict, List, Optional, AsyncGenerator, Union, TYPE_CHECKING
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
import asyncio
import hashlib
import json
import logging

# Import types only for type checking
if TYPE_CHECKING:
    from google.generativeai.types import GenerateContentResponse, GenerationConfig, SafetySettingDict, Model, EmbeddingDict
    # We might need these for the exception types in hints if used, but RetryableGoogleErrors uses runtime check
    # from google.api_core.exceptions import GoogleAPICallError, ClientError

# Attempt to import google.generativeai for runtime, handle gracefully
try:
    import google.generativeai as genai
    # Import runtime exceptions
    from google.api_core.exceptions import GoogleAPICallError, ClientError
    _GOOGLE_GENAI_INSTALLED = True
    # Define actual retryable errors if library is installed
    RetryableGoogleErrors = (GoogleAPICallError, ClientError, TimeoutError) # Add specific Google errors like ServiceUnavailable, DeadlineExceeded if they exist
    from google.generativeai.types import GenerationConfig, SafetySettingDict # Added SafetySettingDict here
except ImportError:
    _GOOGLE_GENAI_INSTALLED = False
    # Define placeholders for runtime checks/logic if needed, though primary use is type hints
    # The TYPE_CHECKING block handles the type hints themselves.
    # If runtime checks like isinstance(e, GoogleAPICallError) are needed, define dummy exceptions.
    GoogleAPICallError = ConnectionError # Use ConnectionError as fallback for GoogleAPICallError
    ClientError = ConnectionError # Use ConnectionError as fallback for ClientError
    # Define runtime fallback for RetryableGoogleErrors tuple, including TimeoutError and our fallbacks
    RetryableGoogleErrors = (ConnectionError, TimeoutError) # Use the fallback exception types + TimeoutError
    print("Warning: 'google-generativeai' library not found. GoogleProvider will not function.")

from app.models.llm_config import LLMConfig, SafetySetting
from .base_provider import LLMProvider, GenerationResponse, EmbeddingResponse

# Dynamically define retryable errors based on library availability
if _GOOGLE_GENAI_INSTALLED:
    # Use actual Google exceptions if library is installed
    ActualRetryableErrors = (GoogleAPICallError, ClientError, TimeoutError) # Add others as needed
else:
    # Use fallback exceptions (like ConnectionError) if library is not installed
    ActualRetryableErrors = (ConnectionError, TimeoutError) # Match test env

# Default retry configuration using the dynamically set errors
DEFAULT_RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=10),
    "retry": retry_if_exception_type(ActualRetryableErrors)
}

class GoogleProvider(LLMProvider):
    """
    LLMProvider implementation for Google Gemini API.
    Includes basic retry logic and response validation.
    Includes a simple in-memory cache.
    """
    # RETRY_CONFIG = None # Removed class variable

    def __init__(self, config: LLMConfig):
        if not _GOOGLE_GENAI_INSTALLED:
            raise ImportError(
                "google-generativeai library is required for GoogleProvider. "
                "Please install it using `pip install google-generativeai`."
            )

        # Removed dynamic config from init
        # if GoogleProvider.RETRY_CONFIG is None:
        #     if _GOOGLE_GENAI_INSTALLED:
        #         ActualRetryableErrors = (GoogleAPICallError, ClientError, TimeoutError)
        #     else:
        #         ActualRetryableErrors = (ConnectionError, TimeoutError)
        #     GoogleProvider.RETRY_CONFIG = {
        #          "stop": stop_after_attempt(3),
        #          "wait": wait_exponential(multiplier=1, min=2, max=10),
        #          "retry": retry_if_exception_type(ActualRetryableErrors)
        #      }
        #     print(f"Retry configured for exceptions: {ActualRetryableErrors}")

        self.client = None # Initialized in _initialize_client
        self.generative_model = None # Initialized after client
        self._cache: Dict[str, Union[GenerationResponse, EmbeddingResponse]] = {} # In-memory cache
        super().__init__(config)

    def _initialize_client(self) -> None:
        """Initializes the Google Generative AI client."""
        api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API Key must be provided either in config or as GOOGLE_API_KEY environment variable.")
        
        try:
            genai.configure(api_key=api_key)
            # Store the configured client or reference if needed, though genai often uses module-level config
            self.client = genai # Placeholder, direct client object might not be stored this way
            self.generative_model = genai.GenerativeModel(self.config.model_name)
            print(f"Google GenAI client configured for model: {self.config.model_name}")
        except Exception as e:
            print(f"Error configuring Google GenAI client: {e}")
            raise

    def _prepare_generation_config(self, **kwargs) -> GenerationConfig:
        """Prepares the GenerationConfig dictionary from LLMConfig and kwargs."""
        config_dict = {
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_output_tokens": kwargs.get("max_output_tokens", self.config.max_output_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "top_k": kwargs.get("top_k", self.config.top_k),
            "stop_sequences": kwargs.get("stop_sequences", self.config.stop_sequences),
        }
        filtered_config = {k: v for k, v in config_dict.items() if v is not None}
        # Only construct GenerationConfig if the library is installed
        if _GOOGLE_GENAI_INSTALLED:
             # Runtime check passed, use actual genai type if available
             # Note: Type checker sees GenerationConfig from TYPE_CHECKING block
             return genai.types.GenerationConfig(**filtered_config) if hasattr(genai, 'types') else GenerationConfig(**filtered_config) # Defensive runtime access
        else:
             # Library not installed, return dict. Type checker still expects GenerationConfig.
             # This might require # type: ignore[return-value] if strict.
             return filtered_config # type: ignore[return-value]
    
    def _prepare_safety_settings(self, **kwargs) -> Optional[List[SafetySettingDict]]:
        """Prepares the safety settings list."""
        safety_settings_config = kwargs.get("safety_settings", self.config.safety_settings)
        if safety_settings_config and _GOOGLE_GENAI_INSTALLED:
            # Convert Pydantic models to dictionaries expected by the API
            # Runtime check passed, use actual genai type if available
            # Note: Type checker sees SafetySettingDict from TYPE_CHECKING block
            ActualSafetySettingDict = getattr(genai.types, 'SafetySettingDict', dict) # Defensive runtime access
            return [
                ActualSafetySettingDict(category=s.category.value, threshold=s.threshold.value)
                for s in safety_settings_config
            ]
        # Return list of dicts if lib not installed but config provided, or None
        elif safety_settings_config:
             # Library not installed. Type checker expects List[SafetySettingDict], but we return List[Dict].
             # This might require # type: ignore[return-value] if strict.
             return [s.model_dump() for s in safety_settings_config] # type: ignore[return-value]
        return None

    def _generate_cache_key(self, method: str, **kwargs) -> str:
        """Generates a consistent cache key based on method and inputs."""
        # Create a dictionary of relevant arguments
        key_data = {
            "method": method,
            "model_name": self.config.model_name, 
        }
        
        # Add method-specific arguments
        if method == "generate" or method == "generate_stream":
            key_data["prompt"] = kwargs.get("prompt")
            # Include relevant generation parameters that affect output
            gen_config = self._prepare_generation_config(**kwargs)
            # Convert GenerationConfig object to a dictionary before updating
            if hasattr(gen_config, '__dict__'): # Check if it's an object we can vars()
                gen_config_dict = vars(gen_config)
            elif isinstance(gen_config, dict): # It might already be a dict if lib not installed
                gen_config_dict = gen_config
            else:
                gen_config_dict = {} # Fallback to empty dict
                print(f"Warning: Could not convert gen_config ({type(gen_config)}) to dict for cache key.")
            key_data.update(gen_config_dict) # Add temp, tokens, top_p, top_k, stop_seq
        elif method == "embed":
            key_data["texts"] = tuple(sorted(kwargs.get("texts", []))) # Sort list for consistency
            key_data["embedding_model"] = kwargs.get("embedding_model", "models/text-embedding-004")
            key_data["task_type"] = kwargs.get("task_type", "RETRIEVAL_DOCUMENT")
            key_data["title"] = kwargs.get("title")
        # Add other methods as needed

        # Convert to a JSON string (sorted for consistency) and hash it
        # Using json ensures complex types like lists/dicts are handled
        try:
            serialized_data = json.dumps(key_data, sort_keys=True)
            return hashlib.sha256(serialized_data.encode('utf-8')).hexdigest()
        except TypeError as e:
             print(f"Warning: Could not serialize cache key data: {e}. Caching might be ineffective.")
             # Fallback: Use a simpler key or skip caching for this call
             return f"{method}_{kwargs.get('prompt', '')[:50]}_{hash(str(kwargs))}" # Less reliable fallback

    # Use the globally defined default retry settings
    @retry(**DEFAULT_RETRY_CONFIG)
    async def generate(self, prompt: str, **kwargs) -> GenerationResponse:
        """Generates text using the configured Gemini model with cache, retry, and validation."""
        # Check cache first
        cache_key_params = {"prompt": prompt, **kwargs}
        cache_key = self._generate_cache_key("generate", **cache_key_params)
        if cache_key in self._cache:
            print(f"Cache hit for generate: {cache_key[:10]}...")
            cached_response = self._cache[cache_key]
            if isinstance(cached_response, GenerationResponse):
                 return cached_response
            else:
                 # Handle unexpected type in cache (shouldn't happen with proper usage)
                 print(f"Warning: Cache contained unexpected type for key {cache_key}. Fetching fresh data.")
                 del self._cache[cache_key] # Remove invalid entry

        print(f"Cache miss for generate: {cache_key[:10]}...")
        if not self.generative_model:
            raise RuntimeError("Google GenAI client not initialized properly.")

        generation_config = self._prepare_generation_config(**kwargs)
        safety_settings = self._prepare_safety_settings(**kwargs)
        
        response_text = "" # Default value
        token_usage = None
        finish_reason = None
        
        try:
            # Actual API call
            # Use string for type hint here if GenerateContentResponse is only in TYPE_CHECKING
            api_response: "GenerateContentResponse" = await self.generative_model.generate_content_async(
                contents=prompt,
                generation_config=generation_config, # This is now potentially a dict or GenerationConfig
                safety_settings=safety_settings, # This is now potentially None, List[Dict], or List[SafetySettingDict]
            )
            
            # --- Data Extraction --- 
            if hasattr(api_response, 'usage_metadata') and api_response.usage_metadata:
                token_usage = {
                    "prompt_tokens": getattr(api_response.usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(api_response.usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(api_response.usage_metadata, 'total_token_count', 0)
                }
            
            if api_response.candidates and hasattr(api_response.candidates[0], 'finish_reason'):
                 # Ensure we extract the name attribute string
                 extracted_reason = api_response.candidates[0].finish_reason
                 finish_reason_str = getattr(extracted_reason, 'name', None) # Get .name if exists
                 if finish_reason_str:
                    finish_reason = finish_reason_str # Assign the string
                 else:
                    # Handle case where .name is missing or finish_reason itself is None/unexpected
                    print(f"Warning: Could not extract finish_reason name. Got: {extracted_reason}")
                    finish_reason = None # Or some default error string?

            try:
                response_text = api_response.text
            except ValueError:
                 if hasattr(api_response, 'prompt_feedback') and api_response.prompt_feedback:
                     # Ensure we extract the name attribute string here too
                     extracted_block_reason = api_response.prompt_feedback.block_reason
                     finish_reason_str = getattr(extracted_block_reason, 'name', None)
                     if finish_reason_str:
                         finish_reason = f"BLOCKED:{finish_reason_str}"
                     else:
                         print(f"Warning: Could not extract block_reason name. Got: {extracted_block_reason}")
                         finish_reason = "BLOCKED:UNKNOWN_REASON"
                 else:
                     finish_reason = "BLOCKED:UNKNOWN_REASON"
                 print(f"Content generation possibly blocked. Reason: {finish_reason}")
            except AttributeError:
                 print("Warning: Response object does not contain .text attribute.")
                 finish_reason = finish_reason or "ERROR:MISSING_TEXT"

            # --- Pydantic Validation --- 
            try:
                validated_response = GenerationResponse(
                    text=response_text,
                    token_usage=token_usage,
                    finish_reason=finish_reason
                )
                # Store in cache on success
                self._cache[cache_key] = validated_response
                print(f"Stored in cache: {cache_key[:10]}...")
                return validated_response
            except ValidationError as ve:
                print(f"Pydantic validation failed for GenerationResponse: {ve}")
                raise ValueError(f"Failed to validate generation response: {ve}")

        except RetryableGoogleErrors as e:
             print(f"Google GenAI generation failed after retries: {e}")
             raise 
        except Exception as e:
            print(f"Non-retryable error during Google GenAI generation: {e}")
            raise

    # Use the globally defined default retry settings
    @retry(**DEFAULT_RETRY_CONFIG)
    async def _start_generate_stream(self, prompt: str, generation_config, safety_settings):
         """Helper to initiate the stream, wrapped by retry."""
         return self.generative_model.generate_content_async(
                contents=prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True,
            )

    async def generate_stream(
        self, prompt: str, **kwargs
    ) -> AsyncGenerator[GenerationResponse, None]:
        """Generates text stream, yielding GenerationResponse objects with accumulating data."""
        if not self.generative_model:
            raise RuntimeError("Google GenAI client not initialized properly.")

        generation_config = self._prepare_generation_config(**kwargs)
        safety_settings = self._prepare_safety_settings(**kwargs)

        stream = None
        try:
            stream = await self._start_generate_stream(prompt, generation_config, safety_settings)
        except RetryableGoogleErrors as e:
             print(f"Google GenAI streaming failed after retries on initial call: {e}")
             raise
        except Exception as e:
            print(f"Error starting Google GenAI stream: {e}")
            raise

        accumulated_response = GenerationResponse(text="") # Initialize empty response
        final_chunk_processed = False
        try:
            async for chunk in stream:
                final_chunk_processed = True # Mark that we received at least one chunk
                chunk_text = ""
                chunk_finish_reason = None
                chunk_token_usage = None 
                is_final_chunk = False # Flag to indicate if this chunk has final metadata

                # --- Extract Text --- 
                try:
                     chunk_text = chunk.text
                except (ValueError, AttributeError) as chunk_err:
                     print(f"Warning: Could not extract text from stream chunk: {chunk_err}")
                     # Continue processing chunk for metadata even if text extraction fails

                # --- Extract Metadata (Tokens, Finish Reason) --- 
                # Check for token usage metadata (usually appears at the end)
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    is_final_chunk = True
                    chunk_token_usage = {
                        "prompt_tokens": getattr(chunk.usage_metadata, 'prompt_token_count', 0),
                        "completion_tokens": getattr(chunk.usage_metadata, 'candidates_token_count', 0),
                        "total_tokens": getattr(chunk.usage_metadata, 'total_token_count', 0)
                    }
                    accumulated_response.token_usage = chunk_token_usage # Update final token count
                    print(f"Stream received final token usage: {chunk_token_usage}")

                # Check for finish reason (also usually at the end or if blocked)
                if chunk.candidates and hasattr(chunk.candidates[0], 'finish_reason'):
                    is_final_chunk = True
                    chunk_finish_reason = chunk.candidates[0].finish_reason.name 
                    accumulated_response.finish_reason = chunk_finish_reason # Update final reason
                    print(f"Stream received finish reason: {chunk_finish_reason}")
                
                # Check for blocking reasons
                if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                     is_final_chunk = True # Blocking usually terminates the stream
                     chunk_finish_reason = f"BLOCKED:{chunk.prompt_feedback.block_reason.name}"
                     accumulated_response.finish_reason = chunk_finish_reason
                     print(f"Stream possibly blocked. Reason: {chunk_finish_reason}")
                     # Yield this final status chunk and break
                     # yield GenerationResponse(text="", token_usage=accumulated_response.token_usage, finish_reason=chunk_finish_reason)
                     # break
                
                # --- Yield Validated Chunk --- 
                try:
                    # Create response for the *current* chunk
                    current_chunk_response = GenerationResponse(
                        text=chunk_text,
                        # Include metadata only if it appeared in *this* chunk 
                        # (useful for debugging, but might be confusing for consumers)
                        # Alternatively, only yield metadata in the *final* yielded object.
                        token_usage=chunk_token_usage if is_final_chunk else None, 
                        finish_reason=chunk_finish_reason if is_final_chunk else None
                    )
                    yield current_chunk_response
                except ValidationError as ve:
                    print(f"Pydantic validation failed for stream chunk: {ve}")
                    raise ValueError(f"Failed to validate stream chunk: {ve}")
                
                # --- Check if stream finished based on metadata --- 
                if is_final_chunk and chunk_finish_reason:
                     # If we got a definitive finish reason, break the loop
                     break

            # After the loop, if we processed chunks but didn't get a final reason/metadata chunk
            # (e.g., stream ended abruptly), we might yield the accumulated state if needed,
            # but typically the loop finishes naturally when the stream ends.
            # if final_chunk_processed and not accumulated_response.finish_reason:
            #     print("Warning: Stream finished without explicit final metadata chunk.")
            #     accumulated_response.finish_reason = accumulated_response.finish_reason or "STOPPED_UNKNOWN" # Or maybe None? 
            #     # Optionally yield a final status object
            #     # yield accumulated_response 
                
        except Exception as e: # Catch potential errors during iteration too
            print(f"Error during Google GenAI streaming iteration: {e}")
            # Yield a final error state? 
            # yield GenerationResponse(text="", finish_reason=f"ERROR:{type(e).__name__}")
            raise

    # Use the globally defined default retry settings
    @retry(**DEFAULT_RETRY_CONFIG)
    async def embed(self, texts: Union[str, List[str]], **kwargs) -> EmbeddingResponse:
        """Generates embeddings with cache, retry logic and response validation."""
        contents = texts if isinstance(texts, list) else [texts]
        # Check cache first
        cache_key_params = {"texts": contents, **kwargs}
        cache_key = self._generate_cache_key("embed", **cache_key_params)
        if cache_key in self._cache:
            print(f"Cache hit for embed: {cache_key[:10]}...")
            cached_response = self._cache[cache_key]
            if isinstance(cached_response, EmbeddingResponse):
                 return cached_response
            else:
                 print(f"Warning: Cache contained unexpected type for key {cache_key}. Fetching fresh data.")
                 del self._cache[cache_key]

        print(f"Cache miss for embed: {cache_key[:10]}...")
        embedding_model_name = kwargs.get("embedding_model", "models/text-embedding-004")
        task_type = kwargs.get("task_type", "RETRIEVAL_DOCUMENT")
        title = kwargs.get("title")

        embeddings_list = []
        token_usage = None

        try:
            # Actual API call
            # Use string for type hint here if EmbeddingDict is only in TYPE_CHECKING
            api_result: "EmbeddingDict" = await genai.embed_content_async(
                model=embedding_model_name,
                content=contents,
                task_type=task_type,
                title=title,
            )
            
            # --- Data Extraction --- 
            if 'embedding' in api_result and isinstance(api_result['embedding'], list):
                embeddings_list = api_result['embedding']
            else:
                 raise ValueError("Invalid embedding structure in API response")

            token_usage = None # Placeholder

            # --- Pydantic Validation --- 
            try:
                validated_response = EmbeddingResponse(
                    embeddings=embeddings_list,
                    token_usage=token_usage
                )
                # Store in cache on success
                self._cache[cache_key] = validated_response
                print(f"Stored in cache: {cache_key[:10]}...")
                return validated_response
            except ValidationError as ve:
                print(f"Pydantic validation failed for EmbeddingResponse: {ve}")
                raise ValueError(f"Failed to validate embedding response: {ve}")

        except RetryableGoogleErrors as e:
             print(f"Google GenAI embedding failed after retries: {e}")
             raise
        except Exception as e:
            print(f"Non-retryable error during Google GenAI embedding: {e}")
            raise

    # Use the globally defined default retry settings
    @retry(**DEFAULT_RETRY_CONFIG)
    async def count_tokens(self, text: str, **kwargs) -> int:
        """Counts tokens using the configured Gemini model's tokenizer with retry logic."""
        if not self.generative_model:
            raise RuntimeError("Google GenAI client not initialized properly.")
        
        try:
            response = await self.generative_model.count_tokens_async(contents=text)
            return response.total_tokens
        except RetryableGoogleErrors as e:
             print(f"Google GenAI token counting failed after retries: {e}")
             raise
        except Exception as e:
            print(f"Non-retryable error during Google GenAI token counting: {e}")
            raise

    # Use the globally defined default retry settings
    @retry(**DEFAULT_RETRY_CONFIG)
    async def list_models(self, **kwargs) -> List[Dict[str, Any]]:
        """Lists available Gemini models with retry logic and handles sync/async."""
        try:
            # Check if an async version exists (assuming a naming convention)
            if hasattr(genai, 'list_models_async'):
                # If an async version exists, use it
                models_iterator = await genai.list_models_async(**kwargs) # Pass kwargs if needed
                print("Using async list_models_async")
            else:
                # If only sync version exists, run it in a thread pool executor
                print("Using sync list_models in executor")
                loop = asyncio.get_running_loop()
                # Run the synchronous genai.list_models() in the default executor
                # Ensure kwargs are passed correctly to the sync function if needed
                models_iterator = await loop.run_in_executor(None, lambda: list(genai.list_models(**kwargs))) # Wrap list() if needed for executor
            
            model_list = []
            # The iterator itself might still be sync even if the initial call was async
            # or run in executor. Iteration should generally be quick.
            for model in models_iterator: # Iterate over the result from the executor
                # Use getattr for runtime safety
                supported_methods = getattr(model, 'supported_generation_methods', [])
                # Filter for models supporting content generation
                if 'generateContent' in supported_methods:
                    model_info = {
                        # Use getattr for runtime safety on all model attributes
                        "name": getattr(model, 'name', 'N/A'),
                        "display_name": getattr(model, 'display_name', 'N/A'),
                        "description": getattr(model, 'description', 'N/A'),
                        "input_token_limit": getattr(model, 'input_token_limit', None),
                        "output_token_limit": getattr(model, 'output_token_limit', None),
                        "supported_generation_methods": supported_methods,
                        "temperature": getattr(model, 'temperature', None),
                        "top_p": getattr(model, 'top_p', None),
                        "top_k": getattr(model, 'top_k', None),
                    }
                    model_list.append(model_info)
            return model_list
        except RetryableGoogleErrors as e:
             print(f"Google GenAI model listing failed after retries: {e}")
             raise # Re-raise the caught retryable error
        except Exception as e:
            print(f"Non-retryable error listing Google GenAI models: {e}")
            # Log the full traceback for debugging non-retryable errors
            import traceback
            traceback.print_exc()
            raise # Re-raise the caught non-retryable error 
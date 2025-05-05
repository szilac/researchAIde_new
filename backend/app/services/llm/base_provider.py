"""
Defines the abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from pydantic import BaseModel

from app.models.llm_config import LLMConfig # Assuming LLMConfig is here

class GenerationResponse(BaseModel):
    """Standardized response for text generation."""
    text: str
    token_usage: Optional[Dict[str, int]] = None # e.g., {"prompt_tokens": 10, "completion_tokens": 50}
    finish_reason: Optional[str] = None
    # Add other relevant fields as needed

class EmbeddingResponse(BaseModel):
    """Standardized response for text embeddings."""
    embeddings: List[List[float]]
    token_usage: Optional[Dict[str, int]] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM API providers.
    Ensures a consistent interface across different LLM services.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initializes the specific LLM client based on the config."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> GenerationResponse:
        """
        Generates text based on a prompt.

        Args:
            prompt: The input text prompt.
            **kwargs: Provider-specific arguments (e.g., temperature, max_tokens from config or overrides).

        Returns:
            A standardized GenerationResponse object.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, **kwargs
    ) -> AsyncGenerator[GenerationResponse, None]:
        """
        Generates text based on a prompt, yielding results incrementally.

        Args:
            prompt: The input text prompt.
            **kwargs: Provider-specific arguments.

        Yields:
            Standardized GenerationResponse objects as they become available.
        """
        # Ensure the generator is properly typed
        # This is a placeholder for the abstract method signature
        if False: # pragma: no cover
            yield GenerationResponse(text="", token_usage={}, finish_reason="")
        pass
        
    @abstractmethod
    async def embed(self, texts: Union[str, List[str]], **kwargs) -> EmbeddingResponse:
        """
        Generates embeddings for one or more texts.

        Args:
            texts: A single text or a list of texts to embed.
            **kwargs: Provider-specific arguments (e.g., model name for embedding).

        Returns:
            A standardized EmbeddingResponse object.
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str, **kwargs) -> int:
        """
        Counts the number of tokens for a given text based on the provider's tokenizer.

        Args:
            text: The text to tokenize.
            **kwargs: Provider-specific arguments.
        
        Returns:
            The number of tokens.
        """
        pass

    @abstractmethod
    async def list_models(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Lists available models for the provider.

        Args:
            **kwargs: Provider-specific arguments.

        Returns:
            A list of dictionaries, each representing a model.
        """
        pass 
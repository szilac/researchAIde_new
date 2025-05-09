"""
Defines Pydantic models for LLM configuration, specifically for Google Gemini.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum  # Keep Enum import for placeholder definitions

# LLMProviderType Definition
class LLMProviderType(str, Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Add other providers as needed

# Attempt to import safety enums, handle gracefully if library not installed yet
try:
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    # Define placeholders if google.generativeai is not installed
    print(
        "Warning: 'google-generativeai' library not found. "
        "Using placeholder enums for HarmCategory and HarmBlockThreshold."
    )

    class HarmCategory(Enum):
        HARM_CATEGORY_UNSPECIFIED = "HARM_CATEGORY_UNSPECIFIED"
        HARM_CATEGORY_HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
        HARM_CATEGORY_SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"
        HARM_CATEGORY_HARASSMENT = "HARM_CATEGORY_HARASSMENT"
        HARM_CATEGORY_DANGEROUS_CONTENT = "HARM_CATEGORY_DANGEROUS_CONTENT"

    class HarmBlockThreshold(Enum):
        HARM_BLOCK_THRESHOLD_UNSPECIFIED = "HARM_BLOCK_THRESHOLD_UNSPECIFIED"
        BLOCK_LOW_AND_ABOVE = "BLOCK_LOW_AND_ABOVE"
        BLOCK_MEDIUM_AND_ABOVE = "BLOCK_MEDIUM_AND_ABOVE"
        BLOCK_ONLY_HIGH = "BLOCK_ONLY_HIGH"
        BLOCK_NONE = "BLOCK_NONE"


class SafetySetting(BaseModel):
    """
    Represents a single safety setting rule for content generation.
    """

    category: HarmCategory
    threshold: HarmBlockThreshold

    class Config:
        use_enum_values = True  # Store enum values as strings if passed in/out
        extra = "ignore"  # Ignore extra fields


class LLMConfig(BaseModel):
    """
    Configuration for the LLM provider, specifically tailored for Google Gemini.
    NOTE: This model is currently Google Gemini specific. 
    If other providers are added with different config structures,
    consider a more generic base LLMConfig and provider-specific sub-models.
    """

    api_key: Optional[str] = Field(
        default=None,  # Use default instead of None directly
        description="Google API Key. If None, the provider will attempt to load it from the GOOGLE_API_KEY environment variable.",
    )
    model_name: str = Field(
        default="gemini-1.5-flash",
        description="Name of the specific Gemini model to use (e.g., 'gemini-1.5-pro-002', 'gemini-1.5-flash-001').",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,  # Google allows up to 2.0 for some models
        description="Controls randomness (0.0-2.0). Lower values are more deterministic. Defaults vary by model.",
    )
    max_output_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum number of tokens to generate in the response.",
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter. Cumulative probability cutoff for token selection.",
    )
    top_k: Optional[int] = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter. Limits selection to top K probable tokens.",
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        max_items=5,  # Add constraint based on docs
        description="Sequences where the model should stop generating. Max 5 sequences.",
    )
    safety_settings: Optional[List[SafetySetting]] = Field(
        default=None,
        description="List of safety settings to apply, overriding defaults.",
    )

    class Config:
        extra = "ignore"  # Ignore extra fields if provided during instantiation
        use_enum_values = True  # Store enum values as strings if passed in/out 
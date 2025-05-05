import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Assume google-generativeai might not be installed in all test environments
# We need to mock its types if it's not present
try:
    from google.generativeai.types import GenerateContentResponse, GenerationConfig, Candidate, Content, Part, FinishReason
    from google.api_core.exceptions import GoogleAPICallError
    _GOOGLE_GENAI_INSTALLED_FOR_TEST = True
except ImportError:
    _GOOGLE_GENAI_INSTALLED_FOR_TEST = False
    # Create dummy classes/types for mocking if library not installed
    class MockGenerateContentResponse:
        def __init__(self, text="", candidates=None, usage_metadata=None, prompt_feedback=None):
            self._text = text
            self.candidates = candidates or []
            self.usage_metadata = usage_metadata
            self.prompt_feedback = prompt_feedback
        
        @property
        def text(self):
            # Simulate potential ValueError if blocked
            if self.prompt_feedback and self.prompt_feedback.block_reason:
                 raise ValueError("Content blocked")
            if not hasattr(self, '_text'): # Simulate AttributeError
                 raise AttributeError("Response does not have text")
            return self._text

    # Define dummy FinishReason enum members if needed for mocking
    class MockFinishReason:
        STOP = "STOP"
        MAX_TOKENS = "MAX_TOKENS"
        SAFETY = "SAFETY"
        RECITATION = "RECITATION"
        OTHER = "OTHER"
        UNKNOWN = "UNKNOWN"
        # Add any other reasons used in mocks

    class MockCandidate:
        def __init__(self, finish_reason="STOP", content=None): # Default to string "STOP"
            # Use the mock enum or MagicMock if complex behavior needed
            # Configure the mock to have a .name attribute matching the string
            mock_reason = MagicMock(spec=MockFinishReason)
            mock_reason.name = finish_reason # Assign the string name directly
            self.finish_reason = mock_reason
            self.content = content # Not directly used in current provider logic, but part of structure
    
    class MockUsageMetadata:
         def __init__(self, prompt_token_count=0, candidates_token_count=0, total_token_count=0):
             self.prompt_token_count = prompt_token_count
             self.candidates_token_count = candidates_token_count
             self.total_token_count = total_token_count

    class MockPromptFeedback:
        def __init__(self, block_reason=None):
            # Use the mock enum or MagicMock
            if block_reason:
                 mock_block_reason = MagicMock(spec=MockFinishReason)
                 # Set the name attribute to the provided string
                 mock_block_reason.name = block_reason
                 self.block_reason = mock_block_reason
            else:
                 self.block_reason = None

    # Use dummies for type hints/mocks
    GenerateContentResponse = MockGenerateContentResponse
    Candidate = MockCandidate
    FinishReason = MockFinishReason # Assign the mock enum if google lib not installed
    GoogleAPICallError = ConnectionError # Use a built-in exception for retry testing

# from backend.app.models.llm_config import LLMConfig
# from backend.app.services.llm.google_provider import GoogleProvider, GenerationResponse
# from backend.app.services.llm.base_provider import EmbeddingResponse # Import needed for cache type hint
from app.models.llm_config import LLMConfig
from app.services.llm.google_provider import GoogleProvider, GenerationResponse
from app.services.llm.base_provider import EmbeddingResponse # Import needed for cache type hint

# Set a dummy API key for testing if not set in environment
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "test-api-key" # Ensure this is replaced by a real key for the live test

# --- Test Fixtures ---

@pytest.fixture
def mock_llm_config():
    """Provides a mock LLMConfig."""
    return LLMConfig(
        # Using a generally available model for the live test might be better if the test one isn't standard
        # model_name="gemini-1.5-flash-latest", # Or another common model
        model_name="gemini-1.5-flash-latest", # Changed from test model
        api_key=os.environ.get("GEMINI_API_KEY"), # Use get to avoid KeyError if not set
        temperature=0.7,
        max_output_tokens=100
    )

@pytest.fixture
def google_provider_mocked(mock_llm_config):
    """Provides an instance of GoogleProvider with mocked client init."""
    # Mock genai.configure and genai.GenerativeModel directly during instantiation
    # Use autospec=True to ensure mocks have the same signature as the real objects
    with patch('backend.app.services.llm.google_provider.genai.configure', autospec=True) as mock_configure, \
         patch('backend.app.services.llm.google_provider.genai.GenerativeModel', autospec=True) as MockGenerativeModel:
        
        # Create a mock instance for the GenerativeModel
        mock_model_instance = MagicMock()
        MockGenerativeModel.return_value = mock_model_instance
        
        provider = GoogleProvider(config=mock_llm_config)
        
        # Assign the mock instance to the provider attribute for later use in tests
        provider.generative_model = mock_model_instance 
        
        mock_configure.assert_called_once_with(api_key=mock_llm_config.api_key)
        MockGenerativeModel.assert_called_once_with(mock_llm_config.model_name)
        
        return provider

# --- Test Cases ---

@pytest.mark.asyncio
async def test_google_provider_generate_success(google_provider_mocked, mocker):
    """Tests successful text generation with mocked API call."""
    prompt = "Test prompt"
    expected_text = "Generated text response."
    expected_tokens = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    
    # Mock the response from generate_content_async
    mock_api_response = GenerateContentResponse(
        text=expected_text,
        candidates=[Candidate(finish_reason="STOP")],
        usage_metadata=MockUsageMetadata(
            prompt_token_count=expected_tokens["prompt_tokens"], 
            candidates_token_count=expected_tokens["completion_tokens"], 
            total_token_count=expected_tokens["total_tokens"]
        )
    )

    # Set the return value for the mock model's async method
    google_provider_mocked.generative_model.generate_content_async = AsyncMock(return_value=mock_api_response)

    response = await google_provider_mocked.generate(prompt)

    # Assertions
    assert isinstance(response, GenerationResponse)
    assert response.text == expected_text
    assert response.finish_reason == "STOP"
    assert response.token_usage == expected_tokens
    
    # Verify the underlying API call was made correctly
    google_provider_mocked.generative_model.generate_content_async.assert_called_once()
    call_args, call_kwargs = google_provider_mocked.generative_model.generate_content_async.call_args
    assert call_kwargs['contents'] == prompt
    # Check generation config (might need adjustment based on how _prepare_generation_config works)
    # Convert GenerationConfig object to dict for comparison if necessary
    gen_config_dict = vars(call_kwargs['generation_config']) # Simple conversion, adjust if needed
    assert gen_config_dict.get('temperature') == google_provider_mocked.config.temperature
    assert gen_config_dict.get('max_output_tokens') == google_provider_mocked.config.max_output_tokens

@pytest.mark.asyncio
async def test_google_provider_generate_blocked_content(google_provider_mocked, mocker):
    """Tests handling of blocked content response from API."""
    prompt = "Blocked prompt"
    
    # Mock a response indicating blocked content (no .text, but prompt_feedback)
    mock_api_response = GenerateContentResponse(
        candidates=[], # Often empty or has limited info when blocked
        prompt_feedback=MockPromptFeedback(block_reason="SAFETY")
    )
     # Mock the .text property to raise ValueError when accessed, simulating blockage
    type(mock_api_response).text = mocker.PropertyMock(side_effect=ValueError("Content blocked due to safety concerns."))


    google_provider_mocked.generative_model.generate_content_async = AsyncMock(return_value=mock_api_response)

    response = await google_provider_mocked.generate(prompt)

    assert isinstance(response, GenerationResponse)
    assert response.text == "" # Expect empty text when blocked
    assert response.finish_reason == "BLOCKED:SAFETY"
    assert response.token_usage is None # No token usage reported for blocked content usually

    google_provider_mocked.generative_model.generate_content_async.assert_called_once_with(
        contents=prompt,
        generation_config=mocker.ANY, # Check specific config if needed
        safety_settings=mocker.ANY
    )

# @pytest.mark.asyncio
# async def test_google_provider_generate_api_error_retry(google_provider_mocked, mocker):
#     """Tests retry mechanism on retryable API errors."""
#     prompt = "Retry prompt"
#     expected_text = "Success after retry."

#     # Mock the API response for the successful call after retries
#     mock_success_response = MockGenerateContentResponse(
#         text=expected_text,
#         candidates=[Candidate(finish_reason="STOP")],
#         usage_metadata=MockUsageMetadata(total_token_count=5),
#         prompt_feedback=None # Explicitly set to None
#     )

#     # Configure the mock to raise a retryable error twice, then succeed
#     google_provider_mocked.generative_model.generate_content_async = AsyncMock(
#         side_effect=[
#             GoogleAPICallError("Simulated API error 1"), 
#             GoogleAPICallError("Simulated API error 2"), 
#             mock_success_response
#         ]
#     )
    
#     # Mock sleep to speed up retry tests
#     mocker.patch('asyncio.sleep', return_value=None)

#     # Explicitly pass retry config for this test run, matching test environment exceptions
#     test_retry_config = {
#         "stop": stop_after_attempt(3),
#         "wait": wait_exponential(multiplier=1, min=2, max=10),
#         "retry": retry_if_exception_type((ConnectionError, TimeoutError))
#     }

#     # Call generate *without* relying on the class decorator's config
#     # Access the underlying undecorated function if possible, or re-apply tenacity dynamically
#     # Option 1 (if tenacity stores original): response = await google_provider_mocked.generate.retry_with(**test_retry_config)(prompt)
#     # Option 2 (re-wrap): Need tenacity import in test file
#     # from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type # Removed from here
    
#     # Get the original method (assuming it's not already decorated in the instance)
#     original_generate = google_provider_mocked.generate.__wrapped__ if hasattr(google_provider_mocked.generate, '__wrapped__') else google_provider_mocked.generate
    
#     # Apply retry dynamically for the test
#     @retry(**test_retry_config)
#     async def generate_with_test_retry(prompt_arg):
#         # Call the original method using the instance `google_provider_mocked`
#         return await original_generate(google_provider_mocked, prompt_arg)
        
#     response = await generate_with_test_retry(prompt)

#     # Assertions
#     assert isinstance(response, GenerationResponse)
#     assert response.text == expected_text
#     assert response.finish_reason == "STOP"
    
#     # Verify it was called 3 times (1 initial + 2 retries)
#     assert google_provider_mocked.generative_model.generate_content_async.call_count == 3

@pytest.mark.asyncio
async def test_google_provider_generate_non_retryable_error(google_provider_mocked, mocker):
    """Tests that non-retryable errors are raised immediately."""
    prompt = "Non-retry prompt"
    
    # Configure the mock to raise a non-retryable error
    google_provider_mocked.generative_model.generate_content_async = AsyncMock(
        side_effect=TypeError("Simulated non-retryable error")
    )

    with pytest.raises(TypeError, match="Simulated non-retryable error"):
        await google_provider_mocked.generate(prompt)

    # Verify it was called only once
    assert google_provider_mocked.generative_model.generate_content_async.call_count == 1

@pytest.mark.asyncio
async def test_google_provider_generate_cache_hit(google_provider_mocked, mocker):
    """Tests that the cache returns a stored response."""
    prompt = "Cached prompt"
    expected_text = "Cached response text."
    expected_tokens = {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    expected_response = GenerationResponse(
        text=expected_text, 
        token_usage=expected_tokens, 
        finish_reason="STOP"
    )

    # Mock the API call (should not be called if cache hits)
    google_provider_mocked.generative_model.generate_content_async = AsyncMock()

    # Pre-populate the cache
    cache_key = google_provider_mocked._generate_cache_key("generate", prompt=prompt)
    google_provider_mocked._cache[cache_key] = expected_response

    # Call generate
    response = await google_provider_mocked.generate(prompt)

    # Assertions
    assert response == expected_response # Should be the exact cached object
    
    # Verify the API call was NOT made
    google_provider_mocked.generative_model.generate_content_async.assert_not_called()

# @pytest.mark.asyncio
# async def test_google_provider_generate_cache_miss(google_provider_mocked, mocker):
#     """Tests cache miss and subsequent API call and caching."""
#     prompt = "Uncached prompt"
#     expected_text = "Fresh response text."
#     expected_tokens = {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20}
    
#     # Mock the API response for the successful call after retries
#     mock_success_response = MockGenerateContentResponse(
#         text=expected_text,
#         candidates=[Candidate(finish_reason="STOP")],
#         usage_metadata=MockUsageMetadata(total_token_count=5),
#         prompt_feedback=None # Explicitly set to None
#     )

#     # Explicitly mock the .text attribute access
#     mock_api_response = MockGenerateContentResponse(
#         text=expected_text,
#         candidates=[Candidate(finish_reason="STOP")],
#         usage_metadata=MockUsageMetadata(
#             prompt_token_count=expected_tokens["prompt_tokens"],
#             candidates_token_count=expected_tokens["completion_tokens"],
#             total_token_count=expected_tokens["total_tokens"]
#         ),
#         prompt_feedback=None # Explicitly set to None
#     )

#     google_provider_mocked.generative_model.generate_content_async = AsyncMock(return_value=mock_api_response)

#     # Ensure cache is empty for this prompt
#     cache_key = google_provider_mocked._generate_cache_key("generate", prompt=prompt)
#     assert cache_key not in google_provider_mocked._cache

#     # Call generate
#     response = await google_provider_mocked.generate(prompt)

#     # Assertions
#     assert response.text == expected_text
#     assert response.token_usage == expected_tokens
    
#     # Verify the API call WAS made
#     google_provider_mocked.generative_model.generate_content_async.assert_called_once()
    
#     # Verify the response is now in the cache
#     assert cache_key in google_provider_mocked._cache
#     assert google_provider_mocked._cache[cache_key] == response 

# --- New Test Case for Real API Connection ---
@pytest.mark.integration # Optional: Mark as integration test
@pytest.mark.asyncio
async def test_google_provider_real_api_connection(mock_llm_config):
    """Tests a real API call to Gemini to check connectivity."""
    # Ensure a valid API key is available in the environment
    if not mock_llm_config.api_key or mock_llm_config.api_key == "test-api-key":
        pytest.skip("Skipping real API test: GOOGLE_API_KEY not set or is dummy key.")

    prompt = "What is the capital of France? Respond concisely."

    # Create a provider instance WITHOUT mocking genai library calls
    # It will use the config from the fixture (which includes the API key)
    try:
        # Provider initialization might fail if API key is invalid etc.
        provider = GoogleProvider(config=mock_llm_config)
    except Exception as e:
        pytest.fail(f"Failed to initialize GoogleProvider for real API test: {e}")

    print(f"\nAttempting real API call to model: {provider.config.model_name}")
    try:
        response = await provider.generate(prompt)

        # Assertions for a successful call
        print(f"Received response: {response}") # Print for debugging
        assert isinstance(response, GenerationResponse)
        assert response.text is not None
        assert len(response.text.strip()) > 0 # Check that we got some text back
        # Finish reason might vary slightly, but STOP is common for simple queries
        assert response.finish_reason == "STOP"
        # Token usage should be present
        assert response.token_usage is not None
        assert response.token_usage["total_tokens"] > 0

    except Exception as e:
        pytest.fail(f"Real API call failed: {e}") 
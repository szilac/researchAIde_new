# backend/tests/conftest.py
# This file will contain global pytest fixtures.
import pytest
from backend.tests.utils.mock_llm_responses import create_mock_ai_message, create_mock_tool_call
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_simple_ai_response() -> AIMessage:
    """Pytest fixture for a simple mock AIMessage response."""
    return create_mock_ai_message(content="This is a default mock AI response.")

@pytest.fixture
def mock_ai_response_with_tool_call() -> AIMessage:
    """Pytest fixture for a mock AIMessage with a tool call."""
    mock_tool = create_mock_tool_call(name="example_tool", args={"param1": "value1"})
    return create_mock_ai_message(content="", tool_calls=[mock_tool])

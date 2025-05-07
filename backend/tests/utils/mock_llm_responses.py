# backend/tests/utils/mock_llm_responses.py
"""Utilities for generating mock LLM responses for testing."""

from langchain_core.messages import AIMessage, ToolCall
from typing import List, Dict, Any, Optional
import uuid

def create_mock_tool_call(name: str, args: Dict[str, Any], id: Optional[str] = None) -> ToolCall:
    """
    Creates a mock ToolCall object.

    Args:
        name: The name of the tool to be called.
        args: The arguments for the tool call.
        id: Optional ID for the tool call; defaults to a new UUID.

    Returns:
        A ToolCall dictionary.
    """
    return ToolCall(
        name=name,
        args=args,
        id=id if id else f"mock_tool_call_{uuid.uuid4()}"
    )

def create_mock_ai_message(
    content: str,
    tool_calls: Optional[List[ToolCall]] = None,
    id: Optional[str] = None,
    tool_call_chunks: Optional[List[Dict[str, Any]]] = None, # For streaming
) -> AIMessage:
    """
    Creates a mock AIMessage object.

    Args:
        content: The string content of the message.
        tool_calls: An optional list of ToolCall objects.
        id: Optional ID for the AIMessage; defaults to a new UUID.
        tool_call_chunks: Optional list of tool call chunks for streaming simulation.

    Returns:
        An AIMessage instance.
    """
    return AIMessage(
        content=content,
        tool_calls=tool_calls if tool_calls else [],
        id=id if id else f"mock_ai_msg_{uuid.uuid4()}",
        # tool_call_chunks is part of AIMessageChunk but AIMessage can accept it.
        # This might be useful for some mock scenarios.
        additional_kwargs={'tool_call_chunks': tool_call_chunks} if tool_call_chunks else {}
    )

# Example Usage (can be removed or kept for testing this module)
if __name__ == '__main__':
    # Mock AI message with simple content
    simple_message = create_mock_ai_message(content="Hello, this is a mock response.")
    print(f"Simple Message: {simple_message}")

    # Mock AI message with a tool call
    mock_tool = create_mock_tool_call(name="get_weather", args={"location": "San Francisco"})
    message_with_tool = create_mock_ai_message(
        content="",  # Often empty when tool calls are present
        tool_calls=[mock_tool]
    )
    print(f"Message with Tool Call: {message_with_tool}")

    # Mock AI message simulating streaming tool call chunks
    # (Note: AIMessage itself doesn't directly use tool_call_chunks in its primary fields,
    # but it can be passed via additional_kwargs if a mock needs to simulate chunking behavior
    # that a downstream consumer might aggregate)
    chunks = [
        {"name": "search_tool", "args": '{ "query": "latest "', "index": 0, "id": "tool_abc"},
        {"args": ' "news" }', "index": 0, "id": "tool_abc"},
    ]
    message_with_chunks = create_mock_ai_message(
        content="",
        additional_kwargs={"tool_call_chunks": chunks} # Storing in additional_kwargs
                                                      # as AIMessage type doesn't directly have tool_call_chunks
    )
    # A more accurate way to represent a final AIMessage that *resulted* from streamed chunks
    # would be to construct the final ToolCall object.
    # This example is more about how you might pass chunk-like data if your mock setup needs it.
    
    # Correct representation for an AIMessage that has a fully formed tool call
    # (potentially aggregated from chunks by some upstream process before reaching the agent logic being tested)
    aggregated_tool_call = ToolCall(name="search_tool", args={"query": "latest news"}, id="tool_abc")
    final_message_from_streamed_tool = AIMessage(content="", tool_calls=[aggregated_tool_call])
    print(f"Final Message from Streamed Tool Call: {final_message_from_streamed_tool}")

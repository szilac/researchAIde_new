from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

PerformativeType = Literal[
    "inform_result",  # Informing about the result of an action
    "inform_state",   # Informing about the current state
    "request_action", # Requesting an agent to perform an action
    "request_info",   # Requesting information from an agent
    "query_data",     # Querying data (e.g., from a vector store)
    "provide_feedback", # Providing feedback on a previous output
    "confirm_action", # Confirming an action has been taken
    "reject_action",  # Rejecting a request
    "error_report",   # Reporting an error
    "status_update"   # Providing a status update on a long-running task
]

class AgentMessage(BaseModel):
    """
    Standardized message structure for inter-agent communication within the LangGraph orchestrator.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str  # Should typically be the session_id from GraphState
    sender_agent_id: str  # ID or name of the sending agent/node
    receiver_agent_id: Optional[str] = None # ID or name of the intended receiving agent/node, None for broadcast or state update
    
    performative: PerformativeType
    content: Dict[str, Any] # Structured content of the message
    
    timestamp: str = Field(default_factory=lambda: str(uuid.uuid4())) # Using uuid4 for timestamp for simplicity, replace with datetime if needed

    class Config:
        frozen = True # Messages are immutable once created

# Example Usage (not part of the file, just for illustration):
# msg = AgentMessage(
#     conversation_id=\"session_123\",
#     sender_agent_id=\"PhdAgentNode\",
#     receiver_agent_id=\"ArxivSearchNode\",
#     performative=\"request_action\",
#     content={\"task\": \"execute_search\", \"query\": \"quantum computing\"}
# ) 
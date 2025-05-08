from typing import Literal, Dict, Any, Optional, List, Union
from pydantic import Field # Removed BaseModel as BaseMessage is the base
import uuid
from langchain_core.messages import BaseMessage

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
    "status_update",  # Providing a status update on a long-running task
    "system_event"   # Added for more general system messages
]

class AgentMessage(BaseMessage):
    """
    Standardized message structure for inter-agent communication within the LangGraph orchestrator.
    Inherits from BaseMessage for LangGraph compatibility.
    """
    content: Union[str, List[Union[Dict[str, Any], str]]]
    # Custom fields will be managed via additional_kwargs or set directly if not part of Pydantic validation of BaseMessage itself
    # The `type` field is inherited from BaseMessage and should be set appropriately.

    # Pydantic fields for our custom attributes. These will be stored in additional_kwargs by BaseMessage.
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str  # Should typically be the session_id from GraphState
    sender_agent_id: str  # ID or name of the sending agent/node
    receiver_agent_id: Optional[str] = None # ID or name of the intended receiving agent/node, None for broadcast or state update
    performative: PerformativeType
    structured_content: Optional[Dict[str, Any]] = None # Keep this to hold our original dict content
    timestamp: str = Field(default_factory=lambda: str(uuid.uuid4())) # Using uuid4 for timestamp for simplicity, replace with datetime if needed

    # Ensure 'type' is explicitly part of __init__ or set before super()
    # type: str # This is already a field in BaseMessage

    def __init__(self, **data: Any):
        # Pop custom fields to handle them separately before passing to BaseMessage
        original_structured_content = data.pop('content', {})
        # Ensure custom fields are present in data for BaseMessage to pick up in additional_kwargs or if it expects them
        # Pydantic V2 BaseModel handles extra fields by default based on config (extra='allow' is default for BaseMessage I believe)
        
        # BaseMessage expects 'content' as str or List[Union[str, Dict]]
        # Create a simple string representation for BaseMessage.content
        # More sophisticated serialization might be needed for complex dicts.
        content_for_base = str(original_structured_content) if original_structured_content else ""
        data['content'] = content_for_base # Put the transformed content back for BaseMessage

        # Ensure 'type' is set for BaseMessage. If not provided, infer or default it.
        if 'type' not in data:
            data['type'] = data.get('sender_agent_id', 'system_event')

        # Store original dict content in our dedicated field. 
        # This must be done carefully due to frozen nature. Pass it to super() via data.
        if isinstance(original_structured_content, dict):
            data['structured_content'] = original_structured_content
        else:
            # Ensure structured_content is None if original was not a dict or not present
            data['structured_content'] = None 

        super().__init__(**data)
        # After super().__init__, the instance is frozen. No more direct assignments to fields like self.structured_content
        # If BaseMessage doesn't pick up structured_content as a field via **data, it will be in additional_kwargs if extra='allow'

    class Config:
        # frozen = True # Removed frozen config to allow LangGraph add_messages to assign id
        arbitrary_types_allowed = True # Often needed with BaseMessage and additional_kwargs

# Example Usage (not part of the file, just for illustration):
# msg = AgentMessage(
#     conversation_id=\"session_123\",
#     sender_agent_id=\"PhdAgentNode\",
#     receiver_agent_id=\"ArxivSearchNode\",
#     performative=\"request_action\",
#     content={\"task\": \"execute_search\", \"query\": \"quantum computing\"}
# ) 
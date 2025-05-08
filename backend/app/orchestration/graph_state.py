from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph.message import add_messages # Keep this import with GraphState
from app.models.message_models import AgentMessage # Keep this import with GraphState

# --- Constants ---
MAX_ITERATIONS_REFINE = 3
MAX_RETRIES = 2 # Max retries for error recovery

# --- Graph State Definition ---
class GraphState(TypedDict):
    """
    Represents the state of our research orchestration graph.
    """
    # Core research inputs
    research_query: Optional[str]
    config_parameters: Optional[Dict[str, Any]]
    session_id: Optional[str]

    # Planning and Searching
    initial_phd_prompt: Optional[str]
    constructed_queries: Optional[List[Dict[str, Any]]]
    query_formulation_confidence: Optional[float]
    search_parameters: Optional[Dict[str, Any]]
    raw_arxiv_results: Optional[List[Dict[str, Any]]]
    search_execution_status: Optional[str]

    # Analysis and Shortlisting
    scored_arxiv_results: Optional[List[Dict[str, Any]]]
    shortlisting_threshold: Optional[float]
    initial_paper_shortlist: Optional[List[Dict[str, Any]]]

    # Human Review and Processing
    confirmed_paper_shortlist: Optional[List[Dict[str, Any]]]
    ingestion_reports: Optional[List[Dict[str, Any]]]
    processed_paper_ids: Optional[List[str]] # Added as it's used by nodes

    # Literature Analysis and Gap Identification
    research_plan: Optional[Any]
    analysis_prompt_template: Optional[str]
    literature_analysis_output: Optional[Dict[str, Any]]
    updated_research_plan: Optional[Any]
    chroma_query_summaries: Optional[List[Any]]
    identified_gaps_output: Optional[Dict[str, Any]]

    # Direction Generation and Refinement Cycle
    generated_directions_output: Optional[Dict[str, Any]]
    literature_context_summary: Optional[str]
    iteration_count: int
    postdoc_evaluation_output: Optional[Dict[str, Any]]
    current_directions_being_refined: Optional[Dict[str, Any]]
    refined_directions_output: Optional[Dict[str, Any]]
    previous_refined_directions_output: Optional[Dict[str, Any]]

    # Final Presentation
    final_approved_directions: Optional[Dict[str, Any]]
    final_postdoc_evaluation: Optional[Dict[str, Any]]
    user_facing_report_data: Optional[Dict[str, Any]]
    workflow_outcome: Optional[str] # Added for final status

    # General conversational messages
    messages: Annotated[List[AgentMessage], add_messages]

    # Error Handling
    error_message: Optional[str]
    error_source_node: Optional[str]
    error_details: Optional[Any]
    recovery_strategy_decision: Optional[str]
    current_graph_state_snapshot: Optional[Dict[str, Any]]
    retry_attempts: Optional[Dict[str, int]]
    
    # Task Tracking (within nodes)
    active_node_tasks: Optional[Dict[str, Dict[str, Any]]]

    # Event System
    last_events: Optional[List[Dict[str, Any]]]

    # Coordination & Conflict Resolution
    conflict_detected: Optional[bool]
    conflicting_outputs: Optional[List[Any]]
    resolved_output: Optional[Any]

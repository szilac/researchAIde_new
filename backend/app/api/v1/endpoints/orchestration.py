import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.dependencies import get_research_orchestrator
from app.orchestration.orchestrator import ResearchOrchestrator
from app.orchestration.graph_state import GraphState # For type hinting and understanding state structure
from app.models.message_models import AgentMessage # For understanding messages in state

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models for API ---

class WorkflowStartRequest(BaseModel):
    research_query: str = Field(..., description="The initial research query or topic.")
    general_area: Optional[str] = Field(None, description="Optional general research area.")
    initial_phd_prompt: Optional[str] = Field(None, description="Optional specific initial prompt for the PhD Agent.")
    user_id: Optional[str] = Field(None, description="Optional user identifier for the session.")
    session_id: Optional[UUID] = Field(default_factory=uuid4, description="Optional session ID; one will be generated if not provided.")
    config_parameters: Optional[Dict[str, Any]] = Field(None, description="Optional configuration parameters for the workflow.")

class WorkflowInitiateResponse(BaseModel):
    workflow_id: UUID = Field(..., description="The unique ID for this workflow instance (matches session_id).")
    status: str = Field(default="initiated", description="Initial status of the workflow.")
    message: str = Field(default="Workflow initiated and will run in the background.", description="User-facing message.")

class WorkflowStatusResponse(BaseModel):
    workflow_id: UUID
    current_graph_state: Optional[Dict[str, Any]] = Field(None, description="Snapshot of the current graph state. For debugging or detailed view.")
    
    # Key fields extracted from GraphState for frontend convenience
    research_query: Optional[str] = None
    session_id: Optional[UUID] = None
    user_id: Optional[str] = None
    initial_phd_prompt: Optional[str] = None
    iteration_count: Optional[int] = None
    max_iterations_refine: Optional[int] = None
    max_retries: Optional[int] = None
    
    constructed_queries: Optional[Any] = None # FormulatedQueriesOutput
    arxiv_search_results: Optional[List[Dict]] = None
    scored_arxiv_results: Optional[List[Dict]] = None # List[PaperRelevanceAssessment]
    initial_paper_shortlist: Optional[List[Dict]] = None
    confirmed_paper_shortlist: Optional[List[Dict]] = None
    
    processing_progress: Optional[Dict] = None
    ingestion_reports: Optional[List[Dict]] = None
    
    literature_analysis_output: Optional[Any] = None # LiteratureAnalysisOutput
    conflict_resolution_attempts: Optional[int] = None
    identified_gaps_output: Optional[Any] = None # IdentifiedGapsOutput
    generated_directions_output: Optional[Any] = None # GeneratedDirectionsOutput
    postdoc_evaluation_output: Optional[Any] = None # PostDocEvaluationOutput
    refined_directions_output: Optional[Any] = None # GeneratedDirectionsOutput
    
    user_facing_report_data: Optional[Dict[str, Any]] = None
    
    last_events: Optional[List[Dict]] = Field(None, description="Recent events from the workflow.")
    messages: Optional[List[Dict]] = Field(None, description="Chronological messages from agents in the workflow.")
    
    error_message: Optional[str] = None
    error_source_node: Optional[str] = None
    error_details: Optional[str] = None
    workflow_outcome: Optional[str] = Field(None, description="Overall outcome: 'running', 'success', 'error', 'error_in_finalization', 'max_iterations_reached', 'max_retries_reached', 'waiting_for_shortlist_review'")
    
    # Fields to guide frontend interaction
    is_waiting_for_input: bool = False
    input_prompt_message: Optional[str] = None # e.g., "Please review the paper shortlist."
    
    # Add a field for the current active node or step if easily determinable
    current_step_name: Optional[str] = None


class ShortlistReviewRequest(BaseModel):
    # Assuming papers are identified by a unique ID, e.g., arxiv_id
    # The actual structure of a "paper" dict here should match what initial_paper_shortlist provides
    confirmed_papers: List[Dict[str, Any]] = Field(..., description="List of paper objects that the user confirmed for further processing.")

# --- Helper to extract data from GraphState into WorkflowStatusResponse ---
def _map_state_to_status_response(workflow_id: UUID, graph_state_dict: Optional[Dict[str, Any]]) -> WorkflowStatusResponse:
    """Helper to map GraphState dict to API response model."""
    if not graph_state_dict:
        # Handle case where state might exist but be empty/invalid
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status="unknown",
            workflow_outcome="unknown_state_empty_or_invalid",
            current_step_name="unknown",
            last_updated=str(uuid4()) # Placeholder - need proper timestamp
        )

    outcome = "running"
    is_waiting = False
    current_step = graph_state_dict.get("__metadata__", {}).get("step", -1) # Get current step from metadata if available
    current_node = "unknown"
    
    # Determine current node based on last message sender if possible
    last_message = graph_state_dict.get("messages", [])[-1] if graph_state_dict.get("messages") else None
    if isinstance(last_message, AgentMessage):
         current_node = f"After {last_message.sender_agent_id}" # Approximat
    elif isinstance(last_message, dict) and 'sender_agent_id' in last_message:
         current_node = f"After {last_message['sender_agent_id']}" # If state has dicts
    else:
        # Fallback if no messages or last message is not informative
        # Maybe check `last_events`?
        last_event = graph_state_dict.get("last_events", [])[-1] if graph_state_dict.get("last_events") else None
        if last_event and isinstance(last_event, dict) and last_event.get("details", {}).get("node"):
            current_node = f"After {last_event['details']['node']}"

    # Check for specific waiting state flag
    if graph_state_dict.get("is_waiting_for_shortlist_review", False):
        outcome = "waiting_for_shortlist_review"
        is_waiting = True
        current_node = "request_shortlist_review_node" # Explicitly set node

    # Check for final outcomes (overwrite waiting state if finished)
    elif graph_state_dict.get("workflow_outcome") == "success":
        outcome = "success"
        is_waiting = False
        current_node = "prepare_final_output_node" # Final node
    elif graph_state_dict.get("workflow_outcome", "").startswith("error"):
        outcome = graph_state_dict.get("workflow_outcome", "error_unknown")
        is_waiting = False
        current_node = graph_state_dict.get("error_source_node", current_node)

    # Extract relevant data for the response payload
    response_payload = {}
    if outcome == "waiting_for_shortlist_review":
        response_payload["initial_paper_shortlist"] = graph_state_dict.get("initial_paper_shortlist", [])
        response_payload["research_query"] = graph_state_dict.get("research_query")
    elif outcome == "success":
        # Include final report data if available
        response_payload["final_report"] = graph_state_dict.get("user_facing_report_data")
    elif "error" in outcome:
        response_payload["error_details"] = {
            "source_node": graph_state_dict.get("error_source_node"),
            "message": graph_state_dict.get("error_message"),
            "traceback": graph_state_dict.get("error_details") # Be careful exposing tracebacks
        }

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status=outcome, # Use the determined outcome as the primary status
        workflow_outcome=outcome,
        current_step_name=current_node,
        is_waiting_for_input=is_waiting,
        payload=response_payload,
        last_updated=str(uuid4()) # Placeholder
    )

# --- API Endpoints ---

@router.post("/workflows/", response_model=WorkflowInitiateResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ResearchOrchestrator = Depends(get_research_orchestrator)
):
    """
    Initiates a new research workflow asynchronously.
    """
    workflow_id = request.session_id or uuid4() # Use provided or generate UUID
    logger.info(f"Starting workflow {workflow_id} for query: '{request.research_query}' and general area: '{request.general_area}'")

    # Check if dependent services (like agents) were initialized properly
    if orchestrator.phd_agent is None:
        logger.error(f"Cannot start workflow {workflow_id}: PhD Agent service is unavailable (failed initialization).")
        raise HTTPException(status_code=503, detail="PhD Agent service unavailable.")
    
    # Corrected check: Access the LLM provider instance via agent.dependencies.llm_manager
    if orchestrator.phd_agent.dependencies.llm_manager is None:
         logger.warning(f"Starting workflow {workflow_id}, but PhD Agent has no configured LLM provider via dependencies.")
         # Consider raising 503 if LLM is absolutely required for any workflow start

    # Construct initial state for the LangGraph graph
    initial_state: GraphState = {
        "research_query": request.research_query,
        "general_area": request.general_area,
        "initial_phd_prompt": request.initial_phd_prompt,
        "session_id": workflow_id, # Pass the UUID object
        "user_id": request.user_id,
        "config_parameters": request.config_parameters or {}, 
        # Initialize other necessary fields from GraphState with defaults if needed
        "messages": [],
        "last_events": [],
        "raw_arxiv_results": None,
        "constructed_queries": None,
        "search_execution_status": None,
        "scored_paper_results": None,
        "initial_paper_shortlist": None,
        "is_waiting_for_shortlist_review": False,
        "reviewed_paper_shortlist": None,
        "literature_analysis_results": None,
        "identified_gaps": None,
        "generated_directions": None,
        "final_report": None,
        "error_message": None,
        "error_source_node": None,
        "error_details": None,
    }

    config = {"configurable": {"thread_id": str(workflow_id)}} 

    # Corrected: Call graph.ainvoke for background execution
    background_tasks.add_task(orchestrator.graph.ainvoke, initial_state, config)

    return WorkflowInitiateResponse(
        workflow_id=workflow_id,
        status="initiated",
        message="Workflow started successfully in the background."
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: UUID = Path(..., description="The ID of the workflow to retrieve."),
    orchestrator: ResearchOrchestrator = Depends(get_research_orchestrator)
):
    """
    Retrieves the current status and state of a research workflow.
    """
    config = {"configurable": {"thread_id": str(workflow_id)}}
    logger.info(f"API: Fetching status for workflow ID: {workflow_id} (Config: {config})")
    
    current_state_snapshot = None
    snapshot_type = "N/A"
    state_values = None
    try:
        current_state_snapshot = orchestrator.graph.get_state(config)
        snapshot_type = type(current_state_snapshot).__name__
        logger.info(f"API: orchestrator.graph.get_state for {workflow_id} returned type: {snapshot_type}. Value: {current_state_snapshot}")

        # Check 1: Is the snapshot object itself None?
        if current_state_snapshot is None:
            logger.warning(f"API: get_state returned None for {workflow_id}. Raising 404.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow state not found (snapshot is None).")
        
        # Check 2: Does the snapshot have values and are they non-empty?
        if not hasattr(current_state_snapshot, 'values') or not current_state_snapshot.values:
             logger.warning(f"API: get_state returned a snapshot, but it has no 'values' or values are empty for {workflow_id}. Snapshot: {current_state_snapshot}. Raising 404.")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow state not found (snapshot has no values).")

        # If we pass both checks, proceed
        state_values = current_state_snapshot.values
        logger.info(f"API: Extracted non-empty state_values from snapshot for {workflow_id}. Type: {type(state_values).__name__}")
        if isinstance(state_values, dict):
             logger.debug(f"API: State values keys: {list(state_values.keys())}")
        else:
             logger.debug(f"API: State values are not a dict: {state_values}")

        # Map and return
        response_data = _map_state_to_status_response(workflow_id, state_values)
        logger.info(f"API: Returning status for workflow {workflow_id}. Outcome: {response_data.workflow_outcome}")
        return response_data

    except HTTPException as http_exc:
        logger.warning(f"API: Re-raising HTTPException (Status: {http_exc.status_code}) for workflow {workflow_id}.")
        raise http_exc 
    except Exception as e:
        logger.error(f"API: Error retrieving state for workflow {workflow_id} (Snapshot Type: {snapshot_type}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workflow state: {str(e)}")


@router.post("/workflows/{workflow_id}/shortlist_review", response_model=WorkflowStatusResponse)
async def submit_shortlist_review(
    request_data: ShortlistReviewRequest,
    background_tasks: BackgroundTasks, # To resume graph in background
    workflow_id: UUID = Path(..., description="The ID of the workflow."),
    orchestrator: ResearchOrchestrator = Depends(get_research_orchestrator),
):
    """
    Submits the user's confirmed paper shortlist to a waiting workflow.
    This endpoint is called when the workflow status indicates it's waiting for shortlist review.
    It updates the workflow state and attempts to resume it.
    """
    logger.info(f"Received shortlist review for workflow {workflow_id}. Confirmed papers: {len(request_data.confirmed_papers)}")
    config = {"configurable": {"thread_id": str(workflow_id)}}

    try:
        # 1. Get current state to ensure it's actually waiting
        current_state_snapshot = orchestrator.graph.get_state(config)
        if not current_state_snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found or state missing.")

        # Basic check: Is it expecting this input? More robust checks would involve specific state flags.
        # For now, we assume if this endpoint is called, it's the right time.
        # A better check would be against `workflow_outcome == "waiting_for_shortlist_review"`
        # from a mapped status response, or a flag in GraphState.

        # 2. Update the state with the confirmed shortlist
        # The structure of confirmed_paper_shortlist should match what `process_and_ingest_papers_node` expects.
        # This usually involves full paper objects from the `initial_paper_shortlist`.
        update_payload = {"confirmed_paper_shortlist": request_data.confirmed_papers}
        
        # Add a message indicating user provided feedback
        user_feedback_message = AgentMessage(
            conversation_id=str(workflow_id),
            sender_agent_id="user_via_api", # Or a more specific user identifier
            performative="INFORM_CONTENT", # Or a custom performative like "PROVIDE_REVIEW"
            content={
                "review_type": "paper_shortlist_confirmation",
                "confirmed_count": len(request_data.confirmed_papers),
                "details": "User submitted confirmed paper shortlist."
            }
        ).model_dump(mode='json') # Ensure it's a dict for state update

        # Append to existing messages
        current_messages = current_state_snapshot.values.get("messages", [])
        updated_messages = current_messages + [user_feedback_message]
        update_payload["messages"] = updated_messages

        orchestrator.graph.update_state(config, update_payload)
        logger.info(f"State updated for workflow {workflow_id} with confirmed shortlist.")

        # 3. Resume the graph execution in the background
        # Pass None as the first argument to ainvoke to continue from the updated state
        background_tasks.add_task(orchestrator.graph.ainvoke, None, config)
        logger.info(f"Workflow {workflow_id} resumed in background after shortlist review.")
        
        # Optimistically return a status indicating it's resuming
        # Client should poll GET /workflows/{workflow_id} for actual next state
        return WorkflowStatusResponse(
            workflow_id=workflow_id, 
            workflow_outcome="resuming_after_review",
            messages=[user_feedback_message] # Show the message we just added
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting shortlist review for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing shortlist review: {str(e)}")


@router.get("/workflows/{workflow_id}/results", response_model=WorkflowStatusResponse) # Reuse for consistency
async def get_workflow_results(
    workflow_id: UUID = Path(..., description="The ID of the workflow to retrieve results for."),
    orchestrator: ResearchOrchestrator = Depends(get_research_orchestrator)
):
    """
    Retrieves the final results of a completed research workflow.
    If the workflow is not yet completed or errored, it returns the current status.
    """
    logger.info(f"Fetching results for workflow {workflow_id}")
    config = {"configurable": {"thread_id": str(workflow_id)}}
    
    try:
        current_state_snapshot = orchestrator.graph.get_state(config)
        if current_state_snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow state not found.")
        
        state_values = current_state_snapshot.values
        response_data = _map_state_to_status_response(workflow_id, state_values)

        if response_data.workflow_outcome == "success" and response_data.user_facing_report_data:
            logger.info(f"Final results retrieved for workflow {workflow_id}.")
            return response_data
        elif response_data.workflow_outcome not in ["running", "waiting_for_shortlist_review", "resuming_after_review"]: # Error or other terminal state
             logger.warning(f"Attempted to get results for workflow {workflow_id}, but it's in state: {response_data.workflow_outcome}")
             return response_data # Return current status which includes error info
        else: # Still running or waiting
            logger.info(f"Workflow {workflow_id} is still in progress (state: {response_data.workflow_outcome}). Returning current status.")
            # Maybe raise a specific HTTP error like 425 Too Early if strictly for final results
            # But returning current status is more informative for polling clients
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workflow results: {str(e)}")

# TODO:
# - Consider adding an endpoint to explicitly interrupt/cancel a workflow.
# - The `_map_state_to_status_response` needs refinement to accurately reflect `current_step_name`
#   and `is_waiting_for_input` based on the actual graph structure and how it signals these states.
#   This might involve adding specific flags or sentinel values to the GraphState by the orchestrator nodes.
# - Error handling in `_map_state_to_status_response` for messages needs to be robust.
# - Ensure that `GraphState`
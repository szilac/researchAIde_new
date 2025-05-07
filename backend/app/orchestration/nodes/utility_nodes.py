\
from typing import Dict, Any, Optional, List
import traceback

from ..graph_state import GraphState, MAX_RETRIES # MAX_RETRIES is used in global_error_handler
from backend.app.models.message_models import AgentMessage, PerformativeType
from backend.app.utils.logging_utils import get_logger

logger = get_logger(__name__)

async def prepare_final_output_node(state: GraphState) -> Dict[str, Any]:
    node_name = "prepare_final_output_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        final_directions_output = state.get("refined_directions_output") or state.get("generated_directions_output")
        last_postdoc_eval = state.get("postdoc_evaluation_output")
        literature_analysis = state.get("literature_analysis_output")
        identified_gaps = state.get("identified_gaps_output")
        original_query = state.get("research_query")
        initial_phd_prompt = state.get("initial_phd_prompt")
        formulated_queries = state.get("constructed_queries")
        scored_arxiv_results = state.get("scored_arxiv_results")
        initial_shortlist = state.get("initial_paper_shortlist")
        confirmed_shortlist = state.get("confirmed_paper_shortlist")
        ingestion_reports = state.get("ingestion_reports")
        iteration_count = state.get("iteration_count", 0)

        report_data = {
            "session_id": session_id,
            "original_research_query": original_query,
            "initial_system_prompt_to_phd": initial_phd_prompt,
            "formulated_search_queries": formulated_queries,
            "scored_arxiv_papers": scored_arxiv_results,
            "initial_shortlisted_papers": initial_shortlist,
            "human_confirmed_shortlisted_papers": confirmed_shortlist,
            "paper_ingestion_summary": ingestion_reports,
            "literature_analysis_results": literature_analysis,
            "identified_research_gaps": identified_gaps,
            "final_research_directions": final_directions_output,
            "last_evaluation_of_directions": last_postdoc_eval,
            "total_refinement_iterations": iteration_count,
            "workflow_status": "completed_successfully"
        }

        summary_message_content = {"status": "Research workflow completed successfully.", "session_id": session_id, "final_directions_count": len(final_directions_output.get("directions", [])) if final_directions_output else 0, "total_iterations": iteration_count}
        final_agent_message = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_COMPLETION, content=summary_message_content)
        final_event = {"event_type": "FinalOutputReady", "details": summary_message_content}
        current_events = state.get("last_events", [])
        updated_events = current_events + [final_event]

        logger.info(f"Final output prepared for session {session_id}. Workflow complete.")

        return {
            "user_facing_report_data": report_data,
            "messages": add_messages(state.get("messages", []), [final_agent_message]),
            "last_events": updated_events,
            "error_message": None, "error_source_node": None, "error_details": None,
            "workflow_outcome": "success"
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "user_facing_report_data": {"status": "error_in_final_reporting", "error_message": str(e)},
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})]),
            "workflow_outcome": "error_in_finalization"
        }

async def global_error_handler_node(state: GraphState) -> Dict[str, Any]:
    node_name = "global_error_handler_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    
    error_message = state.get("error_message", "Unknown error")
    source_node = state.get("error_source_node", "Unknown node")
    retry_attempts_map = state.get("retry_attempts", {}) # Renamed to avoid conflict
    current_retries = retry_attempts_map.get(source_node, 0)
    session_id = state.get("session_id", "unknown_session")
    
    logger.info(f"Handling error from node: {source_node}. Message: {error_message}. Retries: {current_retries}")

    recovery_strategy = "TERMINATE_SAFELY"
    if current_retries < MAX_RETRIES:
        logger.info(f"Attempting retry {current_retries + 1}/{MAX_RETRIES} for node {source_node}.")
        recovery_strategy = "RETRY_NODE"
        retry_attempts_map[source_node] = current_retries + 1
    else:
        logger.warning(f"Max retries ({MAX_RETRIES}) reached for node {source_node}. Terminating.")
        recovery_strategy = "TERMINATE_SAFELY"

    error_report_message = AgentMessage(
        conversation_id=session_id,
        sender_agent_id=node_name,
        performative=PerformativeType.ERROR_REPORT,
        content={"failed_node": source_node, "error_message": error_message, "chosen_strategy": recovery_strategy, "retries_attempted": retry_attempts_map.get(source_node, 0)}
    )
    
    error_state_update = {}
    if recovery_strategy == "RETRY_NODE":
        error_state_update = {"error_message": None, "error_source_node": None, "error_details": None}

    return {
        "recovery_strategy_decision": recovery_strategy,
        "retry_attempts": retry_attempts_map,
        "messages": [error_report_message],
        **error_state_update
    }

async def resolve_conflict_node(state: GraphState) -> Dict[str, Any]:
    node_name = "resolve_conflict_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        conflicts = state.get("conflicting_outputs")
        # source_of_conflict = state.get("error_source_node") # May not be accurate for conflicts
        logger.info(f"Resolving conflict. Conflicting data: {conflicts}")
        
        resolved_data = None
        if conflicts and isinstance(conflicts, list) and len(conflicts) > 0:
            resolved_data = conflicts[0] 
        else:
            resolved_data = state.get("literature_analysis_output") 
            logger.warning(f"No specific conflicting_outputs, falling back to literature_analysis_output: {resolved_data}")

        logger.info(f"Conflict resolved (simulated). Using output: {resolved_data}")
        resolution_event = {"event_type": "ConflictResolved", "details": {"node": node_name, "strategy": "Simulated:PickFirstOrFallback"}}
        
        return {
            "literature_analysis_output": resolved_data, 
            "conflict_detected": False,
            "conflicting_outputs": None,
            "resolved_output": resolved_data,
            "last_events": [resolution_event],
            "error_message": None, "error_source_node": None, "error_details": None,
            "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_RESULT, content={"status": "conflict_resolved", "resolution_strategy": "Simulated:PickFirstOrFallback"})])
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name} during conflict resolution: {e} !!!", exc_info=True)
        return {
            "error_message": f"Failed to resolve conflict: {e}",
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "conflict_detected": True, # Keep flag set
            "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": f"Failed to resolve conflict: {e}"})])
        }

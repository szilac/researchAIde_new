from typing import Dict, Any, Optional, List
import traceback

from ..graph_state import GraphState
from app.models.message_models import AgentMessage, PerformativeType
from app.utils.logging_utils import get_logger
from langgraph.graph.message import add_messages

# Type hints for agents/services
from app.agents.phd_agent import PhDAgent, GeneratedDirectionsOutput
from app.agents.postdoc_agent import PostDocAgent
from app.models.operation_models import IdentifiedGapsOutput, PostDocEvaluationOutput

logger = get_logger(__name__)

async def identify_research_gaps_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "identify_research_gaps_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        literature_analysis_output = state.get("literature_analysis_output")
        research_query = state.get("research_query")

        if not research_query:
            raise ValueError("Research query is missing for gap identification.")
        if not phd_agent:
            raise ValueError("PhDAgent was not provided.")
        
        if not literature_analysis_output or literature_analysis_output.get("status") != "analysis_complete":
            logger.warning("Literature analysis missing or incomplete. Skipping gap identification.")
            message_content = {"status": "skipped_no_valid_analysis", "gaps_identified_count": 0}
            return {
                "identified_gaps_output": message_content,
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=message_content)]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }
        
        analysis_summary = literature_analysis_output.get("overall_summary", "")
        key_themes = literature_analysis_output.get("key_themes", [])

        logger.info(f"Calling PhDAgent to identify research gaps for query: '{research_query}'")

        gaps_output_model: Optional[IdentifiedGapsOutput] = await phd_agent.identify_research_gaps(
            literature_summary=analysis_summary,
            key_themes=key_themes,
            research_topic=research_query
        )
        
        gaps_output_dict = None
        if gaps_output_model and hasattr(gaps_output_model, 'model_dump'):
            gaps_output_dict = gaps_output_model.model_dump(exclude_none=True)
            if "status" not in gaps_output_dict:
                gaps_output_dict["status"] = "gaps_identification_complete"
        else:
            phd_agent.logger.warning("PhDAgent.identify_research_gaps returned None/unexpected format.")
            gaps_output_dict = {"status": "gaps_identification_failed_agent_output_issue", "identified_gaps": [], "summary_of_gaps": "Agent did not return valid gap analysis."}

        message_to_next_node = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=gaps_output_dict)
        return {
            "identified_gaps_output": gaps_output_dict,
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "identified_gaps_output": {"status": "gaps_identification_error", "error_message": str(e)},
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

async def generate_research_directions_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "generate_research_directions_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        identified_gaps_output = state.get("identified_gaps_output")
        research_topic = state.get("research_query") 

        if not research_topic:
            raise ValueError("Research topic is missing for generating research directions.")
        if not phd_agent:
            raise ValueError("PhDAgent was not provided.")

        if not identified_gaps_output or identified_gaps_output.get("status") != "gaps_identification_complete":
            logger.warning("Identified gaps missing or incomplete. Skipping direction generation.")
            message_content = {"status": "skipped_no_valid_gaps", "directions_generated_count": 0}
            return {
                "generated_directions_output": message_content,
                "iteration_count": 0, 
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=message_content)]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        gaps_summary = identified_gaps_output.get("summary_of_gaps", "")
        identified_gaps_list = identified_gaps_output.get("identified_gaps", [])

        logger.info(f"Calling PhDAgent to generate research directions for topic: '{research_topic}'")

        directions_output_model: Optional[GeneratedDirectionsOutput] = await phd_agent.generate_research_directions(
            identified_gaps_summary=gaps_summary,
            identified_gaps_list=identified_gaps_list,
            research_topic=research_topic
        )
        
        directions_output_dict = None
        if directions_output_model and hasattr(directions_output_model, 'model_dump'):
            directions_output_dict = directions_output_model.model_dump(exclude_none=True)
            if "status" not in directions_output_dict:
                directions_output_dict["status"] = "directions_generation_complete"
        else:
            phd_agent.logger.warning("PhDAgent.generate_research_directions returned None/unexpected format.")
            directions_output_dict = {"status": "directions_generation_failed_agent_output_issue", "directions": [], "overall_strategy_justification": "Agent did not return valid directions."}

        message_to_next_node = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=directions_output_dict)
        
        initial_iteration_count = 0 # Initialize for the refinement loop
        return {
            "generated_directions_output": directions_output_dict,
            "iteration_count": initial_iteration_count, 
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "generated_directions_output": {"status": "directions_generation_error", "error_message": str(e)},
            "iteration_count": state.get("iteration_count", 0),
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

async def evaluate_research_directions_node(state: GraphState, postdoc_agent: Optional[PostDocAgent], graph_checkpointer: Optional[Any]) -> Dict[str, Any]:
    node_name = "evaluate_research_directions_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        current_directions_output = state.get("refined_directions_output") or state.get("generated_directions_output")
        literature_summary = state.get("literature_analysis_output", {}).get("overall_summary", "")
        iteration_count = state.get("iteration_count", 0) 

        if not current_directions_output or not current_directions_output.get("directions"):
            logger.warning("No current research directions to evaluate. Skipping evaluation.")
            return {
                "postdoc_evaluation_output": {"status": "skipped_no_directions"},
                "iteration_count": iteration_count + 1, 
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content={"status": "skipped_no_directions"})]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        directions_to_evaluate = current_directions_output.get("directions", [])
        config_params = state.get("config_parameters", {})
        hitl_evaluation_active = config_params.get("hitl_evaluation_active", False)

        evaluation_output_dict = {}
        if postdoc_agent and not hitl_evaluation_active:
            logger.info(f"Calling PostDocAgent to evaluate {len(directions_to_evaluate)} directions (Iter: {iteration_count + 1})")
            postdoc_eval_model: Optional[PostDocEvaluationOutput] = await postdoc_agent.evaluate_research_directions(
                research_directions=directions_to_evaluate,
                literature_summary=literature_summary,
                original_query=state.get("research_query", "")
            )
            if postdoc_eval_model and hasattr(postdoc_eval_model, 'model_dump'):
                evaluation_output_dict = postdoc_eval_model.model_dump(exclude_none=True)
                if "status" not in evaluation_output_dict:
                     evaluation_output_dict["status"] = "evaluation_by_postdoc_complete"
            else:
                postdoc_agent.logger.warning("PostDocAgent.evaluate_research_directions returned None/unexpected format.")
                evaluation_output_dict = {"status": "evaluation_failed_agent_output_issue", "assessments": [], "summary": "PostDocAgent did not return valid evaluation."}
        elif hitl_evaluation_active and graph_checkpointer:
            logger.info(f"INTERRUPT FOR HUMAN EVALUATION (Iter: {iteration_count + 1})")
            data_for_hitl_review = {"interrupt_type": "directions_evaluation_required", "directions": directions_to_evaluate, "summary": literature_summary, "query": state.get("research_query"), "iteration": iteration_count + 1, "session_id": session_id, "message": "Please evaluate directions."}
            evaluation_output_dict = {"status": "pending_human_evaluation", "data_for_review": data_for_hitl_review}
        else:
            logger.warning("PostDocAgent unavailable & HITL not active/possible. Simulating auto-approval.")
            mock_assessments = [{"title": d.get("title", "Dir"), "score": 0.75, "critique": "Simulated plausible."} for d in directions_to_evaluate]
            evaluation_output_dict = {"assessments": mock_assessments, "summary": "Simulated auto-assessment.", "status": "evaluation_simulated_auto_approval"}

        message_to_next_node = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=evaluation_output_dict)
        return {
            "postdoc_evaluation_output": evaluation_output_dict,
            "iteration_count": iteration_count + 1,
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "postdoc_evaluation_output": {"status": "evaluation_error", "error_message": str(e)},
            "iteration_count": state.get("iteration_count", 0) + 1,
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

async def refine_directions_based_on_assessment_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "refine_directions_based_on_assessment_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        postdoc_evaluation_output = state.get("postdoc_evaluation_output")
        current_directions_input = state.get("refined_directions_output") or state.get("generated_directions_output")
        current_directions_list = current_directions_input.get("directions", []) if current_directions_input else []
        research_topic = state.get("research_query")
        iteration_count = state.get("iteration_count", 1)

        if not research_topic:
            raise ValueError("Research topic missing for refining directions.")
        if not phd_agent:
            raise ValueError("PhDAgent was not provided.")

        if not postdoc_evaluation_output or postdoc_evaluation_output.get("status", "").startswith("skipped") or \
           postdoc_evaluation_output.get("status") == "evaluation_error" or \
           postdoc_evaluation_output.get("status") == "pending_human_evaluation":
            logger.warning("Postdoc evaluation skipped, failed, or pending. Cannot refine. Passing through current directions.")
            return {
                "refined_directions_output": current_directions_input, 
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content={"status": "refinement_skipped_invalid_evaluation", "details": postdoc_evaluation_output.get("status")})]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        assessments = postdoc_evaluation_output.get("assessments")
        if not assessments and not current_directions_list:
             logger.warning("No assessments and no current directions. Cannot refine.")
             return {"refined_directions_output": {"status": "refinement_skipped_no_assessment_or_directions"}, "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content={"status": "refinement_skipped_no_assessment_or_directions"})]), "error_message": None, "error_source_node": None, "error_details": None}
        elif not assessments and current_directions_list:
            logger.warning("No specific assessment details provided. Passing through current directions.")
            return {"refined_directions_output": current_directions_input, "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content={"status": "refinement_skipped_no_assessment_details"})]), "error_message": None, "error_source_node": None, "error_details": None}

        logger.info(f"Calling PhDAgent to refine research directions (Iter: {iteration_count}) for topic: '{research_topic}'")

        refined_output_model: Optional[GeneratedDirectionsOutput] = await phd_agent.refine_research_directions(
            current_directions=current_directions_list,
            evaluation_feedback=assessments,
            research_topic=research_topic
        )
        
        refined_output_dict = None
        if refined_output_model and hasattr(refined_output_model, 'model_dump'):
            refined_output_dict = refined_output_model.model_dump(exclude_none=True)
            if "status" not in refined_output_dict:
                refined_output_dict["status"] = "refinement_complete"
        else:
            phd_agent.logger.warning("PhDAgent.refine_research_directions returned None/unexpected format.")
            refined_output_dict = {"status": "refinement_failed_agent_output_issue", "directions": current_directions_list, "justification": "Agent did not return valid refinement."}

        message_to_next_node = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="inform_result", content=refined_output_dict)
        
        return {
            "refined_directions_output": refined_output_dict,
            "iteration_count": iteration_count, # Iteration count is already incremented in evaluate_research_directions_node for the next cycle.
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "refined_directions_output": {"status": "refinement_error", "error_message": str(e), "directions": state.get("refined_directions_output", {}).get("directions", []) or state.get("generated_directions_output", {}).get("directions", [])},
            "iteration_count": state.get("iteration_count", 1),
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

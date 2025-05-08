from typing import TypedDict, List, Dict, Any, Optional, Annotated
import uuid
import traceback
import asyncio
import functools # Added for functools.partial
import logging # Import logging

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Send

from app.models.message_models import AgentMessage, PerformativeType

# Import from new modules
from .graph_state import GraphState, MAX_ITERATIONS_REFINE, MAX_RETRIES
from .conditional_edges import should_refine_further, check_for_errors, check_for_conflict

# Import node functions
from .nodes.initialization_nodes import (
    initialize_workflow_node, 
    formulate_search_queries_node, 
    execute_arxiv_search_node
)
from .nodes.analysis_nodes import (
    score_paper_relevance_node,
    create_initial_shortlist_node,
    request_shortlist_review_node,
    process_and_ingest_papers_node,
    perform_literature_analysis_node
)
from .nodes.refinement_nodes import (
    identify_research_gaps_node,
    generate_research_directions_node,
    evaluate_research_directions_node,
    refine_directions_based_on_assessment_node
)
from .nodes.utility_nodes import (
    prepare_final_output_node,
    global_error_handler_node,
    resolve_conflict_node
)

# Agent and Service Imports (These will remain as they are specific to the orchestrator's dependencies)
from backend.app.agents.phd_agent import PhDAgent
from backend.app.agents.postdoc_agent import PostDocAgent
from backend.app.services.arxiv_service import ArxivService
from backend.app.services.pdf_processor import PyPDF2Processor 
from backend.app.services.ingestion_service import IngestionService
from backend.app.services.vector_db_client import VectorDBClient

# Import Pydantic models from the new location
from backend.app.models.operation_models import (
    FormulatedQueriesOutput,
    PaperRelevanceAssessment, # Corrected name for AssessedPaperRelevance
    LiteratureAnalysisOutput,
    IdentifiedGapsOutput,
    GeneratedDirectionsOutput,
    PostDocEvaluationOutput # Assuming this might be needed here too eventually
)

# Define the explicit list of nodes that can be retried
RETRYABLE_NODES = [
    "initializing", "planning", "searching",
    "score_paper_relevance", "create_initial_shortlist", "request_shortlist_review",
    "processing_papers", "literature_analysis",
    "identifying_gaps", "generating_directions",
    "evaluate_research_directions", "refine_directions",
    "presenting_final_directions",
    "resolve_conflict"
    # Add any other nodes that might route to the error handler and need retrying
]

def route_after_error_handler(state: GraphState) -> str:
    """Determines the next node after the error handler runs."""
    recovery_decision = state.get("recovery_strategy_decision", "TERMINATE_SAFELY")
    if recovery_decision == "RETRY_NODE":
        source_node = state.get("error_source_node")
        if source_node in RETRYABLE_NODES:
            print(f"[Router] Retrying node: {source_node}")
            return source_node
        else:
            print(f"[Router] Error: Unknown source node '{source_node}' for retry. Terminating.")
            return END
    else:
        print("[Router] Terminating workflow safely after error.")
        return END

class ResearchOrchestrator:
    def __init__(self, 
                 phd_agent: PhDAgent,
                 arxiv_service: ArxivService,
                 pdf_processor_service: PyPDF2Processor, 
                 ingestion_service: IngestionService, 
                 vector_db_client: VectorDBClient, 
                 postdoc_agent: Optional[PostDocAgent] = None, 
                 checkpointer: Optional[BaseCheckpointSaver] = None
                 ):
        self.phd_agent = phd_agent
        self.arxiv_service = arxiv_service
        self.pdf_processor_service = pdf_processor_service
        self.ingestion_service = ingestion_service
        self.vector_db_client = vector_db_client
        self.postdoc_agent = postdoc_agent
        
        self.workflow = StateGraph(GraphState)
        self._build_graph()
        self.graph = self.workflow.compile(checkpointer=checkpointer)
        self.graph_checkpointer = self.graph.checkpointer

    def _build_graph(self):
        # Initialization and Search
        self.workflow.add_node("initializing", initialize_workflow_node)
        self.workflow.add_node("planning", functools.partial(formulate_search_queries_node, phd_agent=self.phd_agent))
        self.workflow.add_node("searching", functools.partial(execute_arxiv_search_node, arxiv_service=self.arxiv_service))
        
        # Analysis, Shortlisting, Review, Processing, Ingestion
        self.workflow.add_node("score_paper_relevance", functools.partial(score_paper_relevance_node, phd_agent=self.phd_agent))
        self.workflow.add_node("create_initial_shortlist", create_initial_shortlist_node)
        self.workflow.add_node("request_shortlist_review", request_shortlist_review_node)
        self.workflow.add_node("processing_papers", functools.partial(process_and_ingest_papers_node, pdf_processor_service=self.pdf_processor_service, ingestion_service=self.ingestion_service))
        self.workflow.add_node("literature_analysis", functools.partial(perform_literature_analysis_node, phd_agent=self.phd_agent, vector_db_client=self.vector_db_client))
        
        # Refinement Loop Nodes
        self.workflow.add_node("identifying_gaps", functools.partial(identify_research_gaps_node, phd_agent=self.phd_agent))
        self.workflow.add_node("generating_directions", functools.partial(generate_research_directions_node, phd_agent=self.phd_agent))
        self.workflow.add_node("evaluate_research_directions", functools.partial(evaluate_research_directions_node, postdoc_agent=self.postdoc_agent))
        self.workflow.add_node("refine_directions", functools.partial(refine_directions_based_on_assessment_node, phd_agent=self.phd_agent))
        
        # Final Output and Utility Nodes
        self.workflow.add_node("presenting_final_directions", prepare_final_output_node)
        self.workflow.add_node("global_error_handler", global_error_handler_node)
        self.workflow.add_node("resolve_conflict", resolve_conflict_node)
        
        # Conditional Edge Logic Nodes (imported standalone functions)
        self.workflow.add_node("check_conflict_after_literature_analysis", check_for_conflict)
        self.workflow.add_node("check_refinement_loop_condition", should_refine_further)

        self.workflow.add_edge(START, "initializing")

        current_success_path = {
            "initializing": "planning",
            "planning": "searching",
            "searching": "score_paper_relevance",
            "score_paper_relevance": "create_initial_shortlist",
            "create_initial_shortlist": "request_shortlist_review",
            "request_shortlist_review": "processing_papers",
            "processing_papers": "literature_analysis", 
            "resolve_conflict": "identifying_gaps", 
            "identifying_gaps": "generating_directions",
            "generating_directions": "evaluate_research_directions", 
        }

        nodes_with_standard_error_check = [
            "initializing", "planning", "searching",
            "score_paper_relevance", "create_initial_shortlist", "request_shortlist_review",
            "processing_papers", "literature_analysis",
            "identifying_gaps", "generating_directions",
            "evaluate_research_directions", "refine_directions",
            "presenting_final_directions",
            "resolve_conflict"
        ]

        for node_name in nodes_with_standard_error_check:
            next_node_in_path = current_success_path.get(node_name)
            if node_name == "literature_analysis":
                self.workflow.add_conditional_edges(node_name, check_for_errors, {"error_found": "global_error_handler", "no_error": "check_conflict_after_literature_analysis"})
                continue
            if node_name == "resolve_conflict":
                self.workflow.add_conditional_edges(node_name, check_for_errors, {"error_found": "global_error_handler", "no_error": current_success_path.get("resolve_conflict", "identifying_gaps")})
            elif next_node_in_path:
                self.workflow.add_conditional_edges(node_name, check_for_errors, {"error_found": "global_error_handler", "no_error": next_node_in_path})
            elif node_name == "presenting_final_directions": 
                self.workflow.add_conditional_edges(node_name, check_for_errors, {"error_found": "global_error_handler", "no_error": END})
        
        self.workflow.add_conditional_edges("check_conflict_after_literature_analysis", lambda x: x, {"conflict_found": "resolve_conflict", "no_conflict": "identifying_gaps" })
        self.workflow.add_conditional_edges("evaluate_research_directions", check_for_errors, { "error_found": "global_error_handler", "no_error": "refine_directions" })
        self.workflow.add_conditional_edges("refine_directions", check_for_errors, { "error_found": "global_error_handler", "no_error": "check_refinement_loop_condition" })
        self.workflow.add_conditional_edges("check_refinement_loop_condition", lambda x: x, {"evaluate_research_directions": "evaluate_research_directions", "presenting_final_directions": "presenting_final_directions" })
        self.workflow.add_conditional_edges("global_error_handler", route_after_error_handler, {**{node_name: node_name for node_name in RETRYABLE_NODES}, END: END})

    # ... (invoke, ainvoke, stream, get_graph_state, update_graph_state, get_graph_visualization methods remain the same) ...

    # --- REMOVE Original Node Methods that were moved --- 
    # async def initialize_workflow_node(self, state: GraphState) -> Dict[str, Any]:
    #     pass 
    # async def formulate_search_queries_node(self, state: GraphState) -> Dict[str, Any]:
    #     pass 
    # async def execute_arxiv_search_node(self, state: GraphState) -> Dict[str, Any]:
    #     pass 

    # --- Remaining Node Methods (to be moved next) ---
    async def score_paper_relevance_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass 
    async def create_initial_shortlist_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass 
    async def request_shortlist_review_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass 
    async def process_and_ingest_papers_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass 
    async def perform_literature_analysis_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass 
    async def prepare_final_output_node(self, state: GraphState) -> Dict[str, Any]:
        node_name = "prepare_final_output_node"
        print(f"--- Node: {node_name} (Orchestrator Method) ---")
        session_id = state.get("session_id", "unknown_session")
        try:
            # Gather all relevant pieces of information from the state
            final_directions_output = state.get("refined_directions_output") or state.get("generated_directions_output")
            last_postdoc_eval = state.get("postdoc_evaluation_output")
            literature_analysis = state.get("literature_analysis_output")
            identified_gaps = state.get("identified_gaps_output")
            original_query = state.get("research_query")
            initial_phd_prompt = state.get("initial_phd_prompt")
            formulated_queries = state.get("constructed_queries")
            # arxiv_search_summary = state.get("arxiv_search_summary") # Key not consistently used, check if needed
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

            summary_message_content = {
                "status": "Research workflow completed successfully.",
                "session_id": session_id,
                "final_directions_count": len(final_directions_output.get("directions", [])) if final_directions_output else 0,
                "total_iterations": iteration_count
            }
            final_agent_message = AgentMessage(
                conversation_id=session_id,
                sender_agent_id=node_name,
                performative=PerformativeType.INFORM_COMPLETION,
                content=summary_message_content
            )
            
            final_event = {"event_type": "FinalOutputReady", "details": summary_message_content}
            current_events = state.get("last_events", [])
            updated_events = current_events + [final_event]

            print(f"  Final output prepared for session {session_id}. Workflow complete.")

            return {
                "user_facing_report_data": report_data,
                "messages": add_messages(state.get("messages", []), [final_agent_message]),
                "last_events": updated_events,
                "error_message": None, 
                "error_source_node": None, 
                "error_details": None,
                "workflow_outcome": "success"
            }
        except Exception as e:
            print(f"!!! ERROR in {node_name}: {e} !!!")
            if hasattr(self, 'phd_agent') and self.phd_agent:
                self.phd_agent.logger.error(f"Error in {node_name}: {e}", exc_info=True)
            else:
                traceback.print_exc()
            return {
                "error_message": str(e),
                "error_source_node": node_name,
                "error_details": traceback.format_exc(),
                "user_facing_report_data": {"status": "error_in_final_reporting", "error_message": str(e)},
                "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})]),
                "workflow_outcome": "error_in_finalization"
            }

    async def global_error_handler_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass

    async def resolve_conflict_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass
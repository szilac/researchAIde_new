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
from .conditional_edges import should_refine_further, check_for_conflict

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
    resolve_conflict_node
)

# Agent and Service Imports (These will remain as they are specific to the orchestrator's dependencies)
from backend.app.agents.phd_agent import PhDAgent
from backend.app.agents.postdoc_agent import PostDocAgent
from backend.app.services.arxiv_service import ArxivService
from backend.app.services.pdf_processor import PyPDF2Processor # Import the class
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

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    def __init__(self,
                 phd_agent: PhDAgent,
                 arxiv_service: ArxivService,
                 ingestion_service: IngestionService,
                 vector_db_client: VectorDBClient, 
                 postdoc_agent: Optional[PostDocAgent] = None, 
                 checkpointer: Optional[BaseCheckpointSaver] = None
                 ):
        """Initializes the Research Orchestrator with necessary dependencies."""
        self.phd_agent = phd_agent
        self.postdoc_agent = postdoc_agent
        self.arxiv_service = arxiv_service
        self.ingestion_service = ingestion_service
        self.vector_db_client = vector_db_client
        self.checkpointer = checkpointer # Assign checkpointer passed in init
        
        self.workflow = StateGraph(GraphState)
        self._build_graph() # Build graph structure
        # Compile the graph using the checkpointer assigned to self
        self.graph = self.workflow.compile(checkpointer=self.checkpointer)
        # Remove redundant/incorrect assignment: self.graph_checkpointer = self.graph.checkpointer 
        logger.info("ResearchOrchestrator initialized and graph built.")

    def _build_graph(self):
        workflow = self.workflow

        # --- Define Nodes --- 
        workflow.add_node("initialize_workflow", initialize_workflow_node)
        workflow.add_node("formulate_search_queries", functools.partial(formulate_search_queries_node, phd_agent=self.phd_agent))
        workflow.add_node("execute_arxiv_search", functools.partial(execute_arxiv_search_node, arxiv_service=self.arxiv_service))
        workflow.add_node("score_paper_relevance", functools.partial(score_paper_relevance_node, phd_agent=self.phd_agent))
        workflow.add_node("create_initial_shortlist", create_initial_shortlist_node)
        workflow.add_node("request_shortlist_review", request_shortlist_review_node)
        workflow.add_node("processing_papers", functools.partial(process_and_ingest_papers_node, pdf_processor_class=PyPDF2Processor, ingestion_service=self.ingestion_service))
        workflow.add_node("literature_analysis", functools.partial(perform_literature_analysis_node, phd_agent=self.phd_agent, vector_db_client=self.vector_db_client))
        workflow.add_node("identify_research_gaps", functools.partial(identify_research_gaps_node, phd_agent=self.phd_agent))
        workflow.add_node("generate_research_directions", functools.partial(generate_research_directions_node, phd_agent=self.phd_agent))
        workflow.add_node("evaluate_research_directions", functools.partial(evaluate_research_directions_node, postdoc_agent=self.postdoc_agent, graph_checkpointer=self.checkpointer))
        workflow.add_node("refine_directions_based_on_assessment", functools.partial(refine_directions_based_on_assessment_node, phd_agent=self.phd_agent))
        workflow.add_node("prepare_final_output", prepare_final_output_node)
        workflow.add_node("resolve_conflict", resolve_conflict_node)
        
        # --- Define Edges --- 
        workflow.set_entry_point("initialize_workflow")

        # Standard flow
        workflow.add_edge("initialize_workflow", "formulate_search_queries")
        workflow.add_edge("formulate_search_queries", "execute_arxiv_search")
        workflow.add_edge("execute_arxiv_search", "score_paper_relevance")
        workflow.add_edge("score_paper_relevance", "create_initial_shortlist")
        workflow.add_edge("create_initial_shortlist", "request_shortlist_review")
        workflow.add_edge("request_shortlist_review", "processing_papers")
        workflow.add_edge("processing_papers", "literature_analysis")
        
        # Conditional edge after literature analysis
        workflow.add_conditional_edges(
            "literature_analysis",
            check_for_conflict, 
            {
                "conflict_found": "resolve_conflict",
                "no_conflict": "identify_research_gaps" 
            }
        )
        workflow.add_edge("resolve_conflict", "identify_research_gaps")

        # Refinement loop logic
        workflow.add_edge("identify_research_gaps", "generate_research_directions")
        workflow.add_edge("generate_research_directions", "evaluate_research_directions")
        workflow.add_conditional_edges(
            "evaluate_research_directions",
            should_refine_further, 
            {
                "refine_directions": "refine_directions_based_on_assessment",
                "finalize_output": "prepare_final_output" 
            }
        )
        workflow.add_edge("refine_directions_based_on_assessment", "evaluate_research_directions")

        # End point
        workflow.add_edge("prepare_final_output", END)

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

    async def resolve_conflict_node(self, state: GraphState) -> Dict[str, Any]:
        # ... (current detailed implementation) ...
        pass
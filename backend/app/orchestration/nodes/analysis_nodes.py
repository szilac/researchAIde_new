from typing import Dict, Any, Optional, List, Union
import traceback
import asyncio # Added for to_thread
import aiohttp # Added for async HTTP requests
import tempfile # Added for temporary files
from pathlib import Path # Added for path operations

from ..graph_state import GraphState
from app.models.message_models import AgentMessage, PerformativeType
from app.utils.logging_utils import get_logger
from langgraph.graph.message import add_messages

# Type hints for agents/services
from app.agents.phd_agent import PhDAgent
from app.services.pdf_processor import PyPDF2Processor
from app.services.ingestion_service import IngestionService
from app.models.operation_models import PaperRelevanceOutput, PaperRelevanceAssessment, LiteratureAnalysisOutput

# from langgraph.checkpoint.base import BaseCheckpointSaver # Needed if directly interacting with checkpointer

logger = get_logger(__name__)

async def score_paper_relevance_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "score_paper_relevance_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    scored_results_list = []
    try:
        raw_arxiv_results = state.get("raw_arxiv_results", [])
        research_query = state.get("research_query")

        if not research_query:
            raise ValueError("Research query is missing for paper relevance scoring.")
        if not phd_agent:
            raise ValueError("PhDAgent instance was not provided to score_paper_relevance_node.")

        if not raw_arxiv_results:
            logger.warning("No raw arXiv results to score. Skipping relevance assessment.")
            return {
                "scored_arxiv_results": [],
                "messages": add_messages(state.get("messages",[]), [AgentMessage(
                    conversation_id=str(session_id),
                    sender_agent_id=node_name,
                    performative="inform_result",
                    content={"status": "skipped_no_raw_results", "scored_count": 0}
                )]),\
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        logger.info(f"Calling PhDAgent to assess relevance of {len(raw_arxiv_results)} papers for query: '{research_query}'")
        
        for paper_data in raw_arxiv_results:
            paper_id = paper_data.get("arxiv_id") or paper_data.get("id")
            title = paper_data.get("title")
            abstract = paper_data.get("summary")

            if not all([paper_id, title, abstract]):
                logger.warning(f"Skipping paper due to missing id/arxiv_id, title, or summary: {paper_data}")
                continue

            paper_relevance_output: Optional[Dict] = await phd_agent.assess_paper_relevance(
                paper_id=str(paper_id),
                title=title,
                abstract=abstract,
                research_topic=research_query
            )

            assessments_list = paper_relevance_output.get("assessments") if paper_relevance_output else None
            if assessments_list:
                for assessment_data in assessments_list:
                    if isinstance(assessment_data, dict):
                        assessment_dict = assessment_data.copy()
                        assessment_dict["original_paper_identifier"] = paper_id
                        assessment_dict["original_title"] = title
                        scored_results_list.append(assessment_dict)
                    else:
                        logger.warning(f"Unexpected assessment data type in mock output: {type(assessment_data)}")
            else:
                logger.warning(f"PhDAgent.assess_paper_relevance returned None, empty assessments, or unexpected format for paper_id: {paper_id}. Output: {paper_relevance_output}")

        status_content = {
            "status": "paper_relevance_assessment_complete",
            "input_paper_count": len(raw_arxiv_results),
            "scored_paper_count": len(scored_results_list)
        }

        message_to_next_node = AgentMessage(
            conversation_id=str(session_id),
            sender_agent_id=node_name,
            performative="inform_result",
            content=status_content
        )

        return {
            "scored_arxiv_results": scored_results_list,
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "scored_arxiv_results": scored_results_list,
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

async def create_initial_shortlist_node(state: GraphState) -> Dict[str, Any]:
    node_name = "create_initial_shortlist_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        scored_results = state.get("scored_arxiv_results", [])
        config_params = state.get("config_parameters", {})
        shortlisting_threshold = config_params.get("relevance_shortlisting_threshold", 0.7)

        if not scored_results:
            logger.warning("No scored ArXiv results to create a shortlist from.")
            return {
                "initial_paper_shortlist": [],
                "messages": [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="status_update", content={"status": "Shortlist creation skipped, no scored results"})],
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        initial_shortlist = [
            paper for paper in scored_results
            if paper.get("relevance_score", 0.0) >= shortlisting_threshold
        ]
        
        shortlist_creation_message = AgentMessage(
            conversation_id=str(session_id),
            sender_agent_id=node_name,
            performative="inform_result",
            content={"status": "Initial paper shortlist created", "shortlist_count": len(initial_shortlist), "threshold_used": shortlisting_threshold}
        )
        return {
            "initial_paper_shortlist": initial_shortlist, 
            "messages": [shortlist_creation_message],
            "error_message": None, "error_source_node": None, "error_details": None
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "initial_paper_shortlist": [],
            "messages": [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})]
        }

async def request_shortlist_review_node(state: GraphState, graph_checkpointer: Optional[Any] = None) -> Dict[str, Any]:
    node_name = "request_shortlist_review_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        initial_shortlist = state.get("initial_paper_shortlist", [])
        research_query = state.get("research_query", "N/A")
        config_params = state.get("config_parameters", {})
        hitl_shortlist_review_active = config_params.get("hitl_shortlist_review_active", False)
        
        logger.info(f"Node {node_name}: Retrieved config_params: {config_params}")
        logger.info(f"Node {node_name}: Determined hitl_shortlist_review_active: {hitl_shortlist_review_active}")

        if not initial_shortlist:
            logger.warning("No initial paper shortlist for review. Auto-confirming empty list.")
            state_update = {
                "confirmed_paper_shortlist": [],
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="status_update", content={"status": "Shortlist review skipped, no papers"})]),
                "last_events": state.get("last_events", []) + [{"event_type": "ShortlistReviewNotRequired", "details": {"node": node_name, "reason": "Empty initial shortlist"}}],
                "is_waiting_for_shortlist_review": False,
                "error_message": None, "error_source_node": None, "error_details": None,
            }
            return state_update
            
        review_event_content = {}
        confirmed_shortlist_for_state = []

        can_interrupt = hitl_shortlist_review_active and graph_checkpointer is not None
        logger.info(f"Node {node_name}: Can interrupt check (HITL Active: {hitl_shortlist_review_active}, Checkpointer Provided: {graph_checkpointer is not None}) -> {can_interrupt}")

        if can_interrupt: 
            logger.info(f"INTERRUPT: Requesting human review for shortlist of {len(initial_shortlist)} papers for query: '{research_query}'")
            data_for_review = {
                "interrupt_type": "shortlist_review_required",
                "shortlisted_papers": initial_shortlist,
                "original_query": research_query,
                "message_to_human": f"Please review {len(initial_shortlist)} papers for '{research_query}'. Update 'confirmed_paper_shortlist' in state."
            }
            review_event_content = {"status": "human_review_requested", "papers_for_review_count": len(initial_shortlist), "data": data_for_review}
            confirmed_shortlist_for_state = []
            is_waiting_flag = True
            performative = "request_action"
        else:
            if not hitl_shortlist_review_active:
                logger.info("Simulating auto-confirmation: HITL not active.")
            elif graph_checkpointer is None:
                 logger.info("Simulating auto-confirmation: Checkpointer not available for interrupt.")
            else:
                 logger.info("Simulating auto-confirmation (unknown reason).")
            review_event_content = {"status": "shortlist_auto_confirmed", "papers_count": len(initial_shortlist)}
            confirmed_shortlist_for_state = initial_shortlist
            is_waiting_flag = False
            performative = "inform_result"

        review_event = AgentMessage(
            conversation_id=str(session_id),
            sender_agent_id=node_name,
            performative=performative,
            content=review_event_content
        )
        
        state_update_dict = {
            "confirmed_paper_shortlist": confirmed_shortlist_for_state, 
            "messages": add_messages(state.get("messages", []), [review_event]),
            "last_events": state.get("last_events", []) + [{"event_type": "ShortlistReviewProcessInitiated", "details": review_event_content}],
            "is_waiting_for_shortlist_review": is_waiting_flag,
            "error_message": None, "error_source_node": None, "error_details": None,
        }

        if is_waiting_flag:
            logger.info(f"Node {node_name}: Returning state dict, expecting graph interrupt.")
        else:
             logger.info(f"Node {node_name}: Returning state dict, expecting graph proceed.")
             
        return state_update_dict

    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "confirmed_paper_shortlist": [],
            "messages": [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})]
        }

async def process_and_ingest_papers_node(state: GraphState, pdf_processor_class: type[PyPDF2Processor], ingestion_service: IngestionService) -> Dict[str, Any]:
    node_name = "process_and_ingest_papers_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    ingestion_reports = []
    processed_paper_ids = []
    failed_paper_ids = []

    try:
        confirmed_shortlist = state.get("confirmed_paper_shortlist", [])
        
        if not pdf_processor_class:
            raise ValueError("PyPDF2Processor class was not provided.")
        if not ingestion_service:
            raise ValueError("IngestionService instance was not provided.")

        if not confirmed_shortlist:
            logger.warning("No confirmed shortlist for processing and ingestion.")
            return {
                "ingestion_reports": [], 
                "processed_paper_ids": [],
                "messages": add_messages(state.get("messages",[]),[AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="status_update", content={"status": "Processing/ingestion skipped, no confirmed shortlist"})]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }
        
        for paper_data in confirmed_shortlist:
            paper_id = paper_data.get("entry_id") or paper_data.get("id")
            paper_title = paper_data.get("title", "Unknown Title")
            paper_pdf_url = paper_data.get("pdf_url")

            if not paper_id or not paper_pdf_url:
                logger.warning(f"Skipping paper '{paper_title}' due to missing ID or PDF URL.")
                ingestion_reports.append({"paper_id": paper_id or "unknown", "title": paper_title, "status": "skipped_missing_data", "error": "Missing entry_id or pdf_url"})
                failed_paper_ids.append(paper_id or "unknown")
                continue
            
            try: 
                logger.info(f"Processing paper: {paper_title} ({paper_id}) via URL: {paper_pdf_url}")

                processor_instance = pdf_processor_class(pdf_url_or_path=paper_pdf_url)

                processed_content_output: Dict[str, Any] = await processor_instance.process()
                
                if "error" in processed_content_output or not processed_content_output.get("cleaned_text"):
                    error_detail = processed_content_output.get("error", "PDF processing returned no content or failed.")
                    raise ValueError(f"PDF processing failed: {error_detail}")
                logger.info(f"Processed {paper_title} successfully.")

                ingestion_metadata = {
                    "document_id": paper_id, "session_id": session_id, "title": paper_title,
                    "source_url": paper_pdf_url, "original_arxiv_id": paper_data.get("id"),
                    "authors": paper_data.get("authors", []),
                    "published_date": paper_data.get("published"),
                    "pdf_structure_summary": processed_content_output.get("structure", {}),
                    **(paper_data.get("metadata", {})), 
                    "processing_source_filename": processed_content_output.get("source_filename")
                }
                logger.info(f"Ingesting paper: {paper_title} ({paper_id})")
                collection_name = f"session_{session_id}_papers"
                ingestion_result = await ingestion_service.ingest_document(
                    session_id=session_id, document_id=paper_id,
                    document_text=processed_content_output['cleaned_text'],
                    document_metadata=ingestion_metadata 
                )
                
                ingestion_status = "success"
                ingestion_detail_message = "Successfully ingested."
                if isinstance(ingestion_result, dict):
                    ingestion_status = ingestion_result.get("status", "success")
                    ingestion_detail_message = ingestion_result.get("detail", "Successfully ingested.")
                elif not ingestion_result:
                    ingestion_status = "failed"
                    ingestion_detail_message = "Ingestion service reported failure."

                if ingestion_status != "success":
                     raise ValueError(f"Ingestion failed: {ingestion_detail_message}")

                ingestion_reports.append({"paper_id": paper_id, "title": paper_title, "status": ingestion_status, "detail": ingestion_detail_message})
                processed_paper_ids.append(paper_id)
                logger.info(f"Successfully processed and ingested {paper_title} ({paper_id}).")

            except Exception as paper_error:
                logger.error(f"!!! ERROR processing/ingesting paper {paper_title} ({paper_id}): {paper_error} !!!", exc_info=False)
                ingestion_reports.append({"paper_id": paper_id, "title": paper_title, "status": "failed", "error": str(paper_error)})
                failed_paper_ids.append(paper_id)
        
        completion_message_content = {"status": "Paper processing/ingestion phase complete", "total_processed": len(processed_paper_ids), "total_failed": len(failed_paper_ids), "reports_count": len(ingestion_reports)}
        processing_ingestion_done_message = AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="inform_result", content=completion_message_content)
        
        return {
            "ingestion_reports": ingestion_reports,
            "processed_paper_ids": processed_paper_ids,
            "messages": add_messages(state.get("messages",[]),[processing_ingestion_done_message]),
            "error_message": None, "error_source_node": None, "error_details": None
        }

    except Exception as e:
        logger.error(f"!!! ERROR in {node_name} (Outer Scope): {e} !!!", exc_info=True)
        error_agent_message = AgentMessage(
            conversation_id=str(session_id), 
            sender_agent_id=node_name, 
            performative="error_report", 
            content={"error": str(e), "details": "Error in node setup."}
        )
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "ingestion_reports": ingestion_reports, 
            "processed_paper_ids": processed_paper_ids, 
            "messages": add_messages(state.get("messages",[]),[error_agent_message])
        }

async def perform_literature_analysis_node(state: GraphState, phd_agent: PhDAgent, vector_db_client: Any) -> Dict[str, Any]:
    node_name = "perform_literature_analysis_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        ingestion_reports = state.get("ingestion_reports", [])
        research_query = state.get("research_query")
        processed_paper_ids = state.get("processed_paper_ids", [])

        if not research_query:
            raise ValueError("Research query is missing for literature analysis.")
        if not phd_agent:
            raise ValueError("PhDAgent was not provided.")
        if not vector_db_client:
            logger.warning("VectorDBClient not directly provided to node, PhDAgent is responsible for its usage.")

        collection_name = f"session_{session_id}_papers"
        successfully_ingested_count = sum(1 for report in ingestion_reports if report.get("status") == "success")
        
        if successfully_ingested_count == 0:
            logger.warning("No papers successfully ingested. Skipping literature analysis.")
            message_content = {"status": "skipped_no_ingested_content", "papers_analyzed": 0}
            return {
                "literature_analysis_output": message_content, 
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="inform_result", content=message_content)]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        logger.info(f"Calling PhDAgent to analyze literature for query: '{research_query}' in collection: '{collection_name}' based on {successfully_ingested_count} papers.")

        analysis_output_model: Optional[LiteratureAnalysisOutput] = await phd_agent.analyze_literature(
            research_query=research_query,
            collection_name=collection_name
        )
        
        analysis_output_dict = None
        if analysis_output_model and hasattr(analysis_output_model, 'model_dump'):
            analysis_output_dict = analysis_output_model.model_dump(exclude_none=True)
            if "status" not in analysis_output_dict:
                analysis_output_dict["status"] = "analysis_complete"
        else:
            phd_agent.logger.warning("PhDAgent.analyze_literature returned None or unexpected format.")
            analysis_output_dict = {"status": "analysis_failed_agent_output_issue", "analyzed_papers_summary": "Agent did not return valid analysis.", "key_themes": [], "overall_summary": ""}
 
        message_to_next_node = AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="inform_result", content=analysis_output_dict)

        return {
            "literature_analysis_output": analysis_output_dict,
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "literature_analysis_output": {"status": "analysis_error", "error_message": str(e)},
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

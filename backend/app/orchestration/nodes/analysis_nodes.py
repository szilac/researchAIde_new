\
from typing import Dict, Any, Optional, List
import traceback

from ..graph_state import GraphState
from backend.app.models.message_models import AgentMessage, PerformativeType
from backend.app.utils.logging_utils import get_logger # Assuming a shared logger

# Type hints for agents/services
from backend.app.agents.phd_agent import PhDAgent, AssessedPaperRelevance, LiteratureAnalysisOutput
from backend.app.services.pdf_processor import PyPDF2Processor
from backend.app.services.ingestion_service import IngestionService
# from langgraph.checkpoint.base import BaseCheckpointSaver # Needed if directly interacting with checkpointer

logger = get_logger(__name__)

async def score_paper_relevance_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "score_paper_relevance_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
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
                    conversation_id=session_id,
                    sender_agent_id=node_name,
                    performative=PerformativeType.INFORM_RESULT,
                    content={"status": "skipped_no_raw_results", "scored_count": 0}
                )]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        logger.info(f"Calling PhDAgent to assess relevance of {len(raw_arxiv_results)} papers for query: '{research_query}'")
        
        assessed_papers_output: Optional[List[AssessedPaperRelevance]] = await phd_agent.assess_papers_relevance(
            papers_to_assess=raw_arxiv_results, 
            research_query=research_query
        )

        scored_results_list = []
        if assessed_papers_output:
            for assessed_paper_model in assessed_papers_output:
                if hasattr(assessed_paper_model, 'model_dump'):
                    scored_results_list.append(assessed_paper_model.model_dump(exclude_none=True))
                elif isinstance(assessed_paper_model, dict):
                    scored_results_list.append(assessed_paper_model)
                else:
                    phd_agent.logger.warning(f"Unexpected assessed paper model type: {type(assessed_paper_model)}")
        else:
            phd_agent.logger.warning("PhDAgent.assess_papers_relevance returned None or empty list.")

        status_content = {
            "status": "paper_relevance_assessment_complete",
            "input_paper_count": len(raw_arxiv_results),
            "scored_paper_count": len(scored_results_list)
        }

        message_to_next_node = AgentMessage(
            conversation_id=session_id,
            sender_agent_id=node_name,
            performative=PerformativeType.INFORM_RESULT,
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
            "scored_arxiv_results": [],
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})])
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
                "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_STATUS, content={"status": "Shortlist creation skipped, no scored results"})],
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        initial_shortlist = [
            paper for paper in scored_results
            if paper.get("relevance_score", 0.0) >= shortlisting_threshold
        ]
        
        shortlist_creation_message = AgentMessage(
            conversation_id=session_id,
            sender_agent_id=node_name,
            performative=PerformativeType.INFORM_RESULT,
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
            "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})]
        }

async def request_shortlist_review_node(state: GraphState, graph_checkpointer: Optional[Any] = None) -> Dict[str, Any]: # graph_checkpointer type: Optional[BaseCheckpointSaver]
    node_name = "request_shortlist_review_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        initial_shortlist = state.get("initial_paper_shortlist", [])
        research_query = state.get("research_query", "N/A")

        if not initial_shortlist:
            logger.warning("No initial paper shortlist for review. Auto-confirming empty list.")
            return {
                "confirmed_paper_shortlist": [],
                "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_STATUS, content={"status": "Shortlist review skipped, no papers"})],
                "last_events": [{"event_type": "ShortlistReviewNotRequired", "details": {"node": node_name, "reason": "Empty initial shortlist"}}],
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        config_params = state.get("config_parameters", {})
        hitl_shortlist_review_active = config_params.get("hitl_shortlist_review_active", False)

        review_event_content = {}
        confirmed_shortlist_for_state = []

        if hitl_shortlist_review_active and graph_checkpointer: 
            logger.info(f"INTERRUPT: Requesting human review for shortlist of {len(initial_shortlist)} papers for query: '{research_query}'")
            # Actual interruption would be raised by the graph engine if this node returns a special Send value or similar mechanism
            # from langgraph.interrupt import Interrupt; raise Interrupt()
            data_for_review = {
                "interrupt_type": "shortlist_review_required",
                "shortlisted_papers": initial_shortlist,
                "original_query": research_query,
                "message_to_human": f"Please review {len(initial_shortlist)} papers for '{research_query}'. Update 'confirmed_paper_shortlist' in state."
            }
            review_event_content = {"status": "human_review_requested", "papers_for_review_count": len(initial_shortlist), "data": data_for_review}
            # When truly interrupting, confirmed_shortlist_for_state remains empty, to be filled by external update.
            # For this example, if an interrupt mechanism isn't fully in place via how LangGraph calls this,
            # the graph would just proceed. If it *is* truly interrupted, this 'return' is for the state *before* interrupt.
            confirmed_shortlist_for_state = [] 
        else:
            logger.info("Simulating auto-confirmation of initial shortlist (HITL not active or no checkpointer).")
            review_event_content = {"status": "shortlist_auto_confirmed", "papers_count": len(initial_shortlist)}
            confirmed_shortlist_for_state = initial_shortlist

        review_event = AgentMessage(
            conversation_id=session_id,
            sender_agent_id=node_name,
            performative=PerformativeType.REQUEST_ACTION,
            content=review_event_content
        )
        
        return {
            "confirmed_paper_shortlist": confirmed_shortlist_for_state, 
            "messages": [review_event],
            "last_events": [{"event_type": "ShortlistReviewProcessInitiated", "details": review_event_content}],
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "confirmed_paper_shortlist": [],
            "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})]
        }

async def process_and_ingest_papers_node(state: GraphState, pdf_processor_service: PyPDF2Processor, ingestion_service: IngestionService) -> Dict[str, Any]:
    node_name = "process_and_ingest_papers_node"
    logger.info(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    ingestion_reports = []
    processed_paper_ids = []
    failed_paper_ids = []

    try:
        confirmed_shortlist = state.get("confirmed_paper_shortlist", [])
        
        if not pdf_processor_service:
            raise ValueError("PDFProcessorService was not provided to process_and_ingest_papers_node.")
        if not ingestion_service:
            raise ValueError("IngestionService was not provided to process_and_ingest_papers_node.")

        if not confirmed_shortlist:
            logger.warning("No confirmed shortlist for processing and ingestion.")
            return {
                "ingestion_reports": [], 
                "processed_paper_ids": [],
                "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_STATUS, content={"status": "Processing/ingestion skipped, no confirmed shortlist"})],
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
                logger.info(f"Processing paper: {paper_title} ({paper_id})")
                # Actual call to pdf_processor_service
                # processed_content_output = await pdf_processor_service.process_pdf(paper_pdf_url, paper_id)
                logger.info(f"[Mock] Simulating PDF processing for {paper_pdf_url}")
                mock_text_content = f"Simulated processed text for {paper_title}. Abstract: {paper_data.get('summary', '')}."
                processed_content_output = {
                    "text_content": mock_text_content,
                    "metadata": {"source_id": paper_id, "title": paper_title, "url": paper_pdf_url},
                    "page_chunks": [mock_text_content[i:i+500] for i in range(0, len(mock_text_content), 500)]
                }
                logger.info(f"[Mock] PDF processing complete for {paper_id}")

                if not processed_content_output or not processed_content_output.get("text_content"):
                    raise ValueError("PDF processing returned no content.")

                logger.info(f"Ingesting paper: {paper_title} ({paper_id})")
                # Actual call to ingestion_service
                # collection_name = f"session_{session_id}_papers" # Define collection name
                # ingestion_result = await ingestion_service.ingest_document(collection_name=collection_name, content=processed_content_output['text_content'], metadata=processed_content_output['metadata'])
                mock_ingestion_status = "success"
                mock_vector_ids_count = len(processed_content_output.get("page_chunks", []))
                ingestion_report_detail = {"paper_id": paper_id, "title": paper_title, "status": mock_ingestion_status, "detail": f"Successfully ingested with {mock_vector_ids_count} vector chunks."}
                logger.info(f"[Mock] Ingestion complete for {paper_id}")
                
                ingestion_reports.append(ingestion_report_detail)
                processed_paper_ids.append(paper_id)

            except Exception as paper_processing_error:
                logger.error(f"!!! ERROR processing/ingesting paper {paper_title} ({paper_id}): {paper_processing_error} !!!", exc_info=True)
                ingestion_reports.append({"paper_id": paper_id, "title": paper_title, "status": "failed", "error": str(paper_processing_error)})
                failed_paper_ids.append(paper_id)
        
        completion_message_content = {"status": "Paper processing/ingestion phase complete", "total_processed": len(processed_paper_ids), "total_failed": len(failed_paper_ids), "reports_count": len(ingestion_reports)}
        processing_ingestion_done_message = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_RESULT, content=completion_message_content)
        
        return {
            "ingestion_reports": ingestion_reports,
            "processed_paper_ids": processed_paper_ids,
            "messages": [processing_ingestion_done_message],
            "error_message": None, "error_source_node": None, "error_details": None
        }
    except Exception as e:
        logger.error(f"!!! ERROR in {node_name}: {e} !!!", exc_info=True)
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "ingestion_reports": ingestion_reports,
            "processed_paper_ids": processed_paper_ids,
            "messages": [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})]
        }

async def perform_literature_analysis_node(state: GraphState, phd_agent: PhDAgent, vector_db_client: Any) -> Dict[str, Any]: # vector_db_client type hint: VectorDBClient
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
        if not vector_db_client: # Check if vector_db_client is provided (though PhDAgent might encapsulate it)
            logger.warning("VectorDBClient not directly provided to node, PhDAgent is responsible for its usage.")

        collection_name = f"session_{session_id}_papers"
        successfully_ingested_count = sum(1 for report in ingestion_reports if report.get("status") == "success")
        
        if successfully_ingested_count == 0:
            logger.warning("No papers successfully ingested. Skipping literature analysis.")
            message_content = {"status": "skipped_no_ingested_content", "papers_analyzed": 0}
            return {
                "literature_analysis_output": message_content, 
                "messages": add_messages(state.get("messages",[]), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_RESULT, content=message_content)]),
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        logger.info(f"Calling PhDAgent to analyze literature for query: '{research_query}' in collection: '{collection_name}' based on {successfully_ingested_count} papers.")

        analysis_output_model: Optional[LiteratureAnalysisOutput] = await phd_agent.analyze_literature(
            research_query=research_query,
            collection_name=collection_name # PhDAgent.analyze_literature uses this to interact with VectorDB
        )
        
        analysis_output_dict = None
        if analysis_output_model and hasattr(analysis_output_model, 'model_dump'):
            analysis_output_dict = analysis_output_model.model_dump(exclude_none=True)
            if "status" not in analysis_output_dict:
                analysis_output_dict["status"] = "analysis_complete"
        else:
            phd_agent.logger.warning("PhDAgent.analyze_literature returned None or unexpected format.")
            analysis_output_dict = {"status": "analysis_failed_agent_output_issue", "analyzed_papers_summary": "Agent did not return valid analysis.", "key_themes": [], "overall_summary": ""}
 
        message_to_next_node = AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.INFORM_RESULT, content=analysis_output_dict)

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
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=session_id, sender_agent_id=node_name, performative=PerformativeType.ERROR_REPORT, content={"error": str(e)})])
        }

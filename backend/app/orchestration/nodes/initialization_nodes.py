from typing import Dict, Any, Optional, List
import uuid
import traceback
import asyncio # Add asyncio import

# Imports from our new modules
from ..graph_state import GraphState # Relative import from parent directory
from app.models.message_models import AgentMessage, PerformativeType
from langgraph.graph.message import add_messages

# Type hints for agents/services (actual instances will be passed in)
from app.agents.phd_agent import PhDAgent, FormulatedQueriesOutput
from app.services.arxiv_service import ArxivService

async def initialize_workflow_node(state: GraphState) -> Dict[str, Any]:
    node_name = "initialize_workflow_node"
    print(f"--- Node: {node_name} (Standalone Function) ---")
    session_id_from_state = state.get("session_id") # Get potential incoming session ID
    try:
        research_query = state.get("research_query")
        general_area = state.get("general_area")
        if not research_query:
            # Ensure session_id is determined even in error path if possible
            determined_session_id = session_id_from_state or f"session_{uuid.uuid4()}_error_init"
            raise ValueError("Research query is missing in the initial state.")

        # If no error yet, determine session_id
        session_id = session_id_from_state or f"session_{uuid.uuid4()}"
        
        initial_phd_prompt = (
            f"The primary research query is: '{research_query}'. "
            f"Please formulate a set of targeted search queries for academic databases like ArXiv, "
            f"1. Identify the core keywords and concepts within the topic."
            f"2. Consider relevant synonyms and related terms for these concepts."
            f"3. You MUST generate exactly one (1) search query suitable for Arxiv."
            f"4. Optimize the query for keyword relevance and comprehensiveness. Use boolean operators (AND, OR, NOT) and field codes (e.g., ti: for title, abs: for abstract) where appropriate to focus the search."
        )

        system_message = AgentMessage(
            conversation_id=str(session_id),
            sender_agent_id="SystemInitializer",
            performative="inform_state",
            content={"status": "Workflow initialized", "query": research_query, "session_id": session_id}
        )
        
        return {
            "session_id": session_id,
            "research_query": research_query,
            "general_area": general_area,
            "initial_phd_prompt": initial_phd_prompt,
            "iteration_count": 0,
            "retry_attempts": {},
            "messages": [system_message],
            "error_message": None,
            "error_source_node": None,
            "error_details": None,
        }
    except Exception as e:
        print(f"!!! ERROR in {node_name}: {e} !!!")
        # Ensure the determined session_id (or a default) is in the error output
        # Use determined_session_id if the error happened after it was set, otherwise fallback
        session_id_for_error = determined_session_id if 'determined_session_id' in locals() else (session_id_from_state or "unknown_session_init_error")
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "session_id": session_id_for_error # Correctly pass session_id in error state
        }

async def formulate_search_queries_node(state: GraphState, phd_agent: PhDAgent) -> Dict[str, Any]:
    node_name = "formulate_search_queries_node"
    print(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        research_topic = state.get("research_query")
        general_area = state.get("general_area")
        # config_params = state.get("config_parameters", {})
        # general_area = config_params.get("general_area_for_query_formulation")

        if not research_topic:
            raise ValueError("Research query/topic is missing in state for query formulation.")
        if not phd_agent:
            raise ValueError("PhDAgent instance was not provided to formulate_search_queries_node.")

        print(f"  Calling PhDAgent to formulate search queries for topic: '{research_topic}' (General Area: {general_area})")
        
        formulated_output: Optional[FormulatedQueriesOutput] = await phd_agent.formulate_search_queries(
            research_topic=research_topic,
            general_area=general_area
        )
        
        constructed_queries_list = []
        agent_original_topic = None # Initialize

        if formulated_output and isinstance(formulated_output.queries, list):
            agent_original_topic = formulated_output.original_topic # Attribute access
            for query_info in formulated_output.queries:
                if hasattr(query_info, 'model_dump'):
                    constructed_queries_list.append(query_info.model_dump(mode='json'))
                elif isinstance(query_info, dict): # Fallback if it's already a dict somehow
                    constructed_queries_list.append(query_info)
                else:
                    phd_agent.logger.warning(f"Unexpected query info type in list: {type(query_info)}")
        else:
            phd_agent.logger.warning(f"PhDAgent output format unexpected/empty or queries not a list: {formulated_output}")
            if not formulated_output:
                 phd_agent.logger.error("PhDAgent returned None for query formulation.")
                 # Ensure agent_original_topic is None if formulated_output is None
                 agent_original_topic = None 

        if not constructed_queries_list:
             phd_agent.logger.warning("No search queries were formulated by PhDAgent.")

        status_content = {"status": "query_formulation_complete", "query_count": len(constructed_queries_list)}
        if agent_original_topic and agent_original_topic != research_topic:
            status_content["original_topic_in_agent_output"] = agent_original_topic

        message_to_next_node = AgentMessage(
            conversation_id=str(session_id), # Cast to string
            sender_agent_id=node_name,
            performative="inform_result",
            content=status_content
        )
        
        return {
            "constructed_queries": constructed_queries_list,
            "messages": add_messages(state.get("messages", []), [message_to_next_node]),
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        print(f"!!! ERROR in {node_name}: {e} !!!")
        if phd_agent:
            phd_agent.logger.error(f"Error in {node_name}: {e}", exc_info=True)
        else:
            traceback.print_exc()
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "constructed_queries": [], 
            "messages": add_messages(state.get("messages", []), [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})])
        }

async def execute_arxiv_search_node(state: GraphState, arxiv_service: ArxivService) -> Dict[str, Any]:
    node_name = "execute_arxiv_search_node"
    print(f"--- Node: {node_name} (Standalone Function) ---")
    session_id = state.get("session_id", "unknown_session")
    try:
        constructed_queries = state.get("constructed_queries")
        
        if not arxiv_service:
            raise ValueError("ArxivService instance was not provided to execute_arxiv_search_node.")

        if not constructed_queries or not isinstance(constructed_queries, list) or not constructed_queries:
            print("Warning: No valid constructed queries for ArXiv search. Skipping.")
            return {
                "raw_arxiv_results": [], 
                "search_execution_status": "skipped_no_valid_queries",
                "messages": [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="status_update", content={"status": "ArXiv search skipped, no valid queries"})],
                "error_message": None, "error_source_node": None, "error_details": None,
            }

        all_results: List[Dict[str, Any]] = []
        search_status = "success_partial_results"
        
        config_params = state.get("config_parameters", {})
        max_results_per_query = config_params.get("max_arxiv_results_per_query", 5)
        # sort_by = config_params.get("arxiv_sort_by", "relevance")
        # sort_order = config_params.get("arxiv_sort_order", "descending")

        for query_info in constructed_queries:
            query_string = query_info.get("query_string")
            if not query_string:
                print(f"Warning: Skipping query with no query_string: {query_info}")
                continue
            
            print(f"  Searching ArXiv for: '{query_string}' (max: {max_results_per_query})")
            try:
                # Run the synchronous search_papers call in a separate thread
                papers: List[Dict[str, Any]] = await asyncio.to_thread(
                    arxiv_service.search_papers,
                    query=query_string, 
                    max_results=max_results_per_query,
                    # sort_by=sort_by, # Pass these if you re-enable them
                    # sort_order=sort_order 
                )
                if papers:
                    all_results.extend(papers)
                    print(f"    Found {len(papers)} papers for '{query_string}'.")
                else:
                    print(f"    No papers found for query: '{query_string}'.")
            except Exception as query_e:
                print(f"  Error searching ArXiv for query '{query_string}': {query_e}")
        
        if not all_results:
            search_status = "success_no_results_found"
        elif len(all_results) > 0:
            search_status = "success_found_results"
        
        search_done_message = AgentMessage(
            conversation_id=str(session_id),
            sender_agent_id=node_name,
            performative="inform_result",
            content={"status": search_status, "results_count": len(all_results)}
        )
        return {
            "raw_arxiv_results": all_results,
            "search_execution_status": search_status,
            "messages": [search_done_message],
            "error_message": None, "error_source_node": None, "error_details": None,
        }
    except Exception as e:
        print(f"!!! ERROR in {node_name}: {e} !!!")
        return {
            "error_message": str(e),
            "error_source_node": node_name,
            "error_details": traceback.format_exc(),
            "raw_arxiv_results": [],
            "search_execution_status": "error_in_execution",
            "messages": [AgentMessage(conversation_id=str(session_id), sender_agent_id=node_name, performative="error_report", content={"error": str(e)})]
        }

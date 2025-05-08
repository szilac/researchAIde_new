# backend/tests/integration/orchestration/test_research_orchestrator_flows.py
"""Integration tests for ResearchOrchestrator flows and state transitions."""
import pytest
from unittest.mock import MagicMock
from app.orchestration.orchestrator import ResearchOrchestrator
from app.orchestration.graph_state import GraphState
from app.models.operation_models import OrchestratorInputModel
from app.models.message_models import AgentMessage
from backend.tests.utils.mock_services import (
    MockPhDAgent,
    MockPostDocAgent,
    MockArxivService,
    MockPyPDF2Processor,
    MockIngestionService,
    MockVectorDBClient,
)
import logging

# LangGraph imports
from langgraph.graph.state import CompiledStateGraph

@pytest.fixture
def mock_dependencies():
    """Provides a dictionary of mock dependencies for the ResearchOrchestrator."""
    return {
        "phd_agent": MockPhDAgent(),
        "postdoc_agent": MockPostDocAgent(),
        "arxiv_service": MockArxivService(),
        "pdf_processor_service": MockPyPDF2Processor(),
        "ingestion_service": MockIngestionService(),
        "vector_db_client": MockVectorDBClient(),
        "logger": MagicMock(), # Using a generic MagicMock for the logger for now
    }

@pytest.fixture
def research_orchestrator(mock_dependencies):
    """Initializes ResearchOrchestrator with mock dependencies."""
    # Ensure logger is handled correctly - added to __init__ recently
    resolved_logger = mock_dependencies["logger"] or logging.getLogger("TestOrchestrator") 
    
    return ResearchOrchestrator(
        phd_agent=mock_dependencies["phd_agent"],
        arxiv_service=mock_dependencies["arxiv_service"],
        pdf_processor_service=mock_dependencies["pdf_processor_service"],
        ingestion_service=mock_dependencies["ingestion_service"],
        vector_db_client=mock_dependencies["vector_db_client"],
        postdoc_agent=mock_dependencies["postdoc_agent"]
    )

def test_orchestrator_initialization_and_graph_compilation(research_orchestrator):
    """
    Tests that the ResearchOrchestrator initializes correctly and its graph compiles.
    """
    assert research_orchestrator is not None
    assert research_orchestrator.graph is not None
    # The graph is already compiled in __init__, just assert its existence
    assert isinstance(research_orchestrator.graph, CompiledStateGraph) # Optional: check type
    print("ResearchOrchestrator initialized and graph compiled successfully.")

@pytest.mark.asyncio
async def test_orchestrator_simple_flow_invocation(research_orchestrator, mock_dependencies):
    """
    Tests a very simple invocation of the orchestrator graph to ensure it runs.
    This will likely hit the first few nodes which are mostly placeholders.
    """
    initial_input = OrchestratorInputModel(user_id="test_user", conversation_id="conv_123", query="Initial research query", session_id="test_session_001")
    graph_input = GraphState(
        initial_input=initial_input,
        research_query=initial_input.query,
        session_id=initial_input.session_id,
        query_understanding={},
        search_queries=[],
        search_results=[],
        analyzed_papers=[],
        shortlisted_papers=[],
        processed_documents=[],
        research_gaps=[],
        research_directions=[],
        refined_directions=[],
        final_report=None,
        critique_request_details=None,
        critique_results=None,
        evaluation_results=None,
        messages=[AgentMessage(
            conversation_id=initial_input.conversation_id, 
            sender_agent_id="TestClient", 
            performative="request_action",
            content={"action": "start_workflow", "details": "Starting test flow"}
        )]
    )

    # Mock the methods that will be called by the first few nodes if they do more than log
    # For now, our mock services have basic async returns.

    try:
        # Invoke graph - GraphState is a TypedDict, pass it directly
        final_state = await research_orchestrator.graph.ainvoke(graph_input)
        assert final_state is not None
        # Add more specific assertions based on expected final state after placeholder nodes
        assert "messages" in final_state
        assert len(final_state["messages"]) > 1 # Expect at least one new message from a node
        print(f"Graph invoked. Final state messages: {final_state['messages']}")
    except Exception as e:
        pytest.fail(f"Graph invocation failed: {e}")

# Add more tests here for specific paths, conditional logic, etc.

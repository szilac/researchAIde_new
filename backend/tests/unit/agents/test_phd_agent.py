import pytest
import pytest_asyncio
import os
from typing import List
from pathlib import Path

# Adjust imports based on your project structure and where pytest is run from
try:
    from backend.app.agents.phd_agent import (
        PhDAgent,
        PhDAgentDependencies,
        FormulatedQueriesOutput,
    )
    from backend.app.services.llm.prompt_manager import PromptManager
    from langchain_core.messages import AIMessage

except ImportError:
    from app.agents.phd_agent import (
        PhDAgent,
        PhDAgentDependencies,
        FormulatedQueriesOutput,
    )
    from app.services.llm.prompt_manager import PromptManager

# Determine the base path relative to the test file location
_TEST_DIR = Path(__file__).parent
_PROMPT_DIR = _TEST_DIR.parent.parent.parent / "app" / "agents" / "prompts"

# --- Test Fixtures ---

@pytest.fixture(scope="module") # Scope module to load templates once per test module
def prompt_manager():
    """Fixture to provide an initialized PromptManager."""
    if not _PROMPT_DIR.exists():
        pytest.fail(f"Prompt directory not found: {_PROMPT_DIR.resolve()}")
    try:
        manager = PromptManager(template_dir=str(_PROMPT_DIR / "phd"))
        # Ensure essential templates are loaded
        assert 'phd_query_formulation' in manager._templates
        assert 'phd_relevance_assessment' in manager._templates
        assert 'phd_literature_analyzer' in manager._templates
        assert 'phd_gap_identification' in manager._templates
        return manager
    except Exception as e:
        pytest.fail(f"Failed to initialize PromptManager: {e}")

@pytest.fixture
def phd_agent_deps(prompt_manager): # Depend on the prompt_manager fixture
    """Fixture to provide PhDAgentDependencies with PromptManager."""
    return PhDAgentDependencies(
        prompt_manager=prompt_manager,
        arxiv_service=None, 
        chromadb_service=None, 
        llm_manager=None
    )

# --- Test Cases ---

# Mark the test to skip if the GOOGLE_API_KEY is not set
google_api_key_present = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"), 
    reason="GOOGLE_API_KEY environment variable not set. Skipping live LLM test."
)

@google_api_key_present
@pytest.mark.asyncio
async def test_formulate_search_queries_live(phd_agent_deps):
    """Tests the formulate_search_queries method with a live LLM call, using PromptManager."""
    print("\n--- Running test_formulate_search_queries_live ---")
    # 1. Setup
    # phd_agent_deps fixture now includes the loaded prompt_manager
    agent = PhDAgent(dependencies=phd_agent_deps, llm_model_name="google-gla:gemini-1.5-flash")
    test_topic = "Using large language models for automated theorem proving in mathematics"
    test_area = "Artificial Intelligence in Mathematics"
    
    print(f"Test Topic: {test_topic}")
    print(f"Test Area: {test_area}")

    # 2. Execute
    try:
        result = await agent.formulate_search_queries(research_topic=test_topic, general_area=test_area)
        
        # 3. Assertions
        assert isinstance(result, FormulatedQueriesOutput)
        assert result.original_topic == test_topic
        assert isinstance(result.queries, List)
        # Agent method is now designed to return exactly one query.
        assert len(result.queries) == 1, f"Expected 1 query, but got {len(result.queries)}"
        
        print("\n--- Formulated Queries --- (Live LLM Test)")
        for i, query in enumerate(result.queries):
            assert query.query_string is not None
            assert len(query.query_string) > 5 # Basic sanity check
            assert query.source_topic == test_topic
            print(f"Query {i+1}: {query.query_string}")
        
        print("Assertion checks passed.")

    except Exception as e:
        pytest.fail(f"PhDAgent.formulate_search_queries raised an exception: {e}")
    
    print("--- Test Finished --- \n")

# --- Mocked Tests ---

def test_phd_agent_process_simple_response(phd_agent_deps, mock_simple_ai_response):
    """Tests a hypothetical _process_llm_response method with a mocked simple AIMessage."""
    print("\n--- Running test_phd_agent_process_simple_response ---")
    # 1. Setup
    agent = PhDAgent(dependencies=phd_agent_deps, llm_model_name="mock_model") # Using a mock model name

    # Hypothetical method on PhDAgent that processes an AIMessage
    # We'll assume it just returns the content string for this example.
    def _mock_process_llm_response(response: AIMessage) -> str:
        return response.content

    # Monkeypatch this hypothetical method onto the agent instance for this test
    agent._process_llm_response = _mock_process_llm_response

    # 2. Execute
    # mock_simple_ai_response is provided by the fixture from conftest.py
    processed_content = agent._process_llm_response(mock_simple_ai_response)

    # 3. Assertions
    assert isinstance(processed_content, str)
    assert processed_content == "This is a default mock AI response."
    print(f"Processed Content: {processed_content}")
    print("Assertion checks passed.")
    print("--- Test Finished --- \n")

# TODO: Add tests for other methods (assess_paper_relevance, analyze_literature, identify_research_gaps)
# These will likely require mocking the respective agents (_relevance_assessment_agent, etc.)
# or providing mock LLM responses if not testing live LLM interaction for those.

# Add more tests here for other PhDAgent methods, potentially using mocks
# for dependencies like ArxivService and ChromaDBService. 
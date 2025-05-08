from functools import lru_cache
import logging

# Orchestrator and its direct dependencies
from app.orchestration.orchestrator import ResearchOrchestrator
from app.agents.phd_agent import PhDAgent
from app.agents.postdoc_agent import PostDocAgent
from app.services.arxiv_service import ArxivService
from app.services.ingestion_service import IngestionService
from app.services.vector_db_client import VectorDBClient
from app.services.pdf_processor import PyPDF2Processor # Assuming this is the chosen one

# LLM related imports for agent instantiation (simplified)
from app.services.llm.llm_manager import LLMManager
from app.models.llm_config import LLMConfig

# Checkpointer
from langgraph.checkpoint.memory import MemorySaver # Using MemorySaver for simplicity

logger = logging.getLogger(__name__)

# This would ideally load from a global app config or environment variables
# For simplicity, API keys are expected to be in the environment for LLMManager to pick up
GOOGLE_DEFAULT_MODEL_FLASH = "gemini-1.5-flash-lite"
GOOGLE_DEFAULT_MODEL_PRO = "gemini-2.0-flash-lite"


@lru_cache()
def get_checkpointer():
    """Provides a singleton MemorySaver checkpointer."""
    logger.info("Initializing MemorySaver checkpointer.")
    return MemorySaver()

@lru_cache()
def get_vector_db_client():
    """Provides a singleton VectorDBClient."""
    # In a real app, configuration (path, collection name) would come from settings
    logger.info("Initializing VectorDBClient.")
    return VectorDBClient(collection_name="research_papers_prod", embedding_model_name="text-embedding-004")

@lru_cache()
def get_ingestion_service():
    """Provides a singleton IngestionService."""
    logger.info("Initializing IngestionService.")
    return IngestionService(vector_db_client=get_vector_db_client())

@lru_cache()
def get_arxiv_service():
    """Provides a singleton ArxivService."""
    logger.info("Initializing ArxivService.")
    return ArxivService()

@lru_cache()
def get_llm_manager():
    """Provides a singleton LLMManager."""
    logger.info("Initializing LLMManager.")
    return LLMManager()

@lru_cache()
def get_phd_agent():
    """Provides a singleton PhDAgent, configured with a default LLM."""
    logger.info(f"Initializing PhDAgent with Google provider and model {GOOGLE_DEFAULT_MODEL_FLASH}.")
    try:
        manager = get_llm_manager()
        # LLMConfig will try to load API keys from environment by default
        config = LLMConfig(model_name=GOOGLE_DEFAULT_MODEL_FLASH)
        provider = manager.get_provider(config, provider_name="google")
        return PhDAgent(llm_provider=provider)
    except Exception as e:
        logger.error(f"Failed to initialize PhDAgent: {e}", exc_info=True)
        # Fallback to a non-functional agent to prevent full app crash during dev
        # In prod, this should raise or be handled more gracefully
        return PhDAgent(llm_provider=None) 

@lru_cache()
def get_postdoc_agent():
    """
    Provides a singleton PostDocAgent, configured with a default LLM.
    Returns None if initialization fails, as PostDocAgent is optional for some flows.
    """
    logger.info(f"Initializing PostDocAgent with Google provider and model {GOOGLE_DEFAULT_MODEL_PRO}.")
    try:
        manager = get_llm_manager()
        config = LLMConfig(model_name=GOOGLE_DEFAULT_MODEL_PRO)
        provider = manager.get_provider(config, provider_name="google")
        return PostDocAgent(llm_provider=provider)
    except Exception as e:
        logger.error(f"Failed to initialize PostDocAgent: {e}. PostDoc features may be limited.", exc_info=True)
        return None # PostDocAgent is optional in Orchestrator

@lru_cache()
def get_research_orchestrator() -> ResearchOrchestrator:
    """
    Provides a singleton ResearchOrchestrator instance, fully configured.
    """
    logger.info("Initializing ResearchOrchestrator.")
    phd_agent = get_phd_agent()
    if phd_agent.llm_provider is None:
        logger.warning("PhDAgent LLM provider is not available. Orchestrator functionality will be severely limited.")
        # Potentially raise an error here if PhDAgent is absolutely critical and cannot run without LLM
        # raise RuntimeError("PhDAgent could not be initialized with an LLM provider.")

    return ResearchOrchestrator(
        phd_agent=phd_agent,
        postdoc_agent=get_postdoc_agent(), # Can be None
        arxiv_service=get_arxiv_service(),
        ingestion_service=get_ingestion_service(),
        vector_db_client=get_vector_db_client(),
        checkpointer=get_checkpointer()
    )

# Example of how to get PyPDF2Processor if needed as a dependency directly
@lru_cache()
def get_pdf_processor_class():
    """Returns the PyPDF2Processor class."""
    return PyPDF2Processor 
from functools import lru_cache
import logging
from typing import Optional

# Orchestrator and its direct dependencies
from app.orchestration.orchestrator import ResearchOrchestrator
from app.agents.phd_agent import PhDAgent, PhDAgentDependencies
from app.agents.postdoc_agent import PostDocAgent, PostDocAgentDependencies
from app.services.arxiv_service import ArxivService
from app.services.ingestion_service import IngestionService
from app.services.vector_db_client import VectorDBClient
from app.services.pdf_processor import PyPDF2Processor # Assuming this is the chosen one
from app.config import settings # Import the application settings
from app.services.collection_manager import CollectionManager # Added
from app.services.embedding_service import EmbeddingService # Added

# LLM related imports for agent instantiation (simplified)
from app.services.llm.llm_manager import LLMManager
from app.models.llm_config import LLMConfig, LLMProviderType
from app.services.llm.prompt_manager import PromptManager
from app.services.llm.base_provider import LLMProvider

# Checkpointer
from langgraph.checkpoint.memory import MemorySaver # Using MemorySaver for simplicity

logger = logging.getLogger(__name__)


# --- LLM Configuration --- 
# This would ideally load from a global app config or environment variables
# For simplicity, defining a default config here.
DEFAULT_LLM_CONFIG = LLMConfig(
    model_name="gemini-1.5-flash" # Default model for the application
)

# Define an ultimate fallback configuration
ULTIMATE_FALLBACK_CONFIG = LLMConfig(
    model_name="gemini-2.0-flash-lite" # Last resort model
)

def get_llm_provider_instance(config: LLMConfig) -> LLMProvider: # config is now required
    provider_name = LLMProviderType.GOOGLE.value # Assuming Google based on LLMConfig structure
    logger.info(f"Attempting to initialize LLMProvider for {provider_name} with model: {config.model_name}.")
    try:
        provider_instance = LLMManager.get_provider(config=config, provider_name=provider_name)
        logger.info(f"LLMProvider instance for {provider_name}:{config.model_name} initialized successfully.")
        return provider_instance
    except Exception as e:
        logger.error(
            f"Failed to initialize LLMProvider instance for {provider_name} with model {config.model_name}. Config: {config}. Error: {e}",
            exc_info=True
        )
        # This function's responsibility is to try the given config. If it fails, it should raise.
        # Callers (like agent getters) will handle fallbacks if appropriate.
        raise RuntimeError(f"Failed to initialize LLMProvider for model {config.model_name} using {provider_name}.") from e

@lru_cache(maxsize=None)
def get_prompt_manager() -> PromptManager:
    logger.info("Initializing PromptManager.")
    # Provide the path to the directory containing prompt subdirectories (e.g., phd, postdoc)
    # Path should be relative to the workspace root where the backend command is run
    template_directory = "app/agents/prompts"
    logger.info(f"Attempting to load prompt templates from: {template_directory}")
    try:
        return PromptManager(template_dir=template_directory)
    except FileNotFoundError as e:
        logger.error(f"Prompt template directory not found at '{template_directory}'. Check path. Error: {e}")
        # Decide how to handle - raise error or return a non-functional manager?
        # Raising an error is safer as the application likely can't function without prompts.
        raise RuntimeError(f"Prompt template directory not found: {template_directory}") from e
    except Exception as e:
        logger.error(f"Failed to initialize PromptManager from '{template_directory}': {e}", exc_info=True)
        raise RuntimeError("Failed to initialize PromptManager") from e

@lru_cache(maxsize=None)
def get_phd_agent(requested_llm_config: Optional[LLMConfig] = None) -> PhDAgent:
    config_to_use = requested_llm_config if requested_llm_config is not None else DEFAULT_LLM_CONFIG
    provider_name_for_log = LLMProviderType.GOOGLE.value # Assuming Google for now

    logger.info(f"Initializing PhDAgent with {provider_name_for_log} provider and model {config_to_use.model_name}.")

    try:
        llm_provider = get_llm_provider_instance(config_to_use) # Will raise if config_to_use fails
        prompt_manager_instance = get_prompt_manager()
        
        dependencies = PhDAgentDependencies(
            prompt_manager=prompt_manager_instance,
            llm_manager=llm_provider,
        )
        return PhDAgent(dependencies=dependencies, llm_model_name=config_to_use.model_name)
    except Exception as e:
        logger.error(f"Failed to initialize PhDAgent with model {config_to_use.model_name} via {provider_name_for_log}: {e}", exc_info=True)

        if requested_llm_config is not None: # A specific config was requested and it failed
            logger.error(
                f"The requested LLM configuration (model: '{requested_llm_config.model_name}') failed. "
                "No fallback will be attempted for this specific request."
            )
            raise RuntimeError(f"Could not initialize PhDAgent with requested model: {requested_llm_config.model_name}") from e

        # If here, requested_llm_config was None, meaning DEFAULT_LLM_CONFIG was used and failed.
        # Now attempt the ultimate fallback.
        logger.warning(
            f"Default LLM configuration (model: '{DEFAULT_LLM_CONFIG.model_name}') failed. "
            f"Attempting PhDAgent initialization with ultimate fallback LLM (model: '{ULTIMATE_FALLBACK_CONFIG.model_name}')."
        )

        if DEFAULT_LLM_CONFIG.model_name == ULTIMATE_FALLBACK_CONFIG.model_name:
            logger.critical(
                f"Ultimate fallback model '{ULTIMATE_FALLBACK_CONFIG.model_name}' is the same as the failed default model. "
                "Cannot initialize agent. This suggests the model itself is unavailable or misconfigured."
            )
            raise RuntimeError(
                f"Critical: Default LLM (model: '{DEFAULT_LLM_CONFIG.model_name}') and ultimate fallback LLM "
                f"(model: '{ULTIMATE_FALLBACK_CONFIG.model_name}') are identical and both failed to initialize."
            ) from e

        try:
            fallback_llm_provider = get_llm_provider_instance(ULTIMATE_FALLBACK_CONFIG)
            prompt_manager_instance = get_prompt_manager() # Re-get, in case it failed before or was not reached
            fallback_dependencies = PhDAgentDependencies(
                prompt_manager=prompt_manager_instance,
                llm_manager=fallback_llm_provider
            )
            agent = PhDAgent(dependencies=fallback_dependencies, llm_model_name=ULTIMATE_FALLBACK_CONFIG.model_name)
            logger.info(f"PhDAgent initialized successfully with ultimate fallback LLM (model: {ULTIMATE_FALLBACK_CONFIG.model_name}).")
            return agent
        except Exception as final_e:
            logger.critical(
                f"PhDAgent initialization with ultimate fallback LLM (model: '{ULTIMATE_FALLBACK_CONFIG.model_name}') also failed: {final_e}",
                exc_info=True
            )
            raise RuntimeError("Could not initialize PhDAgent even with ultimate fallback configuration.") from final_e

@lru_cache(maxsize=None)
def get_postdoc_agent(requested_llm_config: Optional[LLMConfig] = None) -> PostDocAgent:
    config_to_use = requested_llm_config if requested_llm_config is not None else DEFAULT_LLM_CONFIG
    provider_name_for_log = LLMProviderType.GOOGLE.value # Assuming Google for now

    logger.info(f"Initializing PostDocAgent with {provider_name_for_log} provider and model {config_to_use.model_name}.")
    try:
        llm_provider = get_llm_provider_instance(config_to_use) # Will raise if config_to_use fails
        prompt_manager_instance = get_prompt_manager()
        dependencies = PostDocAgentDependencies(
            prompt_manager=prompt_manager_instance,
            llm_manager=llm_provider
        )
        return PostDocAgent(dependencies=dependencies, llm_model_name=config_to_use.model_name)
    except Exception as e:
        logger.error(f"Failed to initialize PostDocAgent with model {config_to_use.model_name} via {provider_name_for_log}: {e}", exc_info=True)

        if requested_llm_config is not None: # A specific config was requested and it failed
            logger.error(
                f"The requested LLM configuration (model: '{requested_llm_config.model_name}') failed. "
                "No fallback will be attempted for this specific request."
            )
            raise RuntimeError(f"Could not initialize PostDocAgent with requested model: {requested_llm_config.model_name}") from e

        # If here, requested_llm_config was None, meaning DEFAULT_LLM_CONFIG was used and failed.
        # Now attempt the ultimate fallback.
        logger.warning(
            f"Default LLM configuration (model: '{DEFAULT_LLM_CONFIG.model_name}') failed. "
            f"Attempting PostDocAgent initialization with ultimate fallback LLM (model: '{ULTIMATE_FALLBACK_CONFIG.model_name}')."
        )

        if DEFAULT_LLM_CONFIG.model_name == ULTIMATE_FALLBACK_CONFIG.model_name:
            logger.critical(
                f"Ultimate fallback model '{ULTIMATE_FALLBACK_CONFIG.model_name}' is the same as the failed default model. "
                "Cannot initialize agent. This suggests the model itself is unavailable or misconfigured."
            )
            raise RuntimeError(
                f"Critical: Default LLM (model: '{DEFAULT_LLM_CONFIG.model_name}') and ultimate fallback LLM "
                f"(model: '{ULTIMATE_FALLBACK_CONFIG.model_name}') are identical and both failed to initialize."
            ) from e
        
        try:
            fallback_llm_provider = get_llm_provider_instance(ULTIMATE_FALLBACK_CONFIG)
            prompt_manager_instance = get_prompt_manager() # Re-get
            fallback_dependencies = PostDocAgentDependencies(
                prompt_manager=prompt_manager_instance,
                llm_manager=fallback_llm_provider
            )
            agent = PostDocAgent(dependencies=fallback_dependencies, llm_model_name=ULTIMATE_FALLBACK_CONFIG.model_name)
            logger.info(f"PostDocAgent initialized successfully with ultimate fallback LLM (model: {ULTIMATE_FALLBACK_CONFIG.model_name}).")
            return agent
        except Exception as final_e:
            logger.critical(
                f"PostDocAgent initialization with ultimate fallback LLM (model: '{ULTIMATE_FALLBACK_CONFIG.model_name}') also failed: {final_e}",
                exc_info=True
            )
            raise RuntimeError("Could not initialize PostDocAgent even with ultimate fallback configuration.") from final_e

@lru_cache()
def get_checkpointer():
    """Provides a singleton MemorySaver checkpointer."""
    logger.info("Initializing MemorySaver checkpointer.")
    return MemorySaver()

@lru_cache()
def get_vector_db_client() -> VectorDBClient:
    logger.info("Initializing VectorDBClient.")
    return VectorDBClient(settings=settings)

@lru_cache()
def get_collection_manager() -> CollectionManager:
    """Provides a singleton CollectionManager."""
    logger.info("Initializing CollectionManager.")
    db_client = get_vector_db_client()
    return CollectionManager(vector_db_client=db_client)

@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Provides a singleton EmbeddingService."""
    logger.info("Initializing EmbeddingService.")
    # EmbeddingService might need configuration (e.g., model name from settings)
    # or have a default model internal to its class.
    # Assuming a simple constructor for now.
    # Example if config needed: return EmbeddingService(model_name=settings.DEFAULT_EMBEDDING_MODEL)
    return EmbeddingService()

@lru_cache()
def get_ingestion_service() -> IngestionService:
    """Provides a singleton IngestionService."""
    logger.info("Initializing IngestionService.")
    # Provide all required dependencies
    return IngestionService(
        vector_db_client=get_vector_db_client(), 
        collection_manager=get_collection_manager(),
        embedding_service=get_embedding_service()
    )

@lru_cache()
def get_arxiv_service():
    """Provides a singleton ArxivService."""
    logger.info("Initializing ArxivService.")
    return ArxivService()

@lru_cache()
def get_pdf_processor_class():
    """Returns the PyPDF2Processor class."""
    return PyPDF2Processor 

@lru_cache(maxsize=None)
def get_research_orchestrator() -> ResearchOrchestrator:
    """
    Provides a singleton ResearchOrchestrator instance, fully configured.
    """
    logger.info("Initializing ResearchOrchestrator.")
    phd_agent = get_phd_agent()
    
    if phd_agent.dependencies.llm_manager is None:
        logger.warning("PhDAgent LLM provider (via dependencies.llm_manager) is not available. Orchestrator functionality will be severely limited.")
        # raise RuntimeError("PhDAgent could not be initialized with an LLM provider.")

    return ResearchOrchestrator(
        phd_agent=phd_agent,
        postdoc_agent=get_postdoc_agent(),
        arxiv_service=get_arxiv_service(),
        ingestion_service=get_ingestion_service(),
        vector_db_client=get_vector_db_client(),
        checkpointer=get_checkpointer()
    ) 
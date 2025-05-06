"""
Service for managing vector database collections with application-specific logic.
This manager acts as an abstraction layer over the VectorDBClient, enforcing
naming conventions, metadata schemas, and business rules specific to research
collections within the application.
"""

import logging
from typing import Optional, Dict, Any
from chromadb.api.models.Collection import Collection
from chromadb.errors import ChromaError # For catching underlying DB errors

# Assuming these services will be in these locations
from app.services.vector_db_client import VectorDBClient
from app.services.embedding_service import EmbeddingService # If needed for metadata or validation

logger = logging.getLogger(__name__)

class CollectionManager:
    """
    Manages research-specific collections in the vector database.

    This service uses a VectorDBClient to interact with the database and applies
    application-specific logic such as standardized naming conventions (e.g.,
    prefixing with `research_session_`) and metadata management for collections
    related to research sessions.
    """

    # Define a prefix for research collections for easy identification
    RESEARCH_COLLECTION_PREFIX = "research_session_"

    # Define expected metadata keys for research collections
    # This could be more formally defined using Pydantic models later if needed
    REQUIRED_METADATA_KEYS = {"session_id", "research_area"}
    OPTIONAL_METADATA_KEYS = {"research_topic", "created_at"}

    # Added 'hpf_collection_type' as it's used in create_research_collection
    # and can be considered part of the managed schema.
    MANAGED_METADATA_KEYS = {"session_id", "research_area", "research_topic", "hpf_collection_type"}

    def __init__(self, vector_db_client: VectorDBClient, embedding_service: Optional[EmbeddingService] = None):
        """
        Initializes the CollectionManager.

        Args:
            vector_db_client: An initialized instance of VectorDBClient to interact with the database.
            embedding_service: An optional instance of EmbeddingService, which might be used
                                 in the future for validating embedding compatibility or enriching metadata.

        Raises:
            ValueError: If `vector_db_client` is not provided.
        """
        if not vector_db_client:
            logger.error("VectorDBClient instance is required for CollectionManager.")
            raise ValueError("VectorDBClient instance is required.")
        
        self.db_client = vector_db_client
        self.embedding_service = embedding_service
        logger.info("CollectionManager initialized.")

    def _generate_collection_name(self, session_id: str) -> str:
        """
        Generates a standardized, prefixed name for a research collection based on the session ID.

        Args:
            session_id: The unique identifier for the research session.

        Returns:
            The standardized collection name string.
        """
        return f"{self.RESEARCH_COLLECTION_PREFIX}{session_id}"

    # --- Core Collection Management Methods (to be implemented) ---

    def create_research_collection(
        self,
        session_id: str,
        research_area: str,
        research_topic: Optional[str] = None,
    ) -> Optional[Collection]:
        """
        Creates a new research-specific collection with standardized naming and essential metadata.

        It ensures that required metadata fields (`session_id`, `research_area`, `hpf_collection_type`)
        are included. If a collection with the generated name already exists, it will be retrieved.

        Args:
            session_id: Unique identifier for the research session. This is mandatory.
            research_area: The general area or domain of research. This is mandatory.
            research_topic: Optional specific topic within the research area.

        Returns:
            The created or retrieved ChromaDB Collection object if successful,
            otherwise None if input validation fails or an error occurs during DB interaction.
        """
        if not session_id or not research_area:
            logger.error("Session ID and research area are mandatory for creating a research collection.")
            return None

        collection_name = self._generate_collection_name(session_id)
        
        collection_metadata: Dict[str, Any] = {
            "session_id": session_id,
            "research_area": research_area,
            "hpf_collection_type": "research_session" # Application-specific type identifier
        }
        if research_topic:
            collection_metadata["research_topic"] = research_topic
        
        logger.info(f"Attempting to create/get research collection: '{collection_name}' with metadata: {collection_metadata}")
        try:
            collection = self.db_client.get_or_create_collection(
                name=collection_name,
                metadata=collection_metadata
            )

            if not collection:
                logger.error(f"Failed to create or get collection '{collection_name}' via db_client (returned None).")
                return None
            
            # Verify that the core managed metadata is present as expected after creation/retrieval.
            # ChromaDB should preserve metadata on get_or_create_collection if it matches.
            # If it was just created, it should have the metadata we passed.
            # If it existed, its metadata might differ; get_or_create usually doesn't update metadata if exists.
            # This check is more of a sanity check for our application's expectations.
            if collection.metadata:
                for key in self.MANAGED_METADATA_KEYS:
                    if key in collection_metadata and (key not in collection.metadata or collection.metadata[key] != collection_metadata.get(key)):
                        logger.warning(
                            f"Collection '{collection_name}' metadata mismatch for key '{key}'. "
                            f"Expected (if created): '{collection_metadata.get(key)}', Actual in DB: '{collection.metadata.get(key)}'"
                        )
            else:
                logger.warning(f"Collection '{collection_name}' exists but has no accessible metadata after get_or_create_collection.")

            logger.info(f"Successfully accessed/created research collection: '{collection.name}' with ID: {collection.id}")
            return collection
        except ChromaError as ce:
            logger.exception(f"ChromaDB error during create_research_collection for '{collection_name}': {ce}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during create_research_collection for '{collection_name}': {e}")
            return None

    def get_research_collection(self, session_id: str) -> Optional[Collection]:
        """
        Retrieves an existing research-specific collection based on the session ID.

        Args:
            session_id: Unique identifier for the research session.

        Returns:
            The ChromaDB Collection object if found, otherwise None.
            Returns None if `session_id` is not provided or a DB error occurs.
        """
        if not session_id:
            logger.error("Session ID is required to retrieve a research collection.")
            return None
        
        collection_name = self._generate_collection_name(session_id)
        logger.debug(f"Attempting to retrieve research collection: '{collection_name}' for session '{session_id}'")
        try:
            collection = self.db_client.get_collection(name=collection_name)
            if collection:
                logger.info(f"Successfully retrieved research collection: '{collection.name}' for session '{session_id}'")
            else:
                # This case should ideally be handled by get_collection returning None (as per db_client docs)
                # or raising CollectionNotFoundError which db_client now catches and returns None.
                logger.info(f"Research collection '{collection_name}' for session '{session_id}' not found by db_client.")
            return collection
        except ChromaError as ce: # Should be caught by db_client.get_collection, but as a safeguard.
            logger.exception(f"ChromaDB error while getting research collection '{collection_name}': {ce}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error while getting research collection '{collection_name}': {e}")
            return None

    def delete_research_collection(self, session_id: str) -> bool:
        """
        Deletes a research-specific collection based on the session ID.

        Args:
            session_id: Unique identifier for the research session.

        Returns:
            True if the collection was successfully deleted or did not exist.
            False if `session_id` is not provided or an error occurs during deletion
            and the collection might still exist.
        """
        if not session_id:
            logger.error("Session ID is required to delete a research collection.")
            return False

        collection_name = self._generate_collection_name(session_id)
        logger.info(f"Attempting to delete research collection: '{collection_name}' for session '{session_id}'")
        try:
            # db_client.delete_collection should handle ChromaErrors and return bool
            return self.db_client.delete_collection(name=collection_name)
        except Exception as e: # Catch any unexpected errors from the call itself
            logger.exception(f"Unexpected error calling db_client.delete_collection for '{collection_name}': {e}")
            return False

    # --- Placeholder for future schema validation/migration ---
    def validate_collection_schema(self, collection: Collection) -> bool:
        """
        (Placeholder) Validates if a given collection adheres to the application-defined schema
        for research collections, checking for required metadata keys.

        Args:
            collection: The ChromaDB Collection object to validate.

        Returns:
            True if the collection schema is considered valid (currently a placeholder).
            False otherwise (e.g., if metadata is missing or required keys are absent).
        """
        logger.warning("CollectionManager.validate_collection_schema is a placeholder and not fully implemented.")
        if not collection or not collection.metadata:
            logger.warning(f"Validation failed for collection '{collection.name if collection else 'None'}': No metadata found.")
            return False
        
        for key in self.REQUIRED_METADATA_KEYS:
            if key not in collection.metadata:
                logger.warning(f"Validation failed for collection '{collection.name}': Missing required metadata key '{key}'.")
                return False
        logger.debug(f"Basic schema validation passed for collection '{collection.name}'.")
        return True

    def migrate_collection_schema(self, collection_name: str) -> None:
        """
        (Placeholder) Migrates an existing collection to the current schema definition.
        """
        # This would involve fetching the collection, analyzing its current metadata,
        # comparing against the target schema (e.g., REQUIRED_METADATA_KEYS, MANAGED_METADATA_KEYS),
        # and then potentially updating the collection's metadata if supported by ChromaDB,
        # or recreating the collection with new data if metadata update isn't direct.
        # ChromaDB collection metadata update is typically done at creation or via client.modify().
        logger.warning(f"CollectionManager.migrate_collection_schema for '{collection_name}' is a placeholder and not implemented.")
        pass 
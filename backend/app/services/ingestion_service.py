"""
Service responsible for orchestrating the document ingestion pipeline.

This service integrates text chunking, embedding generation, and storage into
a vector database (ChromaDB) via dedicated client and manager services.
It provides a high-level interface to process and store documents for
semantic search and analysis.
"""

import logging
from typing import List, Optional, Dict, Any

# Import dependent services and utilities
from app.services.vector_db_client import VectorDBClient
from app.services.collection_manager import CollectionManager
from app.services.embedding_service import EmbeddingService
from app.services.chunking_service import chunk_text_fixed_size
from chromadb.errors import ChromaError # For specific error handling from DB

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Orchestrates the document ingestion process into the vector database.

    This involves:
    1. Retrieving or confirming the existence of a target collection for a given session.
    2. Chunking the input document text using a specified strategy.
    3. Generating embeddings for each text chunk via an embedding service.
    4. Preparing unique IDs and rich metadata for each chunk.
    5. Adding the chunks, their embeddings, and metadata to the vector database collection.
    """

    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_OVERLAP = 50

    def __init__(
        self,
        vector_db_client: VectorDBClient,
        collection_manager: CollectionManager,
        embedding_service: EmbeddingService,
    ):
        """
        Initializes the IngestionService with necessary dependencies.

        Args:
            vector_db_client: An initialized client for interacting with the vector database.
            collection_manager: An initialized manager for handling collection-specific logic
                                (e.g., naming, retrieval based on session).
            embedding_service: An initialized service for generating text embeddings.

        Raises:
            ValueError: If any of the required service dependencies are not provided.
        """
        if not vector_db_client:
            raise ValueError("VectorDBClient instance is required.")
        if not collection_manager:
            raise ValueError("CollectionManager instance is required.")
        if not embedding_service:
            raise ValueError("EmbeddingService instance is required.")
        
        self.db_client = vector_db_client
        self.collection_manager = collection_manager
        self.embedding_service = embedding_service
        logger.info("IngestionService initialized with all dependencies.")

    def ingest_document(
        self,
        session_id: str,
        document_id: str,
        document_text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> bool:
        """
        Processes a single document and ingests its content as chunks into the vector database.

        The process involves retrieving the appropriate collection for the `session_id`,
        chunking the `document_text`, generating embeddings for these chunks, creating unique
        IDs and metadata for each chunk (including `document_id` and `chunk_index`),
        and finally storing them in the collection.

        Args:
            session_id: The ID of the research session, used to identify or create
                        the target collection.
            document_id: A unique identifier for the source document (e.g., filename, URL, database ID).
            document_text: The raw text content of the document to be ingested.
            document_metadata: Optional dictionary of metadata associated with the source document.
                               This metadata will be merged with chunk-specific metadata.
            chunk_size: Optional custom size for text chunks. If None, uses `DEFAULT_CHUNK_SIZE`.
            chunk_overlap: Optional custom overlap between text chunks. If None, uses `DEFAULT_OVERLAP`.

        Returns:
            True if the document was successfully processed and all its chunks were ingested.
            False if any critical step in the pipeline fails (e.g., collection not found,
            chunking error, embedding error, database insertion error).
        """
        logger.info(f"Starting ingestion for document '{document_id}' into session '{session_id}' using collection manager.")

        # 1. Get target research collection using CollectionManager
        try:
            # Assuming collection should exist. If creation on-the-fly is desired,
            # create_research_collection would be called here with more metadata.
            collection = self.collection_manager.get_research_collection(session_id)
            if not collection:
                logger.error(f"Target collection for session '{session_id}' not found by CollectionManager. Ingestion aborted.")
                return False
            collection_name = collection.name
            logger.info(f"Target collection '{collection_name}' confirmed for session '{session_id}'")
        except Exception as e_coll_mgr:
            logger.exception(f"Error obtaining collection for session '{session_id}' via CollectionManager: {e_coll_mgr}")
            return False

        _chunk_size = chunk_size if chunk_size is not None else self.DEFAULT_CHUNK_SIZE
        _chunk_overlap = chunk_overlap if chunk_overlap is not None else self.DEFAULT_OVERLAP

        # 2. Chunk Text
        try:
            logger.debug(f"Chunking document '{document_id}' with size={_chunk_size}, overlap={_chunk_overlap}")
            chunks = chunk_text_fixed_size(document_text, _chunk_size, _chunk_overlap)
            if not chunks:
                logger.warning(f"No chunks generated for document '{document_id}'. Document might be empty or too short for current chunk settings. Ingestion considered successful with no data.")
                return True
            logger.info(f"Generated {len(chunks)} chunks for document '{document_id}'")
        except ValueError as ve:
            logger.error(f"Invalid chunking parameters (size={_chunk_size}, overlap={_chunk_overlap}) for document '{document_id}': {ve}")
            return False
        except Exception as e_chunk:
            logger.exception(f"Unexpected error during text chunking for document '{document_id}': {e_chunk}")
            return False

        # 3. Generate Embeddings
        try:
            logger.debug(f"Generating embeddings for {len(chunks)} chunks of document '{document_id}'")
            # Ensure generate_embeddings can handle list of texts and returns list of embeddings (np.array or list[float])
            embeddings_np = self.embedding_service.generate_embeddings(chunks)
            if not embeddings_np or len(embeddings_np) != len(chunks):
                logger.error(
                    f"Embedding generation failed or returned mismatched count for document '{document_id}'. "
                    f"Expected: {len(chunks)}, Got: {len(embeddings_np) if embeddings_np else 0}"
                )
                return False
            # Convert numpy arrays to lists of floats if necessary for ChromaDB client
            embeddings: List[List[float]] = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings_np]
            logger.info(f"Generated {len(embeddings)} embeddings for document '{document_id}'")
        except Exception as e_embed:
            logger.exception(f"Error during embedding generation for document '{document_id}': {e_embed}")
            return False

        # 4. Prepare Data for DB (IDs and Metadata)
        chunk_ids: List[str] = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        chunk_metadatas: List[Dict[str, Any]] = []
        base_doc_metadata = document_metadata.copy() if document_metadata else {}
        base_doc_metadata.update({
            "document_id": document_id,
            "session_id": session_id, # Ensure session_id is part of chunk metadata
        })

        for i in range(len(chunks)):
            meta_for_chunk = base_doc_metadata.copy()
            meta_for_chunk["chunk_index"] = i
            meta_for_chunk["chunk_text_length"] = len(chunks[i]) # Example of additional chunk-specific metadata
            chunk_metadatas.append(meta_for_chunk)
            
        if not (len(chunk_ids) == len(chunks) == len(embeddings) == len(chunk_metadatas)):
            logger.critical(f"Critical internal error: Data list length mismatch before DB add for document '{document_id}'. Chunks: {len(chunks)}, Embeddings: {len(embeddings)}, IDs: {len(chunk_ids)}, Metadatas: {len(chunk_metadatas)}. Aborting.")
            return False # Should not happen if previous checks pass

        # 5. Add to DB via VectorDBClient
        logger.info(f"Attempting to add {len(chunk_ids)} pre-processed items to collection '{collection_name}' for document '{document_id}'")
        try:
            success = self.db_client.add_to_collection(
                collection_name=collection_name,
                ids=chunk_ids,
                documents=chunks, # Pass original chunks as documents
                embeddings=embeddings, # Pass generated embeddings
                metadatas=chunk_metadatas
            )
            if success:
                logger.info(f"Successfully ingested {len(chunks)} chunks for document '{document_id}' into collection '{collection_name}'")
            else:
                # The db_client.add_to_collection already logs specific errors.
                logger.error(f"Failed to add chunks for document '{document_id}' to collection '{collection_name}' as reported by db_client.")
            return success
        except ChromaError as ce_db_add: # Catch specific DB errors if VectorDBClient re-raises them or they bypass its internal try-except
            logger.exception(f"ChromaDB error while adding items for document '{document_id}' to '{collection_name}': {ce_db_add}")
            return False
        except Exception as e_db_add:
            logger.exception(f"Unexpected error while adding items for document '{document_id}' to collection '{collection_name}': {e_db_add}")
            return False 
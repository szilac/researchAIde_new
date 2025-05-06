import logging
from typing import List, Dict, Any

from app.services.vector_db_client import VectorDBClient
from app.services.collection_manager import CollectionManager
from app.services.embedding_service import EmbeddingService
from chromadb.errors import ChromaError # For specific error handling

logger = logging.getLogger(__name__)

class SearchService:
    """
    Provides semantic search capabilities over documents stored in ChromaDB.

    This service uses a CollectionManager to identify the correct collection
    for a given session, an EmbeddingService to convert query text into vectors,
    and a VectorDBClient to perform the actual query against the database.
    It processes the raw results from ChromaDB to provide a list of search hits
    with calculated similarity scores.
    """
    def __init__(
        self,
        vector_db_client: VectorDBClient,
        collection_manager: CollectionManager,
        embedding_service: EmbeddingService,
    ):
        """
        Initializes the SearchService with necessary dependencies.

        Args:
            vector_db_client: An initialized client for vector database interactions.
            collection_manager: An initialized manager for collection-related logic.
            embedding_service: An initialized service for generating query embeddings.

        Raises:
            ValueError: If any of the required service dependencies are not provided.
        """
        if not vector_db_client:
            raise ValueError("VectorDBClient instance is required.")
        if not collection_manager:
            raise ValueError("CollectionManager instance is required.")
        if not embedding_service:
            raise ValueError("EmbeddingService instance is required.")

        self.vector_db_client = vector_db_client
        self.collection_manager = collection_manager
        self.embedding_service = embedding_service
        logger.info("SearchService initialized with all dependencies.")

    async def semantic_search(
        self, session_id: str, query_text: str, n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic search for a given query text within a specific session's collection.

        The process involves:
        1. Identifying the target collection name using the `session_id` via CollectionManager.
        2. Retrieving the ChromaDB collection object via VectorDBClient.
        3. Generating an embedding for the `query_text` using EmbeddingService.
        4. Querying the collection with the embedding to find the top `n_results`.
        5. Processing the query results: calculating a similarity score from distance
           (assuming L2 distance, score = 1.0 / (1.0 + distance)), and structuring
           the output.
        6. Returning results sorted by score in descending order.

        Args:
            session_id: The ID of the research session, used to locate the relevant collection.
            query_text: The text string to search for.
            n_results: The maximum number of search results to return.

        Returns:
            A list of search result dictionaries, sorted by similarity score (highest first).
            Each dictionary contains:
            - `id` (str): The unique ID of the result chunk.
            - `document_id` (str, optional): The ID of the original document from which the chunk came.
            - `text` (str, optional): The text content of the result chunk.
            - `score` (float): The calculated similarity score (higher is better).
            - `metadata` (dict, optional): Other metadata associated with the chunk.
            Returns an empty list if the collection is not found, no results are returned
            from the database, or if any critical error occurs during the process.
        """
        logger.info(
            f"Performing semantic search for session '{session_id}' with query: '{query_text[:100]}...' (n_results={n_results})"
        )
        try:
            collection_name = self.collection_manager._generate_collection_name(
                session_id
            )
            # No explicit check for collection_name itself, as _generate_collection_name should always return a string.

            collection = self.vector_db_client.get_collection(collection_name)
            if not collection:
                logger.warning(
                    f"Search failed: Collection '{collection_name}' not found for session '{session_id}'."
                )
                return []
            logger.debug(f"Found collection '{collection_name}' for search.")

            # Generate embedding for the query text
            query_embeddings_list = self.embedding_service.generate_embeddings([query_text])
            if not query_embeddings_list or not query_embeddings_list[0].any(): # Check if list is empty or embedding is empty
                logger.error(f"Failed to generate embedding for query: '{query_text[:100]}...'")
                return []
            query_embedding = query_embeddings_list[0]
            logger.debug(f"Generated query embedding for: '{query_text[:100]}...'")

            # Query the collection
            # ChromaDB query_embeddings expects a list of embeddings (vectors)
            query_results = collection.query(
                query_embeddings=[query_embedding.tolist()], 
                n_results=n_results,
                include=["metadatas", "documents", "distances", "ids"] # Explicitly include ids
            )
            
            processed_results: List[Dict[str, Any]] = []
            # ChromaDB query_results structure: keys are 'ids', 'distances', 'metadatas', 'documents', 'embeddings' (if included)
            # Each key maps to a list of lists, one inner list per query embedding. Here, we have one query.
            if not query_results or not query_results.get("ids") or not query_results["ids"][0]:
                logger.info(f"No search results found in collection '{collection_name}' for query: '{query_text[:100]}...'")
                return []

            ids_list = query_results["ids"][0]
            distances_list = query_results["distances"][0]
            metadatas_list = query_results.get("metadatas")[0] if query_results.get("metadatas") else [None] * len(ids_list)
            documents_list = query_results.get("documents")[0] if query_results.get("documents") else [None] * len(ids_list)

            for i, chunk_id in enumerate(ids_list):
                distance = distances_list[i]
                # Default space in ChromaDB is 'l2'. For 'l2', smaller distance is better.
                # Score calculation: 1.0 / (1.0 + distance) for L2 to make higher score better.
                # Ensure distance is not None for safety, though ChromaDB should always return it.
                score = (1.0 / (1.0 + distance)) if distance is not None else 0.0

                metadata = metadatas_list[i] if metadatas_list and metadatas_list[i] is not None else {}
                document_text = documents_list[i] if documents_list and documents_list[i] is not None else ""
                document_id = metadata.get("document_id") # Extract document_id from metadata if present

                processed_results.append(
                    {
                        "id": chunk_id,
                        "document_id": document_id,
                        "text": document_text,
                        "score": score,
                        "metadata": metadata,
                    }
                )
            
            # Sort results by score in descending order (higher score is better)
            sorted_results = sorted(processed_results, key=lambda x: x["score"], reverse=True)
            logger.info(f"Found {len(sorted_results)} results for query: '{query_text[:100]}...'")
            return sorted_results

        except ValueError as ve: # Catch specific errors like from embedding generation if it raises ValueError
            logger.error(f"ValueError during semantic search for session '{session_id}': {ve}", exc_info=True)
            return []
        except ChromaError as ce: # Catch ChromaDB specific errors
            logger.error(f"ChromaDB error during semantic search for session '{session_id}': {ce}", exc_info=True)
            return []
        except Exception as e: # General catch-all for unexpected errors
            logger.error(f"Unexpected error during semantic search for session '{session_id}': {e}", exc_info=True)
            return [] 
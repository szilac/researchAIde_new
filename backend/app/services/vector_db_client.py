"""
Wrapper service for interacting with the ChromaDB vector database client.
This service abstracts the direct ChromaDB client usage, providing
application-specific error handling and a simplified interface for
common vector database operations.
"""

import logging
from typing import List, Optional, Sequence, Dict, Any

import chromadb
from chromadb.api.models.Collection import Collection
# Potential exception types (example, can be expanded):
from chromadb.errors import ChromaError # Base error for more specific handling

from app.config import Settings

# Configure logging
logger = logging.getLogger(__name__)

class VectorDBClient:
    """
    A client wrapper for ChromaDB operations.

    This class initializes and manages a persistent ChromaDB client,
    offering methods for collection management (create, list, delete, get)
    and data manipulation (add, query) within those collections.
    It aims to simplify interactions with ChromaDB and centralize
    database-specific logic and error handling.
    """

    def __init__(self, settings: Settings):
        """
        Initializes the ChromaDB persistent client using the provided path.

        Args:
            settings: The application settings object containing `CHROMA_DB_PATH`.

        Raises:
            ChromaError: If the ChromaDB client fails to initialize for any reason.
            # Or more specific exceptions if ChromaDB raises them and they are not caught.
        """
        self.settings = settings
        self.client = None
        try:
            self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
            logger.info(f"ChromaDB client initialized. Persistence path: {settings.CHROMA_DB_PATH}")
        except ChromaError as ce: # Catching a more specific Chroma base error
            logger.exception(f"ChromaDB client initialization failed at path {settings.CHROMA_DB_PATH}: {ce}")
            raise # Re-raise to signal failure to the caller
        except Exception as e:
            logger.exception(f"An unexpected error occurred during ChromaDB client initialization at path {settings.CHROMA_DB_PATH}: {e}")
            raise ChromaError(f"Unexpected error during ChromaDB client initialization: {e}") # Wrap in ChromaError

    # --- Collection Management Methods ---

    def list_collections(self) -> Sequence[Collection]:
        """
        Lists all collections currently in the database.

        Returns:
            A sequence of ChromaDB Collection objects. Returns an empty list
            if the client is not initialized or if an error occurs during listing.
        """
        if not self.client:
            logger.error("ChromaDB client not initialized. Cannot list collections.")
            return []
        try:
            return self.client.list_collections()
        except ChromaError as ce:
            logger.exception(f"Failed to list ChromaDB collections due to ChromaDB error: {ce}")
            return []
        except Exception as e:
            logger.exception(f"An unexpected error occurred while listing ChromaDB collections: {e}")
            return []

    def get_or_create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Collection]:
        """
        Retrieves an existing collection by its name or creates it if it does not exist.

        Args:
            name: The name of the collection.
            metadata: Optional metadata (key-value pairs) to associate with the
                      collection if it is being created.

        Returns:
            The ChromaDB Collection object if successfully retrieved or created,
            otherwise None if the client is not initialized or an error occurs.
        """
        if not self.client:
            logger.error(f"ChromaDB client not initialized. Cannot get or create collection '{name}'.")
            return None
        try:
            collection = self.client.get_or_create_collection(name=name, metadata=metadata)
            logger.info(f"Successfully accessed or created collection: '{name}'")
            return collection
        except ChromaError as ce:
            logger.exception(f"Failed to get or create collection '{name}' due to ChromaDB error: {ce}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred while getting or creating collection '{name}': {e}")
            return None

    def delete_collection(self, name: str) -> bool:
        """
        Deletes a collection by its name from the database.

        Args:
            name: The name of the collection to be deleted.

        Returns:
            True if the collection was successfully deleted or if it did not exist initially.
            False if the client is not initialized, the deletion attempt fails and the
            collection still exists, or an unexpected error occurs.
        """
        if not self.client:
            logger.error(f"ChromaDB client not initialized. Cannot delete collection '{name}'.")
            return False

        try:
            self.client.delete_collection(name=name)
            logger.info(f"Successfully deleted collection: '{name}' (or it did not exist).")
            # ChromaDB's delete_collection does not error if the collection doesn't exist.
            # To be absolutely sure, one might re-check with get_collection, but
            # for simplicity, we trust ChromaDB's behavior here.
            return True
        except ChromaError as ce:
            logger.exception(f"Failed to delete collection '{name}' due to ChromaDB error: {ce}")
            # Check if it still exists to be sure
            try:
                if self.client.get_collection(name=name): # pragma: no cover
                    logger.warning(f"Collection '{name}' still exists after failed deletion attempt with ChromaError.")
                    return False
            except ChromaError: # Expected if deletion was effective or it never existed
                 logger.info(f"Collection '{name}' confirmed non-existent after ChromaError during deletion.")
                 return True # It's gone or was never there
            except Exception as e_check: # pragma: no cover
                 logger.exception(f"Unexpected error checking collection '{name}' existence after ChromaError during deletion: {e_check}")
                 return False # Uncertain state
            return False # Failed to delete and it might still be there
        except Exception as e:
            logger.exception(f"An unexpected error occurred while deleting collection '{name}': {e}")
            return False

    def get_collection(self, name: str) -> Optional[Collection]:
        """
        Retrieves an existing collection by its name.

        Args:
            name: The name of the collection to retrieve.

        Returns:
            The ChromaDB Collection object if found, otherwise None.
            Returns None if the client is not initialized or an error occurs.
        """
        if not self.client:
            logger.error(f"ChromaDB client not initialized. Cannot get collection '{name}'.")
            return None
        try:
            return self.client.get_collection(name=name)
        except ChromaError: # More specific: chromadb.errors.CollectionNotFoundError could be caught
            logger.info(f"Collection '{name}' not found in ChromaDB.")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred while getting collection '{name}': {e}")
            return None

    def get_collection_count(self, collection_name: str) -> Optional[int]:
        """
        Gets the total number of items (documents/embeddings) in a specified collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            The count of items as an integer if the collection exists and count is successful.
            Returns None if the collection does not exist, the client is not initialized,
            or an error occurs during the count operation.
        """
        if not self.client: # Check client initialization first
            logger.error(f"ChromaDB client not initialized. Cannot get count for collection '{collection_name}'.")
            return None

        collection = self.get_collection(collection_name)
        if collection:
            try:
                return collection.count()
            except ChromaError as ce:
                logger.exception(f"Failed to get count for collection '{collection_name}' due to ChromaDB error: {ce}")
                return None
            except Exception as e:
                logger.exception(f"An unexpected error occurred while getting count for collection '{collection_name}': {e}")
                return None
        else:
            logger.warning(f"Cannot get count for collection '{collection_name}': Collection not found.")
            return None # Collection not found based on get_collection behavior

    # --- Data Manipulation Methods ---

    def add_to_collection(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Adds items (documents, embeddings, and metadata) to a specified collection.

        Args:
            collection_name: The name of the target collection.
            ids: A list of unique string IDs for the items being added.
            documents: An optional list of text documents corresponding to the IDs.
            embeddings: An optional list of embedding vectors (lists of floats)
                        corresponding to the IDs.
            metadatas: An optional list of metadata dictionaries corresponding to the IDs.

        Returns:
            True if the items were successfully added to the collection.
            False if the collection is not found, the client is not initialized,
            or an error occurs during the addition (e.g., DuplicateIDError from ChromaDB).
        """
        if not self.client: # Check client initialization first
            logger.error(f"ChromaDB client not initialized. Cannot add to collection '{collection_name}'.")
            return False

        collection = self.get_collection(collection_name)
        if not collection:
            logger.error(f"Cannot add to collection '{collection_name}': Collection not found.")
            return False
        
        if not ids:
            logger.warning(f"No IDs provided for adding to collection '{collection_name}'. Skipping operation.")
            return False # Or True, depending on desired behavior for empty input

        try:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully added {len(ids)} items to collection '{collection_name}'")
            return True
        except ChromaError as ce: # e.g., chromadb.errors.DuplicateIDError
            logger.exception(f"Failed to add items to collection '{collection_name}' due to ChromaDB error: {ce}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred while adding items to collection '{collection_name}': {e}")
            return False

    def query_collection(
        self,
        collection_name: str,
        n_results: int,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None, # Default is set by ChromaDB, often good. Explicit for clarity.
    ) -> Optional[Dict[str, Any]]: # ChromaDB's QueryResult is a TypedDict, more specific than Dict[str, Any]
        """
        Queries a specified collection for items similar to the given query embeddings or texts.

        Args:
            collection_name: The name of the collection to query.
            n_results: The number of results to return per query.
            query_embeddings: An optional list of embedding vectors to use for the query.
            query_texts: An optional list of text strings to use for the query.
                         (ChromaDB will embed these using the collection's embedding function).
            where: An optional dictionary for filtering results based on metadata.
                   Example: `{"source": "arxiv"}`
            where_document: An optional dictionary for filtering results based on document content
                            using ChromaDB's document query language. Example: `{"$contains": "search term"}`
            include: An optional list of fields to include in the query results.
                     Defaults to ChromaDB's default (often ["metadatas", "documents", "distances"]).
                     Common options: "ids", "embeddings", "documents", "metadatas", "distances".

        Returns:
            A dictionary containing the query results (e.g., ids, documents, distances, metadatas).
            The structure is defined by ChromaDB's QueryResult type.
            Returns None if the collection is not found, the client is not initialized,
            query parameters are invalid, or an error occurs during the query.
        """
        if not self.client: # Check client initialization first
            logger.error(f"ChromaDB client not initialized. Cannot query collection '{collection_name}'.")
            return None

        collection = self.get_collection(collection_name)
        if not collection:
            logger.error(f"Cannot query collection '{collection_name}': Collection not found.")
            return None

        if not query_embeddings and not query_texts:
            logger.error(f"Query for collection '{collection_name}' requires either query_embeddings or query_texts.")
            return None
        
        # Ensure include is not None if we want to rely on ChromaDB's default
        # Or set a sensible default here if ChromaDB's default is not desired.
        effective_include = include if include is not None else ["metadatas", "documents", "distances", "ids"]

        try:
            results = collection.query(
                query_embeddings=query_embeddings,
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=effective_include 
            )
            logger.debug(f"Query successful on collection '{collection_name}'")
            return results
        except ChromaError as ce:
            logger.exception(f"Failed to query collection '{collection_name}' due to ChromaDB error: {ce}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred while querying collection '{collection_name}': {e}")
            return None 
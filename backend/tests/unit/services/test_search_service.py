import pytest
from unittest.mock import MagicMock, AsyncMock
import numpy as np

# Assuming the service is in backend.app.services.search_service
from app.services.search_service import SearchService
from app.services.vector_db_client import VectorDBClient
from app.services.collection_manager import CollectionManager
from app.services.embedding_service import EmbeddingService

@pytest.fixture
def mock_vector_db_client():
    return MagicMock(spec=VectorDBClient)

@pytest.fixture
def mock_collection_manager():
    return MagicMock(spec=CollectionManager)

@pytest.fixture
def mock_embedding_service():
    mock = MagicMock(spec=EmbeddingService)
    # Mock generate_embeddings to return a list with a numpy array
    mock.generate_embeddings = MagicMock(return_value=[np.array([0.1, 0.2, 0.3])])
    return mock

@pytest.fixture
def search_service(mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    return SearchService(
        vector_db_client=mock_vector_db_client,
        collection_manager=mock_collection_manager,
        embedding_service=mock_embedding_service,
    )

@pytest.mark.asyncio
async def test_semantic_search_success(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    session_id = "test_session"
    query_text = "test query"
    n_results = 2
    collection_name = "research_session_test_session"
    
    mock_collection_manager._generate_collection_name.return_value = collection_name
    
    mock_collection = MagicMock()
    mock_vector_db_client.get_collection.return_value = mock_collection
    
    # Mock ChromaDB query response structure
    mock_query_results = {
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[{"document_id": "doc1"}, {"document_id": "doc2"}]],
        "documents": [["text1", "text2"]],
    }
    mock_collection.query.return_value = mock_query_results
    
    results = await search_service.semantic_search(session_id, query_text, n_results)
    
    assert len(results) == 2
    assert results[0]["id"] == "id1" # Sorted by score (1/(1+0.1) should be first)
    assert results[0]["score"] == 1.0 / (1.0 + 0.1) 
    assert results[1]["id"] == "id2"
    assert results[1]["score"] == 1.0 / (1.0 + 0.2)
    assert results[0]["document_id"] == "doc1"
    assert results[0]["text"] == "text1"

    mock_collection_manager._generate_collection_name.assert_called_once_with(session_id)
    mock_vector_db_client.get_collection.assert_called_once_with(collection_name)
    mock_embedding_service.generate_embeddings.assert_called_once_with([query_text])
    mock_collection.query.assert_called_once()
    # Detailed check for query_embeddings can be added if necessary, e.g., by checking the tolist() call on the embedding

@pytest.mark.asyncio
async def test_semantic_search_no_collection_name(search_service, mock_collection_manager):
    mock_collection_manager._generate_collection_name.return_value = None
    results = await search_service.semantic_search("test_session", "query")
    assert results == []
    mock_collection_manager._generate_collection_name.assert_called_once_with("test_session")

@pytest.mark.asyncio
async def test_semantic_search_collection_not_found(search_service, mock_vector_db_client, mock_collection_manager):
    collection_name = "research_session_test_session"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_vector_db_client.get_collection.return_value = None
    
    results = await search_service.semantic_search("test_session", "query")
    assert results == []
    mock_vector_db_client.get_collection.assert_called_once_with(collection_name)

@pytest.mark.asyncio
async def test_semantic_search_no_results_from_db(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    collection_name = "research_session_test_session"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_collection = MagicMock()
    mock_vector_db_client.get_collection.return_value = mock_collection
    mock_collection.query.return_value = {"ids": []} # Empty results
    
    results = await search_service.semantic_search("test_session", "query")
    assert results == []

@pytest.mark.asyncio
async def test_semantic_search_embedding_error(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    collection_name = "research_session_test_session"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_vector_db_client.get_collection.return_value = MagicMock() # Assume collection exists
    mock_embedding_service.generate_embeddings.side_effect = Exception("Embedding failed")
    
    results = await search_service.semantic_search("test_session", "query")
    assert results == []

@pytest.mark.asyncio
async def test_semantic_search_db_query_error(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    collection_name = "research_session_test_session"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_collection = MagicMock()
    mock_vector_db_client.get_collection.return_value = mock_collection
    mock_collection.query.side_effect = Exception("DB query failed")
    
    results = await search_service.semantic_search("test_session", "query")
    assert results == []

@pytest.mark.asyncio
async def test_semantic_search_results_missing_fields(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    session_id = "test_session_missing_fields"
    query_text = "query text"
    collection_name = "research_session_test_session_missing_fields"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_collection = MagicMock()
    mock_vector_db_client.get_collection.return_value = mock_collection

    # Simulate results with some missing optional fields (documents, metadatas)
    mock_query_results = {
        "ids": [["id1"]],
        "distances": [[0.5]],
        # "metadatas": [[{"document_id": "doc1"}]], # metadatas is missing
        # "documents": [["text1"]], # documents is missing
    }
    mock_collection.query.return_value = mock_query_results

    results = await search_service.semantic_search(session_id, query_text, 1)
    
    assert len(results) == 1
    assert results[0]["id"] == "id1"
    assert results[0]["score"] == 1.0 / (1.0 + 0.5)
    assert results[0]["document_id"] is None # Should default to None
    assert results[0]["text"] == ""         # Should default to empty string
    assert results[0]["metadata"] == {}     # Should default to empty dict

@pytest.mark.asyncio
async def test_semantic_search_sorting(search_service, mock_vector_db_client, mock_collection_manager, mock_embedding_service):
    # Test that results are correctly sorted by score (descending)
    collection_name = "research_session_test_sort"
    mock_collection_manager._generate_collection_name.return_value = collection_name
    mock_collection = MagicMock()
    mock_vector_db_client.get_collection.return_value = mock_collection
    
    # Results are intentionally out of order by distance (which implies score)
    mock_query_results = {
        "ids": [["id1", "id2", "id3"]],
        "distances": [[0.5, 0.1, 0.9]], # Lower distance -> higher score
        "metadatas": [[{}, {}, {}]],
        "documents": [["text1", "text2", "text3"]],
    }
    mock_collection.query.return_value = mock_query_results
    
    results = await search_service.semantic_search("test_sort", "query", 3)
    
    assert len(results) == 3
    # Expected order by score: id2 (score 1/(1+0.1)), id1 (score 1/(1+0.5)), id3 (score 1/(1+0.9))
    assert results[0]["id"] == "id2"
    assert results[1]["id"] == "id1"
    assert results[2]["id"] == "id3"
    
    assert results[0]["score"] > results[1]["score"]
    assert results[1]["score"] > results[2]["score"] 
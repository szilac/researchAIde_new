import pytest
from unittest.mock import MagicMock, patch, call
import logging

# Module to test
from app.services.ingestion_service import IngestionService
from app.services.vector_db_client import VectorDBClient
from app.services.collection_manager import CollectionManager
from app.services.embedding_service import EmbeddingService
# We also need to patch the imported chunking function
# from app.services.chunking_service import chunk_text_fixed_size 
from chromadb.api.models.Collection import Collection # For type hints

# Disable external logging
logging.disable(logging.CRITICAL)

# --- Fixtures --- 

@pytest.fixture
def mock_db_client():
    return MagicMock(spec=VectorDBClient)

@pytest.fixture
def mock_collection_manager():
    manager = MagicMock(spec=CollectionManager)
    # Pre-configure the internal method directly for simplicity in tests
    manager._generate_collection_name.side_effect = lambda sid: f"research_session_{sid}"
    return manager

@pytest.fixture
def mock_embedding_service():
    return MagicMock(spec=EmbeddingService)

@pytest.fixture
def ingestion_service(
    mock_db_client, 
    mock_collection_manager, 
    mock_embedding_service
): 
    """Provides an initialized IngestionService instance with mock dependencies."""
    service = IngestionService(
        vector_db_client=mock_db_client,
        collection_manager=mock_collection_manager,
        embedding_service=mock_embedding_service
    )
    # Just return the service
    return service 

# --- Test Cases --- 

# Constants for tests
SESSION_ID = "test_sess_1"
DOC_ID = "doc_123"
DOC_TEXT = "This is the document text. It is sufficiently long for chunking."
COLLECTION_NAME = f"research_session_{SESSION_ID}"
CHUNKS = ["This is the document text.", " It is sufficiently long for chunking."]
EMBEDDINGS = [[0.1, 0.2], [0.3, 0.4]]
DOC_META = {"source": "test.pdf", "author": "Test Author"}

@pytest.fixture(autouse=True)
def reset_mocks(mock_db_client, mock_collection_manager, mock_embedding_service):
    """Automatically reset mocks before each test."""
    mock_db_client.reset_mock()
    mock_collection_manager.reset_mock()
    mock_collection_manager._generate_collection_name.side_effect = lambda sid: f"research_session_{sid}"
    mock_embedding_service.reset_mock()

# Apply patch to each test needing it
@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_success(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service, mock_db_client):
    """Tests the successful ingestion path."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = CHUNKS # Use mock from patch argument
    mock_embedding_service.generate_embeddings.return_value = EMBEDDINGS
    mock_db_client.add_to_collection.return_value = True

    # Act
    success = ingestion_service.ingest_document(
        session_id=SESSION_ID,
        document_id=DOC_ID,
        document_text=DOC_TEXT,
        document_metadata=DOC_META
    )

    # Assert
    assert success is True
    mock_collection_manager.get_research_collection.assert_called_once_with(SESSION_ID)
    mock_chunk_func.assert_called_once_with( # Use mock from patch argument
        DOC_TEXT, 
        IngestionService.DEFAULT_CHUNK_SIZE, 
        IngestionService.DEFAULT_OVERLAP
    )
    mock_embedding_service.generate_embeddings.assert_called_once_with(CHUNKS)
    
    expected_chunk_ids = [f"{DOC_ID}_chunk_0", f"{DOC_ID}_chunk_1"]
    expected_chunk_metas = [
        {"document_id": DOC_ID, "session_id": SESSION_ID, "source": "test.pdf", "author": "Test Author", "chunk_index": 0},
        {"document_id": DOC_ID, "session_id": SESSION_ID, "source": "test.pdf", "author": "Test Author", "chunk_index": 1}
    ]
    mock_db_client.add_to_collection.assert_called_once_with(
        collection_name=COLLECTION_NAME,
        ids=expected_chunk_ids,
        documents=CHUNKS,
        embeddings=EMBEDDINGS,
        metadatas=expected_chunk_metas
    )

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_custom_chunk_params(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service, mock_db_client):
    """Tests that custom chunk parameters are used."""
    # Arrange
    custom_size = 100
    custom_overlap = 10
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = ["chunk1"]
    mock_embedding_service.generate_embeddings.return_value = [[0.5]]
    mock_db_client.add_to_collection.return_value = True

    # Act
    success = ingestion_service.ingest_document(
        session_id=SESSION_ID,
        document_id=DOC_ID,
        document_text=DOC_TEXT,
        chunk_size=custom_size,
        chunk_overlap=custom_overlap
    )

    # Assert
    assert success is True
    mock_chunk_func.assert_called_once_with( # Use mock from patch argument
        DOC_TEXT, 
        custom_size, 
        custom_overlap
    )

@patch('app.services.ingestion_service.chunk_text_fixed_size') 
def test_ingest_document_collection_not_found(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service, mock_db_client):
    """Tests ingestion failure if the target collection doesn't exist."""
    # Arrange
    mock_collection_manager.get_research_collection.return_value = None

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text=DOC_TEXT)

    # Assert
    assert success is False
    mock_collection_manager.get_research_collection.assert_called_once_with(SESSION_ID)
    mock_chunk_func.assert_not_called() # Use mock from patch argument
    mock_embedding_service.generate_embeddings.assert_not_called()
    mock_db_client.add_to_collection.assert_not_called()

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_chunking_error(mock_chunk_func, ingestion_service, mock_collection_manager):
    """Tests ingestion failure if chunking raises an error."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.side_effect = ValueError("Bad chunk params") # Use mock from patch argument

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text=DOC_TEXT)

    # Assert
    assert success is False
    mock_chunk_func.assert_called_once() # Use mock from patch argument

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_no_chunks(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service, mock_db_client):
    """Tests ingestion when chunking returns an empty list."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = [] # Use mock from patch argument

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text="")

    # Assert
    assert success is True # Should be considered success (nothing to ingest)
    mock_chunk_func.assert_called_once() # Use mock from patch argument
    mock_embedding_service.generate_embeddings.assert_not_called()
    mock_db_client.add_to_collection.assert_not_called()

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_embedding_error(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service):
    """Tests ingestion failure if embedding service raises an error."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = CHUNKS # Use mock from patch argument
    mock_embedding_service.generate_embeddings.side_effect = Exception("Embedding API failed")

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text=DOC_TEXT)

    # Assert
    assert success is False
    mock_embedding_service.generate_embeddings.assert_called_once_with(CHUNKS)

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_embedding_mismatch(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service):
    """Tests failure if embedding count doesn't match chunk count."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = CHUNKS # Use mock from patch argument
    mock_embedding_service.generate_embeddings.return_value = [[0.1, 0.2]] # Only one embedding

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text=DOC_TEXT)

    # Assert
    assert success is False
    mock_embedding_service.generate_embeddings.assert_called_once_with(CHUNKS)

@patch('app.services.ingestion_service.chunk_text_fixed_size')
def test_ingest_document_db_add_failure(mock_chunk_func, ingestion_service, mock_collection_manager, mock_embedding_service, mock_db_client):
    """Tests ingestion failure if adding to the DB fails."""
    # Arrange
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = COLLECTION_NAME
    mock_collection_manager.get_research_collection.return_value = mock_collection
    mock_chunk_func.return_value = CHUNKS # Use mock from patch argument
    mock_embedding_service.generate_embeddings.return_value = EMBEDDINGS
    mock_db_client.add_to_collection.return_value = False # Simulate DB add failure

    # Act
    success = ingestion_service.ingest_document(session_id=SESSION_ID, document_id=DOC_ID, document_text=DOC_TEXT)

    # Assert
    assert success is False
    mock_db_client.add_to_collection.assert_called_once()
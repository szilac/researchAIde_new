import pytest
from unittest.mock import MagicMock, patch
import logging

# Module to test
from app.services.collection_manager import CollectionManager
from app.services.vector_db_client import VectorDBClient
from app.services.embedding_service import EmbeddingService # Optional dependency
from chromadb.api.models.Collection import Collection # For type hints

# Disable external logging during tests
logging.disable(logging.CRITICAL)

@pytest.fixture
def mock_vector_db_client():
    """Provides a MagicMock instance for VectorDBClient."""
    mock_client = MagicMock(spec=VectorDBClient)
    return mock_client

@pytest.fixture
def mock_embedding_service():
    """Provides a MagicMock instance for EmbeddingService."""
    mock_service = MagicMock(spec=EmbeddingService)
    return mock_service

@pytest.fixture
def collection_manager(mock_vector_db_client, mock_embedding_service):
    """Provides an initialized CollectionManager instance with mock dependencies."""
    # Initialize with both mocks, though embedding_service might not be used in all tests yet
    manager = CollectionManager(
        vector_db_client=mock_vector_db_client, 
        embedding_service=mock_embedding_service
    )
    return manager

# --- Test Cases Start Here ---

def test_init_success(mock_vector_db_client, mock_embedding_service):
    """Tests successful initialization."""
    manager = CollectionManager(
        vector_db_client=mock_vector_db_client, 
        embedding_service=mock_embedding_service
    )
    assert manager.db_client == mock_vector_db_client
    assert manager.embedding_service == mock_embedding_service

def test_init_requires_db_client():
    """Tests that VectorDBClient is required for initialization."""
    with pytest.raises(ValueError, match="VectorDBClient instance is required."):
        CollectionManager(vector_db_client=None) # type: ignore

def test_generate_collection_name(collection_manager):
    """Tests the internal method for generating collection names."""
    session_id = "test_session_123"
    expected_name = f"research_session_{session_id}"
    assert collection_manager._generate_collection_name(session_id) == expected_name

# --- create_research_collection Tests ---

def test_create_research_collection_success(collection_manager, mock_vector_db_client):
    """Tests successful creation of a research collection."""
    session_id = "sess_create_ok"
    research_area = "AI Ethics"
    research_topic = "Bias in LLMs"
    expected_name = collection_manager._generate_collection_name(session_id)
    expected_metadata = {
        "session_id": session_id,
        "research_area": research_area,
        "research_topic": research_topic,
        "hpf_collection_type": "research_session"
    }

    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = expected_name
    mock_collection.id = "mock_coll_id_123"
    mock_collection.metadata = expected_metadata # Simulate metadata being set correctly
    mock_vector_db_client.get_or_create_collection.return_value = mock_collection

    collection = collection_manager.create_research_collection(
        session_id=session_id,
        research_area=research_area,
        research_topic=research_topic
    )

    assert collection == mock_collection
    mock_vector_db_client.get_or_create_collection.assert_called_once_with(
        name=expected_name,
        metadata=expected_metadata
    )

def test_create_research_collection_no_topic(collection_manager, mock_vector_db_client):
    """Tests successful creation without an optional topic."""
    session_id = "sess_no_topic"
    research_area = "Quantum Computing"
    expected_name = collection_manager._generate_collection_name(session_id)
    expected_metadata = {
        "session_id": session_id,
        "research_area": research_area,
        "hpf_collection_type": "research_session"
    }

    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = expected_name
    mock_collection.id = "mock_coll_id_456"
    mock_collection.metadata = expected_metadata
    mock_vector_db_client.get_or_create_collection.return_value = mock_collection

    collection = collection_manager.create_research_collection(
        session_id=session_id,
        research_area=research_area
    )

    assert collection == mock_collection
    mock_vector_db_client.get_or_create_collection.assert_called_once_with(
        name=expected_name,
        metadata=expected_metadata
    )

def test_create_research_collection_missing_args(collection_manager, mock_vector_db_client):
    """Tests creation failure if required args are missing."""
    collection1 = collection_manager.create_research_collection(session_id="", research_area="Area")
    assert collection1 is None
    collection2 = collection_manager.create_research_collection(session_id="sess", research_area="")
    assert collection2 is None
    mock_vector_db_client.get_or_create_collection.assert_not_called()

def test_create_research_collection_db_failure(collection_manager, mock_vector_db_client):
    """Tests creation failure if the db client fails."""
    session_id = "sess_db_fail"
    research_area = "Neuroscience"
    expected_name = collection_manager._generate_collection_name(session_id)
    # Simulate the db client returning None
    mock_vector_db_client.get_or_create_collection.return_value = None

    collection = collection_manager.create_research_collection(
        session_id=session_id,
        research_area=research_area
    )

    assert collection is None
    mock_vector_db_client.get_or_create_collection.assert_called_once()

def test_create_research_collection_metadata_mismatch(collection_manager, mock_vector_db_client, caplog):
    """Tests that a warning is logged if metadata doesn't match after creation (optional check)."""
    session_id = "sess_meta_mismatch"
    research_area = "Climate Tech"
    expected_name = collection_manager._generate_collection_name(session_id)
    expected_metadata = {
        "session_id": session_id,
        "research_area": research_area,
        "hpf_collection_type": "research_session"
    }

    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = expected_name
    mock_collection.id = "mock_coll_id_789"
    # Simulate incorrect metadata returned by DB
    mock_collection.metadata = {"session_id": session_id, "research_area": "WRONG AREA"}
    mock_vector_db_client.get_or_create_collection.return_value = mock_collection

    with caplog.at_level(logging.WARNING):
        collection = collection_manager.create_research_collection(
            session_id=session_id,
            research_area=research_area
        )
    
    assert collection == mock_collection # Still returns the collection
    assert "metadata mismatch for 'research_area'" in caplog.text
    mock_vector_db_client.get_or_create_collection.assert_called_once_with(
        name=expected_name,
        metadata=expected_metadata
    )

# --- get_research_collection Tests ---

def test_get_research_collection_success(collection_manager, mock_vector_db_client):
    """Tests getting a collection successfully."""
    session_id = "sess_get_ok"
    expected_name = collection_manager._generate_collection_name(session_id)
    mock_collection = MagicMock(spec=Collection)
    mock_collection.name = expected_name
    mock_vector_db_client.get_collection.return_value = mock_collection

    collection = collection_manager.get_research_collection(session_id)
    assert collection == mock_collection
    mock_vector_db_client.get_collection.assert_called_once_with(name=expected_name)

def test_get_research_collection_not_found(collection_manager, mock_vector_db_client):
    """Tests getting a collection when it's not found by the client."""
    session_id = "sess_get_none"
    expected_name = collection_manager._generate_collection_name(session_id)
    mock_vector_db_client.get_collection.return_value = None # Simulate not found

    collection = collection_manager.get_research_collection(session_id)
    assert collection is None
    mock_vector_db_client.get_collection.assert_called_once_with(name=expected_name)

def test_get_research_collection_missing_args(collection_manager, mock_vector_db_client):
    """Tests failure when session_id is missing."""
    collection = collection_manager.get_research_collection(session_id="")
    assert collection is None
    mock_vector_db_client.get_collection.assert_not_called()

# --- delete_research_collection Tests ---

def test_delete_research_collection_success(collection_manager, mock_vector_db_client):
    """Tests deleting a collection successfully."""
    session_id = "sess_del_ok"
    expected_name = collection_manager._generate_collection_name(session_id)
    mock_vector_db_client.delete_collection.return_value = True # Simulate success

    result = collection_manager.delete_research_collection(session_id)
    assert result is True
    mock_vector_db_client.delete_collection.assert_called_once_with(name=expected_name)

def test_delete_research_collection_failure(collection_manager, mock_vector_db_client):
    """Tests deleting when the db client returns failure."""
    session_id = "sess_del_fail"
    expected_name = collection_manager._generate_collection_name(session_id)
    mock_vector_db_client.delete_collection.return_value = False # Simulate failure

    result = collection_manager.delete_research_collection(session_id)
    assert result is False
    mock_vector_db_client.delete_collection.assert_called_once_with(name=expected_name)

def test_delete_research_collection_missing_args(collection_manager, mock_vector_db_client):
    """Tests failure when session_id is missing."""
    result = collection_manager.delete_research_collection(session_id="")
    assert result is False
    mock_vector_db_client.delete_collection.assert_not_called()

# --- Placeholder Tests ---

def test_validate_collection_schema_placeholder(collection_manager, caplog):
    """Tests the placeholder schema validation method."""
    mock_collection = MagicMock(spec=Collection)
    with caplog.at_level(logging.WARNING):
        result = collection_manager.validate_collection_schema(mock_collection)
    assert result is True # Placeholder currently returns True
    assert "validate_collection_schema is not yet implemented." in caplog.text

def test_migrate_collection_schema_placeholder(collection_manager, caplog):
    """Tests the placeholder schema migration method."""
    with caplog.at_level(logging.WARNING):
        collection_manager.migrate_collection_schema("some_collection_name")
    assert "migrate_collection_schema is not yet implemented." in caplog.text 
import pytest
from unittest.mock import patch, MagicMock
import logging

# Module to test
from app.services.vector_db_client import VectorDBClient
from app.config import Settings

# Disable external logging during tests for cleaner output
logging.disable(logging.CRITICAL)

@pytest.fixture
def mock_settings(tmp_path): # Use pytest's tmp_path fixture for isolation
    """Provides mock Settings pointing to a temporary directory."""
    temp_db_path = tmp_path / "test_chroma_db"
    # Ensure the parent directory exists if PersistentClient needs it
    # temp_db_path.mkdir(parents=True, exist_ok=True) # Usually PersistentClient handles this
    settings = MagicMock(spec=Settings)
    settings.CHROMA_DB_PATH = temp_db_path
    return settings

@pytest.fixture
def mock_chromadb_client():
    """Fixture to mock the chromadb.PersistentClient."""
    with patch('app.services.vector_db_client.chromadb.PersistentClient') as mock_client_constructor:
        mock_client_instance = MagicMock()
        # Configure mock methods for the client instance here if needed for setup
        mock_client_constructor.return_value = mock_client_instance
        yield mock_client_instance # Yield the instance for tests to use/configure

# --- Test Cases Start Here ---

def test_initialization_success(mock_settings, mock_chromadb_client):
    """Tests successful initialization of VectorDBClient."""
    try:
        client_wrapper = VectorDBClient(settings=mock_settings)
        assert client_wrapper.client is not None
        assert client_wrapper.client == mock_chromadb_client
        # Check if PersistentClient was called correctly
        from app.services.vector_db_client import chromadb
        chromadb.PersistentClient.assert_called_once_with(path=str(mock_settings.CHROMA_DB_PATH))
    except Exception as e:
        pytest.fail(f"Initialization failed unexpectedly: {e}")

def test_initialization_failure(mock_settings):
    """Tests that initialization raises error if PersistentClient fails."""
    # Configure the mock PersistentClient constructor to raise an error
    with patch('app.services.vector_db_client.chromadb.PersistentClient', side_effect=Exception("DB connection failed")):
        with pytest.raises(Exception, match="DB connection failed"):
            VectorDBClient(settings=mock_settings)

# --- Collection Management Tests ---

@pytest.fixture
def client_wrapper(mock_settings, mock_chromadb_client): # Use existing mocks
    """Provides an initialized VectorDBClient wrapper instance for tests."""
    # We rely on the mock_chromadb_client fixture patching PersistentClient
    return VectorDBClient(settings=mock_settings)

def test_list_collections_success(client_wrapper, mock_chromadb_client):
    """Tests listing collections successfully."""
    mock_collection1 = MagicMock()
    mock_collection1.name = "col1"
    mock_collection2 = MagicMock()
    mock_collection2.name = "col2"
    mock_chromadb_client.list_collections.return_value = [mock_collection1, mock_collection2]

    collections = client_wrapper.list_collections()
    assert len(collections) == 2
    assert collections[0].name == "col1"
    mock_chromadb_client.list_collections.assert_called_once()

def test_list_collections_failure(client_wrapper, mock_chromadb_client):
    """Tests listing collections when the underlying client call fails."""
    mock_chromadb_client.list_collections.side_effect = Exception("List failed")
    collections = client_wrapper.list_collections()
    assert collections == [] # Expect empty list on failure as per current implementation
    mock_chromadb_client.list_collections.assert_called_once()

def test_get_or_create_collection_success(client_wrapper, mock_chromadb_client):
    """Tests getting or creating a collection successfully."""
    mock_collection = MagicMock()
    mock_collection.name = "new_col"
    mock_chromadb_client.get_or_create_collection.return_value = mock_collection

    collection = client_wrapper.get_or_create_collection("new_col", metadata={"test": "meta"})
    assert collection is not None
    assert collection.name == "new_col"
    mock_chromadb_client.get_or_create_collection.assert_called_once_with(name="new_col", metadata={"test": "meta"})

def test_get_or_create_collection_failure(client_wrapper, mock_chromadb_client):
    """Tests get/create collection when the underlying client call fails."""
    mock_chromadb_client.get_or_create_collection.side_effect = Exception("Create failed")
    collection = client_wrapper.get_or_create_collection("fail_col")
    assert collection is None
    mock_chromadb_client.get_or_create_collection.assert_called_once_with(name="fail_col", metadata=None)

def test_delete_collection_success(client_wrapper, mock_chromadb_client):
    """Tests deleting a collection successfully."""
    # Mock delete to succeed, and subsequent get to fail (confirming deletion)
    mock_chromadb_client.delete_collection.return_value = None # Assume void return
    mock_chromadb_client.get_collection.side_effect = Exception("Not Found") # Simulate collection is gone

    result = client_wrapper.delete_collection("del_col")
    assert result is True
    mock_chromadb_client.delete_collection.assert_called_once_with(name="del_col")
    mock_chromadb_client.get_collection.assert_called_once_with(name="del_col") # Check confirmation

def test_delete_collection_failure_still_exists(client_wrapper, mock_chromadb_client):
    """Tests deleting when collection still exists after attempt."""
    mock_chromadb_client.delete_collection.return_value = None
    # Mock get_collection to *return* a collection, simulating failed deletion
    mock_chromadb_client.get_collection.return_value = MagicMock()

    result = client_wrapper.delete_collection("fail_del")
    assert result is False
    mock_chromadb_client.delete_collection.assert_called_once_with(name="fail_del")
    mock_chromadb_client.get_collection.assert_called_once_with(name="fail_del")

def test_delete_collection_api_error(client_wrapper, mock_chromadb_client):
    """Tests deleting when the delete call itself raises an exception."""
    mock_chromadb_client.delete_collection.side_effect = Exception("Delete API error")
    # Mock get_collection to succeed *before* the failed delete call (for the check)
    # This case simulates the delete call failing, then the check confirming it exists
    # Let's adjust: Assume delete raises, *then* we check. Check should confirm existence.
    mock_chromadb_client.get_collection.return_value = MagicMock() # Collection exists before/after failed delete

    result = client_wrapper.delete_collection("fail_del_api")
    assert result is False # Should fail because exception was caught and collection still exists
    mock_chromadb_client.delete_collection.assert_called_once_with(name="fail_del_api")
    mock_chromadb_client.get_collection.assert_called_once_with(name="fail_del_api") # Check should be called

def test_get_collection_success(client_wrapper, mock_chromadb_client):
    """Tests getting an existing collection."""
    mock_collection = MagicMock()
    mock_collection.name = "existing_col"
    mock_chromadb_client.get_collection.return_value = mock_collection

    collection = client_wrapper.get_collection("existing_col")
    assert collection is not None
    assert collection.name == "existing_col"
    mock_chromadb_client.get_collection.assert_called_once_with(name="existing_col")

def test_get_collection_not_found(client_wrapper, mock_chromadb_client):
    """Tests getting a non-existent collection."""
    mock_chromadb_client.get_collection.side_effect = Exception("Not Found") # Simulate not found
    collection = client_wrapper.get_collection("non_existent")
    assert collection is None
    mock_chromadb_client.get_collection.assert_called_once_with(name="non_existent")

def test_get_collection_count_success(client_wrapper, mock_chromadb_client):
    """Tests getting the count of a collection."""
    mock_collection = MagicMock()
    mock_collection.name = "countable_col"
    mock_collection.count.return_value = 42
    # Make get_collection return this mock collection
    mock_chromadb_client.get_collection.return_value = mock_collection

    count = client_wrapper.get_collection_count("countable_col")
    assert count == 42
    mock_chromadb_client.get_collection.assert_called_once_with(name="countable_col")
    mock_collection.count.assert_called_once()

def test_get_collection_count_collection_not_found(client_wrapper, mock_chromadb_client):
    """Tests getting count when collection doesn't exist."""
    mock_chromadb_client.get_collection.side_effect = Exception("Not Found")
    count = client_wrapper.get_collection_count("no_such_col")
    assert count is None
    mock_chromadb_client.get_collection.assert_called_once_with(name="no_such_col")

def test_get_collection_count_count_error(client_wrapper, mock_chromadb_client):
    """Tests getting count when collection.count() raises an error."""
    mock_collection = MagicMock()
    mock_collection.name = "error_col"
    mock_collection.count.side_effect = Exception("Count failed")
    mock_chromadb_client.get_collection.return_value = mock_collection

    count = client_wrapper.get_collection_count("error_col")
    assert count is None
    mock_chromadb_client.get_collection.assert_called_once_with(name="error_col")
    mock_collection.count.assert_called_once()

# --- Data Manipulation Tests ---

def test_add_to_collection_success(client_wrapper, mock_chromadb_client):
    """Tests adding items to a collection successfully."""
    mock_collection = MagicMock()
    mock_collection.name = "add_col"
    # Simulate get_collection finding the collection
    mock_chromadb_client.get_collection.return_value = mock_collection

    ids = ["id1", "id2"]
    docs = ["doc1", "doc2"]
    metas = [{"m": 1}, {"m": 2}]

    result = client_wrapper.add_to_collection(
        collection_name="add_col", ids=ids, documents=docs, metadatas=metas
    )

    assert result is True
    mock_chromadb_client.get_collection.assert_called_once_with(name="add_col")
    mock_collection.add.assert_called_once_with(
        ids=ids, documents=docs, embeddings=None, metadatas=metas
    )

def test_add_to_collection_collection_not_found(client_wrapper, mock_chromadb_client):
    """Tests adding items when the collection doesn't exist."""
    mock_chromadb_client.get_collection.return_value = None # Simulate not found

    result = client_wrapper.add_to_collection("no_col", ids=["id1"], documents=["doc1"])
    assert result is False
    mock_chromadb_client.get_collection.assert_called_once_with(name="no_col")

def test_add_to_collection_add_error(client_wrapper, mock_chromadb_client):
    """Tests adding items when collection.add raises an error."""
    mock_collection = MagicMock()
    mock_collection.name = "add_err_col"
    mock_collection.add.side_effect = Exception("Add failed")
    mock_chromadb_client.get_collection.return_value = mock_collection

    result = client_wrapper.add_to_collection("add_err_col", ids=["id1"], documents=["doc1"])
    assert result is False
    mock_chromadb_client.get_collection.assert_called_once_with(name="add_err_col")
    mock_collection.add.assert_called_once()

def test_query_collection_success(client_wrapper, mock_chromadb_client):
    """Tests querying a collection successfully."""
    mock_collection = MagicMock()
    mock_collection.name = "query_col"
    mock_query_results = {"ids": [["id1"]], "distances": [[0.1]], "documents": [["doc1"]]}
    mock_collection.query.return_value = mock_query_results
    mock_chromadb_client.get_collection.return_value = mock_collection

    query_texts = ["query text"]
    n_results = 1

    results = client_wrapper.query_collection(
        collection_name="query_col", query_texts=query_texts, n_results=n_results
    )

    assert results == mock_query_results
    mock_chromadb_client.get_collection.assert_called_once_with(name="query_col")
    mock_collection.query.assert_called_once_with(
        query_embeddings=None,
        query_texts=query_texts,
        n_results=n_results,
        where=None,
        where_document=None,
        include=["metadatas", "documents", "distances"]
    )

def test_query_collection_collection_not_found(client_wrapper, mock_chromadb_client):
    """Tests querying when the collection doesn't exist."""
    mock_chromadb_client.get_collection.return_value = None # Simulate not found

    results = client_wrapper.query_collection("no_col_query", query_texts=["q"], n_results=1)
    assert results is None
    mock_chromadb_client.get_collection.assert_called_once_with(name="no_col_query")

def test_query_collection_query_error(client_wrapper, mock_chromadb_client):
    """Tests querying when collection.query raises an error."""
    mock_collection = MagicMock()
    mock_collection.name = "query_err_col"
    mock_collection.query.side_effect = Exception("Query failed")
    mock_chromadb_client.get_collection.return_value = mock_collection

    results = client_wrapper.query_collection("query_err_col", query_texts=["q"], n_results=1)
    assert results is None
    mock_chromadb_client.get_collection.assert_called_once_with(name="query_err_col")
    mock_collection.query.assert_called_once()

def test_query_collection_no_query_input(client_wrapper, mock_chromadb_client):
    """Tests querying without providing query_texts or query_embeddings."""
    mock_collection = MagicMock()
    mock_collection.name = "no_input_col"
    mock_chromadb_client.get_collection.return_value = mock_collection

    results = client_wrapper.query_collection(collection_name="no_input_col", n_results=1)
    assert results is None
    # Ensure get_collection was called, but query should not be
    mock_chromadb_client.get_collection.assert_called_once_with(name="no_input_col")
    mock_collection.query.assert_not_called() 
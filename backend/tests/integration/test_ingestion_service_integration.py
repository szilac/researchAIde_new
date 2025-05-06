import pytest
import os
import shutil
from PyPDF2 import PdfReader
import logging

# Assuming paths are relative to the project root for imports
from app.services.ingestion_service import IngestionService
from app.services.vector_db_client import VectorDBClient
from app.services.collection_manager import CollectionManager
from app.services.embedding_service import EmbeddingService
from app.config import settings # MODIFIED: Corrected import path for settings

# Configure logging for tests (optional, but can be helpful)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# --- Fixtures ---

@pytest.fixture(scope="module")
def test_pdf_path():
    """Provides the path to the test PDF file."""
    # Workspace root is /media/szilac/SSD_sams/work2/researchAIde_new
    # Test file will be in /media/szilac/SSD_sams/work2/researchAIde_new/backend/tests/integration/
    # Data directory is /media/szilac/SSD_sams/work2/researchAIde_new/backend/tests/data/
    
    # Construct path relative to this test file's location.
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up from backend/tests/integration to backend/
    backend_dir = os.path.dirname(os.path.dirname(current_file_dir)) 
    
    pdf_relative_path = "tests/data/1706.03762v7.pdf" # Relative to backend_dir
    pdf_full_path = os.path.join(backend_dir, pdf_relative_path)

    if not os.path.exists(pdf_full_path):
        pytest.fail(f"Test PDF not found at {pdf_full_path}. Please ensure it's in backend/tests/data/")
    return pdf_full_path

@pytest.fixture(scope="module")
def test_chroma_db_path():
    """Provides a temporary path for the test ChromaDB and ensures cleanup."""
    # Workspace root: /media/szilac/SSD_sams/work2/researchAIde_new
    # Target: /media/szilac/SSD_sams/work2/researchAIde_new/backend/tests/test_chroma_db
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_file_dir))
    path = os.path.join(backend_dir, "tests", "test_chroma_db_integration")
    
    # Clean up before test run if it exists from a previous failed run
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True) # Ensure the directory exists
    
    yield path
    
    # Cleanup after tests in this module are done
    if os.path.exists(path):
        shutil.rmtree(path)

@pytest.fixture(scope="module")
def embedding_service_instance():
    """Provides an instance of the EmbeddingService."""
    # Ensure settings.EMBEDDING_MODEL_NAME is appropriate for testing (e.g., a small local model)
    # If not, you might want to override it here or in a test-specific config
    return EmbeddingService(model_name=settings.DEFAULT_EMBEDDING_MODEL)

@pytest.fixture(scope="module")
def vector_db_client_instance(test_chroma_db_path: str):
    """Provides an instance of the VectorDBClient using a temporary DB path."""
    # Create a copy of the settings to override the DB path for this test client
    # This avoids modifying global settings if other tests rely on the default path.
    from app.config import Settings # Import Settings class for instantiation or use a deepcopy
    
    test_specific_settings = Settings(CHROMA_DB_PATH=test_chroma_db_path)
    # If Settings has other critical default values, ensure they are preserved.
    # A more robust approach might be to deepcopy global settings and then override:
    # import copy
    # test_specific_settings = copy.deepcopy(settings)
    # test_specific_settings.CHROMA_DB_PATH = test_chroma_db_path
    # However, for this specific case, instantiating with the overridden path should be sufficient
    # if CHROMA_DB_PATH is the only critical setting for VectorDBClient's constructor path logic.

    return VectorDBClient(settings=test_specific_settings)

@pytest.fixture(scope="module")
def collection_manager_instance(vector_db_client_instance: VectorDBClient, embedding_service_instance: EmbeddingService):
    """Provides an instance of the CollectionManager."""
    if not embedding_service_instance.model:
        pytest.fail("EmbeddingService model failed to load, cannot provide embedding function for CollectionManager.")

    return CollectionManager(
        vector_db_client=vector_db_client_instance,
        embedding_service=embedding_service_instance
    )

@pytest.fixture(scope="module")
def ingestion_service_instance(
    vector_db_client_instance: VectorDBClient,
    collection_manager_instance: CollectionManager,
    embedding_service_instance: EmbeddingService,
):
    """Provides an instance of the IngestionService."""
    return IngestionService(
        vector_db_client=vector_db_client_instance,
        collection_manager=collection_manager_instance,
        embedding_service=embedding_service_instance,
    )

# --- Test Function ---

def test_ingest_pdf_document_pipeline(
    ingestion_service_instance: IngestionService,
    collection_manager_instance: CollectionManager,
    vector_db_client_instance: VectorDBClient, # For direct verification
    test_pdf_path: str,
):
    """
    Integration test for the IngestionService pipeline using a real PDF.
    1. Extracts text from PDF.
    2. Uses IngestionService to chunk, embed, and store.
    3. Verifies data is added to the correct ChromaDB collection.
    """
    session_id = "test_integration_pdf_session_001"
    document_id = "1706.03762v7_test"
    
    # Ensure collection name is derived consistently
    # The IngestionService itself calls _generate_collection_name and then ensures it exists.
    # We'll pre-create it here for clarity and to ensure a clean state.
    
    # 0. Cleanup potentially existing collection from previous failed runs
    try:
        if vector_db_client_instance.get_collection(collection_manager_instance._generate_collection_name(session_id)):
             collection_manager_instance.delete_research_collection(session_id)
             logger.info(f"Cleaned up existing collection for session_id: {session_id}")
    except Exception as e:
        logger.info(f"No pre-existing collection to cleanup for session_id {session_id} or error: {e}")
        pass 

    # 1. Create the collection for the test
    # IngestionService expects the collection to exist (as per its current logic)
    collection = collection_manager_instance.create_research_collection(
        session_id=session_id,
        research_area="test_integration_research_area"
    )
    assert collection is not None, f"Failed to create collection for session_id: {session_id}"
    collection_name_from_manager = collection.name # Use the name returned by the manager
    
    logger.info(f"Test collection '{collection_name_from_manager}' created for session_id: {session_id}")

    # 2. Extract Text from PDF
    extracted_text = ""
    try:
        reader = PdfReader(test_pdf_path)
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\\n" # Add newline between pages
        logger.info(f"Successfully extracted text from {len(reader.pages)} pages of PDF '{os.path.basename(test_pdf_path)}'.")
    except Exception as e:
        pytest.fail(f"Failed to extract text from PDF {test_pdf_path}: {e}")

    assert extracted_text, f"No text extracted from PDF: {test_pdf_path}"
    logger.info(f"Extracted ~{len(extracted_text)} characters from {document_id}.pdf")

    # 3. Ingest Document using the service
    # Using default chunk size/overlap from IngestionService for this test
    success = ingestion_service_instance.ingest_document(
        session_id=session_id,
        document_id=document_id,
        document_text=extracted_text,
        document_metadata={"source_filename": os.path.basename(test_pdf_path)}, # Example metadata
    )

    # 4. Assertions for Ingestion Success
    assert success, "IngestionService.ingest_document returned False"
    logger.info(f"Ingestion reported success for document_id: {document_id}")

    # 5. Verify data in ChromaDB
    # The collection name used by ingest_document should match collection_name_from_manager
    retrieved_collection = vector_db_client_instance.get_collection(collection_name_from_manager)
    assert retrieved_collection is not None, \
        f"Collection '{collection_name_from_manager}' not found after ingestion."

    count = retrieved_collection.count()
    assert count > 0, f"Collection '{collection_name_from_manager}' is empty after ingestion. Text length: {len(extracted_text)}"
    logger.info(f"Found {count} items in collection '{collection_name_from_manager}'")

    # Retrieve a sample and check metadata
    results = retrieved_collection.get(
        limit=5, # Get a few items
        include=["metadatas", "documents"] 
    )
    
    assert results is not None
    assert len(results["ids"]) > 0, "No items retrieved from the collection"
    
    first_metadata = results["metadatas"][0]
    assert first_metadata["session_id"] == session_id
    assert first_metadata["document_id"] == document_id
    assert first_metadata["source_filename"] == os.path.basename(test_pdf_path)
    assert "chunk_index" in first_metadata 
    logger.info(f"Sample retrieved metadata: {first_metadata}")
    
    # Optional: Check if document content looks reasonable (first few chars of the first chunk)
    first_document_chunk = results["documents"][0]
    assert len(first_document_chunk) > 0, "Retrieved document chunk is empty"
    logger.info(f"Sample retrieved document chunk (first 100 chars): {first_document_chunk[:100]}...")

    # The test_chroma_db_path fixture handles cleanup of the DB directory 
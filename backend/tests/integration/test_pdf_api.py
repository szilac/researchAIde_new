import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os

# Adjust the import path according to your project structure to import the app
# This assumes your tests are run from the workspace root or backend directory
# and backend/app is in PYTHONPATH
from app.main import app  # If running tests from 'backend' directory
# If running from workspace root, it might be from backend.app.main import app

client = TestClient(app)

# Determine the test file directory and construct path relative to it
TESTS_DIR = Path(__file__).resolve().parent # -> backend/tests/integration/
TEST_PDF_FILENAME = "1706.03762v7.pdf"
# Assuming PDF is in backend/tests/
TEST_PDF_PATH = TESTS_DIR.parent / TEST_PDF_FILENAME # -> backend/tests/1706.03762v7.pdf


def test_process_pdf_endpoint_success():
    """
    Test successful PDF processing via the /api/v1/pdf/process/ endpoint.
    """
    assert TEST_PDF_PATH.exists(), f"Test PDF not found at {TEST_PDF_PATH}"

    with open(TEST_PDF_PATH, "rb") as pdf_file:
        files = {"file": (TEST_PDF_FILENAME, pdf_file, "application/pdf")}
        response = client.post("/api/v1/pdf/process/", files=files)

    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    assert "cleaned_text" in data
    assert isinstance(data["cleaned_text"], str)
    assert len(data["cleaned_text"]) > 0, "Cleaned text should not be empty"
    
    assert "structure" in data
    assert isinstance(data["structure"], dict)
    assert "paragraphs" in data["structure"] # Check for at least paragraphs key
    
    assert "source_filename" in data
    assert data["source_filename"] == TEST_PDF_FILENAME
    
    assert "raw_text_preview" in data
    assert isinstance(data["raw_text_preview"], str)
    
    # Check if error key is NOT present on success
    assert "error" not in data or data["error"] is None, f"Error key present in successful response: {data.get('error')}"

    print(f"Successfully tested PDF processing for {TEST_PDF_FILENAME}. Preview: {data['raw_text_preview'][:200]}...")

def test_process_pdf_endpoint_invalid_file_type():
    """
    Test PDF processing endpoint with an invalid file type (not PDF).
    """
    # Create a dummy non-PDF file for testing
    content = b"This is not a PDF."
    files = {"file": ("not_a_pdf.txt", content, "text/plain")}
    
    response = client.post("/api/v1/pdf/process/", files=files)
    
    assert response.status_code == 400, f"Expected status 400, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Invalid file type. Only PDF files are accepted."

def test_process_pdf_endpoint_no_file():
    """
    Test PDF processing endpoint when no file is provided.
    """
    response = client.post("/api/v1/pdf/process/") # No files attached
    
    # FastAPI/Starlette typically returns 422 for validation errors like missing files
    assert response.status_code == 422, f"Expected status 422, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert "detail" in data
    # Check for a message indicating the 'file' field is required
    assert any(err["msg"] == "Field required" and "file" in err["loc"] for err in data["detail"])


# To run this test:
# 1. Ensure your FastAPI application is correctly set up and can be imported.
# 2. Ensure '1706.03762v7.pdf' is in the 'backend/tests/' directory.
# 3. From the 'backend' directory, run: pytest tests/integration/test_pdf_api.py
#    Or from the workspace root: pytest backend/tests/integration/test_pdf_api.py 
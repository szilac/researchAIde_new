import pytest
from fastapi.testclient import TestClient
import time
import uuid # Import uuid module

# Assuming your FastAPI app instance is created in main.py
# Adjust the import path if needed
from main import app 

# Use pytest fixture for the TestClient
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Mark tests that make external calls
@pytest.mark.integration
@pytest.mark.external_api
def test_search_papers_success(client):
    """Test successful search via the /papers/search endpoint."""
    # 1. Create a session first
    session_response = client.post("/api/v1/sessions/", json={})
    assert session_response.status_code == 201
    session_data = session_response.json()
    session_id = session_data['session_id']
    
    # 2. Use the real session ID in the header
    query = "quantum computing"
    max_results = 2
    headers = {"X-Session-ID": session_id} 
    response = client.get(f"/api/v1/papers/search?query={query}&max_results={max_results}", headers=headers)
    
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    # Check if we got roughly the number of results requested (API might return slightly fewer)
    assert len(results) <= max_results 
    if len(results) > 0:
        paper = results[0]
        assert "id" in paper
        assert "title" in paper
        assert "authors" in paper
        assert "summary" in paper
        assert "pdf_url" in paper
        assert "published" in paper
        assert isinstance(paper["authors"], list)
    
    # Add a delay to respect arXiv API rate limits
    time.sleep(3)

@pytest.mark.integration
@pytest.mark.external_api
def test_get_paper_details_success(client):
    """Test successful detail retrieval via the /papers/{arxiv_id} endpoint."""
    # 1. Create a session
    session_response = client.post("/api/v1/sessions/", json={})
    assert session_response.status_code == 201
    session_data = session_response.json()
    session_id = session_data['session_id']

    # 2. Use the real session ID
    # Use a known, relatively stable arXiv ID for testing
    arxiv_id = "1706.03762" # Example: "Attention Is All You Need" paper
    headers = {"X-Session-ID": session_id}
    response = client.get(f"/api/v1/papers/{arxiv_id}", headers=headers)
    
    assert response.status_code == 200
    details = response.json()
    assert isinstance(details, dict)
    # Check if the requested ID is part of the returned ID (accounts for versions)
    assert arxiv_id in details["id"]
    assert "title" in details
    assert "authors" in details
    assert "summary" in details
    assert "pdf_url" in details
    assert "published" in details
    assert "updated" in details 
    # Optional fields might be None, so check existence rather than value
    assert "comment" in details
    assert "journal_ref" in details
    assert "doi" in details
    assert "primary_category" in details
    assert "categories" in details
    assert isinstance(details["authors"], list)
    assert isinstance(details["categories"], list)

    # Add a delay
    time.sleep(3)

@pytest.mark.integration # Doesn't hit external API, but tests endpoint logic
def test_search_papers_empty_query(client):
    """Test search endpoint with an empty query (expect 400)."""
    # 1. Create a session
    session_response = client.post("/api/v1/sessions/", json={})
    assert session_response.status_code == 201
    session_data = session_response.json()
    session_id = session_data['session_id']
    
    # 2. Use the real session ID
    headers = {"X-Session-ID": session_id}
    response = client.get("/api/v1/papers/search?query=", headers=headers)
    assert response.status_code == 400
    assert "Query parameter cannot be empty" in response.json()["detail"]

@pytest.mark.integration
@pytest.mark.external_api
def test_get_paper_details_not_found(client):
    """Test detail retrieval with a non-existent ID (expect 404)."""
    # 1. Create a session
    session_response = client.post("/api/v1/sessions/", json={})
    assert session_response.status_code == 201
    session_data = session_response.json()
    session_id = session_data['session_id']

    # 2. Use the real session ID
    arxiv_id = "invalid-id-that-does-not-exist"
    headers = {"X-Session-ID": session_id}
    response = client.get(f"/api/v1/papers/{arxiv_id}", headers=headers)
    assert response.status_code == 404
    assert f"Paper with ID '{arxiv_id}' not found" in response.json()["detail"]

    # Add a delay
    time.sleep(3) 
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any

from app.services.arxiv_service import ArxivService

router = APIRouter()

arxiv_service = ArxivService() # Instantiate the service

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_arxiv_papers(
    query: str = Query(..., description="The search query string for arXiv."),
    max_results: int = Query(10, description="Maximum number of results to return.")
):
    """
    Search arXiv for papers matching the query.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter cannot be empty.")
    try:
        results = arxiv_service.search_papers(query=query, max_results=max_results)
        return results
    except Exception as e:
        # Log the exception details here if needed
        raise HTTPException(status_code=500, detail=f"An error occurred during the arXiv search: {e}")

@router.get("/{arxiv_id}", response_model=Dict[str, Any])
async def get_arxiv_paper_details(arxiv_id: str):
    """
    Retrieve details for a specific arXiv paper by its ID.
    """
    try:
        details = arxiv_service.get_paper_details(arxiv_id=arxiv_id)
        if details is None:
            raise HTTPException(status_code=404, detail=f"Paper with ID '{arxiv_id}' not found.")
        return details
    except HTTPException as he: # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        # Log the exception details here if needed
        raise HTTPException(status_code=500, detail=f"An error occurred retrieving paper details: {e}") 
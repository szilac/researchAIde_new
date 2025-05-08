"""Mock services and agents for testing."""

from unittest.mock import MagicMock

class MockPhDAgent(MagicMock):
    """Mock for PhDAgent."""
    async def initial_assessment(self, *args, **kwargs):
        return {"assessment_complete": True, "message": "Initial assessment mock"}

    async def formulate_search_queries(self, *args, **kwargs):
        return {"queries_formulated": True, "queries": ["query1", "query2"]}

    async def analyze_search_results(self, *args, **kwargs):
        # Simulate returning a list of analyzed documents or some summary
        return {"analysis_complete": True, "analyzed_results": [{"id": "doc1", "summary": "summary1"}]}

    async def identify_research_gaps(self, *args, **kwargs):
        return {"gaps_identified": True, "research_gaps": ["gap1", "gap2"]}


class MockPostDocAgent(MagicMock):
    """Mock for PostDocAgent."""
    async def generate_research_directions(self, *args, **kwargs):
        return {"directions_generated": True, "research_directions": ["direction1", "direction2"]}

    async def refine_directions(self, *args, **kwargs):
        return {"refinement_complete": True, "refined_directions": ["refined_direction1"]}

    async def evaluate_research_quality(self, *args, **kwargs):
        # This node expects a dict that can be unpacked into GraphState
        return {"assessment": {"quality": "high", "feedback": "Good work"}, "message": "Evaluation mock"}


class MockArxivService(MagicMock):
    """Mock for ArxivService."""
    async def search_papers(self, *args, **kwargs):
        # Simulate returning a list of paper objects
        return [{"title": "Paper 1", "summary": "Summary 1", "authors": ["Auth A"], "pdf_url": "url1"}]


class MockPyPDF2Processor(MagicMock):
    """Mock for PyPDF2Processor."""
    async def process_pdf(self, *args, **kwargs):
        # Simulate returning extracted text
        return "Extracted PDF text content."


class MockIngestionService(MagicMock):
    """Mock for IngestionService."""
    async def ingest_document(self, *args, **kwargs):
        # Simulate successful ingestion
        return {"document_id": "doc_123", "status": "ingested"}

    async def ingest_documents_concurrently(self, *args, **kwargs):
        return [{"document_id": f"doc_{i}", "status": "ingested"} for i in range(len(kwargs.get("documents", [])))]


class MockVectorDBClient(MagicMock):
    """Mock for VectorDBClient."""
    async def query_similar_documents(self, *args, **kwargs):
        # Simulate returning similar documents
        return [{"id": "sim_doc1", "content": "similar content"}]

    async def add_documents(self, *args, **kwargs):
        return {"added_count": len(kwargs.get("documents", [])), "status": "success"}

# Example of how you might make them more specific if needed:
# class MockPhDAgentWithSpecifics(MagicMock):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.initial_assessment = MagicMock(return_value={"assessment_complete": True})
#         # etc. for other methods 
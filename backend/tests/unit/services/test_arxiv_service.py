import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

# Assuming ArxivService is importable like this
from app.services.arxiv_service import ArxivService 
import arxiv # Import arxiv to mock its classes/methods

# Mock arxiv.Result class structure for testing
class MockAuthor:
    def __init__(self, name):
        self.name = name

class MockArxivResult:
    def __init__(self, entry_id, title, authors_names, summary, pdf_url, published_iso, updated_iso=None, comment=None, journal_ref=None, doi=None, primary_category=None, categories=None):
        self.entry_id = entry_id
        self.title = title
        self.authors = [MockAuthor(name) for name in authors_names]
        self.summary = summary
        self.pdf_url = pdf_url
        # Simulate datetime object for published/updated
        self.published = datetime.fromisoformat(published_iso.replace('Z', '+00:00')) 
        self.updated = datetime.fromisoformat(updated_iso.replace('Z', '+00:00')) if updated_iso else None
        self.comment = comment
        self.journal_ref = journal_ref
        self.doi = doi
        self.primary_category = primary_category
        self.categories = categories

@pytest.fixture
def arxiv_service():
    """Provides an instance of ArxivService for testing."""
    return ArxivService()

@pytest.fixture
def mock_arxiv_search():
    """Fixture to mock the arxiv.Search class."""
    with patch('app.services.arxiv_service.arxiv.Search', autospec=True) as mock_search_class:
        yield mock_search_class

def test_search_papers_success(arxiv_service, mock_arxiv_search, mocker):
    """Test successful paper search."""
    # Arrange
    mock_result_1 = MockArxivResult(
        entry_id='http://arxiv.org/abs/2301.00001v1', 
        title='Test Paper 1', 
        authors_names=['Author A', 'Author B'], 
        summary='Summary 1', 
        pdf_url='http://arxiv.org/pdf/2301.00001v1',
        published_iso='2023-01-01T10:00:00Z'
    )
    mock_result_2 = MockArxivResult(
        entry_id='http://arxiv.org/abs/2301.00002v1', 
        title='Test Paper 2', 
        authors_names=['Author C'], 
        summary='Summary 2', 
        pdf_url='http://arxiv.org/pdf/2301.00002v1',
        published_iso='2023-01-02T11:00:00Z'
    )
    
    # Mock the results() method of the search instance
    mock_search_instance = mock_arxiv_search.return_value
    mock_search_instance.results.return_value = iter([mock_result_1, mock_result_2])

    # Mock the helper method directly to isolate the search_papers logic
    with patch.object(arxiv_service, '_get_search_results', return_value=iter([mock_result_1, mock_result_2])) as mock_helper:
        # Act
        results = arxiv_service.search_papers(query='test query', max_results=2)

        # Assert
        mock_arxiv_search.assert_called_once_with(
            query='test query', 
            max_results=2, 
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        mock_helper.assert_called_once() # Check helper was called
        assert len(results) == 2
        assert results[0]['id'] == '2301.00001v1'
        assert results[0]['title'] == 'Test Paper 1'
        assert results[0]['authors'] == ['Author A', 'Author B']
        assert results[0]['summary'] == 'Summary 1'
        assert results[0]['pdf_url'] == 'http://arxiv.org/pdf/2301.00001v1'
        assert results[0]['published'] == '2023-01-01T10:00:00+00:00' 
        assert results[1]['id'] == '2301.00002v1'
        assert results[1]['title'] == 'Test Paper 2'

def test_get_paper_details_success(arxiv_service, mock_arxiv_search, mocker):
    """Test successful retrieval of paper details."""
    # Arrange
    arxiv_id = '2301.00003v1'
    mock_detailed_result = MockArxivResult(
        entry_id=f'http://arxiv.org/abs/{arxiv_id}', 
        title='Detailed Paper', 
        authors_names=['Author D'], 
        summary='Detailed Summary', 
        pdf_url=f'http://arxiv.org/pdf/{arxiv_id}',
        published_iso='2023-01-03T12:00:00Z',
        updated_iso='2023-01-04T13:00:00Z',
        comment='A comment',
        journal_ref='Journal Vol 1',
        doi='10.1000/test',
        primary_category='cs.AI',
        categories=['cs.AI', 'stat.ML']
    )
    
    # Mock the results() method to yield one result
    mock_search_instance = mock_arxiv_search.return_value
    mock_search_instance.results.return_value = iter([mock_detailed_result])

    # Mock the helper method
    with patch.object(arxiv_service, '_get_single_result', return_value=mock_detailed_result) as mock_helper:
        # Act
        details = arxiv_service.get_paper_details(arxiv_id=arxiv_id)

        # Assert
        mock_arxiv_search.assert_called_once_with(id_list=[arxiv_id])
        mock_helper.assert_called_once() # Check helper was called
        assert details is not None
        assert details['id'] == arxiv_id
        assert details['title'] == 'Detailed Paper'
        assert details['authors'] == ['Author D']
        assert details['summary'] == 'Detailed Summary'
        assert details['pdf_url'] == f'http://arxiv.org/pdf/{arxiv_id}'
        assert details['published'] == '2023-01-03T12:00:00+00:00'
        assert details['updated'] == '2023-01-04T13:00:00+00:00'
        assert details['comment'] == 'A comment'
        assert details['journal_ref'] == 'Journal Vol 1'
        assert details['doi'] == '10.1000/test'
        assert details['primary_category'] == 'cs.AI'
        assert details['categories'] == ['cs.AI', 'stat.ML']


def test_get_paper_details_not_found(arxiv_service, mock_arxiv_search, mocker):
    """Test retrieval when paper ID is not found."""
    # Arrange
    arxiv_id = 'not_found_id'
    
    # Mock the results() method to yield nothing
    mock_search_instance = mock_arxiv_search.return_value
    mock_search_instance.results.return_value = iter([]) # Empty iterator

     # Mock the helper method
    with patch.object(arxiv_service, '_get_single_result', return_value=None) as mock_helper:
        # Act
        details = arxiv_service.get_paper_details(arxiv_id=arxiv_id)

        # Assert
        mock_arxiv_search.assert_called_once_with(id_list=[arxiv_id])
        mock_helper.assert_called_once() # Check helper was called
        assert details is None

# TODO: Add tests for retry logic (e.g., mocking exceptions from _get_search_results/_get_single_result)
# TODO: Add tests for edge cases (e.g., empty query, API errors if not fully mocked by helpers) 
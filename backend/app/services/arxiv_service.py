import arxiv
import time
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError, retry_if_exception_type
from typing import List, Dict, Any, Iterator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a retry strategy: wait 3 seconds between attempts, stop after 3 attempts
# Retry on common Arxiv errors or general Exceptions
retry_strategy = retry(
    wait=wait_fixed(3),
    stop=stop_after_attempt(3),
    retry_error_callback=lambda retry_state: logger.error(f"Arxiv API call failed after {retry_state.attempt_number} attempts: {retry_state.outcome.exception()}"),
    # Specify exceptions to retry on. Adjust based on observed errors.
    retry=(retry_if_exception_type(arxiv.HTTPError) | retry_if_exception_type(ConnectionError) | retry_if_exception_type(TimeoutError))
)


class ArxivService:
    def __init__(self):
        # Initialization, if any
        pass

    @retry_strategy
    def _get_search_results(self, search: arxiv.Search) -> Iterator[arxiv.Result]:
        """Helper method to get iterator with retry logic."""
        logger.info(f"Fetching results for query: {search.query}, id_list: {search.id_list}")
        return search.results()

    def search_papers(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Searches arXiv for papers matching the query with retry logic."""
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        results = []
        try:
            result_iterator = self._get_search_results(search)
            for result in result_iterator:
                results.append({
                    "id": result.entry_id.split('/')[-1],
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary,
                    "pdf_url": result.pdf_url,
                    "published": result.published.isoformat(),
                    # Add other fields if needed
                })
                # Optional: Add a small delay even within successful iteration if needed,
                # but the main delay is handled by the retry decorator between attempts.
                # time.sleep(0.5)
        except RetryError as e:
            logger.error(f"Failed to retrieve search results for query '{query}' after multiple retries: {e}")
            # Depending on desired behavior, could return empty list or raise exception
            return [] 
        except Exception as e:
            logger.error(f"An unexpected error occurred during paper search for query '{query}': {e}")
            return []

        return results

    @retry_strategy
    def _get_single_result(self, search: arxiv.Search) -> arxiv.Result | None:
        """Helper method to get a single result with retry logic."""
        logger.info(f"Fetching single result for id_list: {search.id_list}")
        try:
            return next(search.results())
        except StopIteration:
            logger.warning(f"No paper found for id_list: {search.id_list}")
            return None

    def get_paper_details(self, arxiv_id: str) -> Dict[str, Any] | None:
        """Fetches details for a specific arXiv paper by its ID with retry logic."""
        search = arxiv.Search(id_list=[arxiv_id])

        try:
            result = self._get_single_result(search)
            if result:
                return {
                    "id": result.entry_id.split('/')[-1],
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary,
                    "pdf_url": result.pdf_url,
                    "published": result.published.isoformat(),
                    "updated": result.updated.isoformat(),
                    "comment": result.comment,
                    "journal_ref": result.journal_ref,
                    "doi": result.doi,
                    "primary_category": result.primary_category,
                    "categories": result.categories,
                    # Add other fields if needed
                }
            else:
                return None # Paper not found
        except RetryError as e:
             logger.error(f"Failed to retrieve details for paper ID '{arxiv_id}' after multiple retries: {e}")
             return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching details for paper ID '{arxiv_id}': {e}")
            return None 
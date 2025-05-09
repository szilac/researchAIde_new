import arxiv
import time
import os
from PyPDF2 import PdfReader

class ArxivSearch:
    def __init__(self):
        # Construct the default API client.
        self.sch_engine = arxiv.Client()
        
    def _process_query(self, query: str) -> str:
        """Process query string to fit within MAX_QUERY_LENGTH while preserving as much information as possible"""
        MAX_QUERY_LENGTH = 300
        
        if len(query) <= MAX_QUERY_LENGTH:
            return query
        
        # Split into words
        words = query.split()
        processed_query = []
        current_length = 0
        
        # Add words while staying under the limit
        # Account for spaces between words
        for word in words:
            # +1 for the space that will be added between words
            if current_length + len(word) + 1 <= MAX_QUERY_LENGTH:
                processed_query.append(word)
                current_length += len(word) + 1
            else:
                break
            
        return ' '.join(processed_query)
    
    def find_papers_by_str(self, query, N=20):
        processed_query = self._process_query(query)
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                search = arxiv.Search(
                    query="abs:" + processed_query,
                    max_results=N,
                    sort_by=arxiv.SortCriterion.Relevance)

                paper_sums = list()
                # `results` is a generator; you can iterate over its elements one by one...
                for r in self.sch_engine.results(search):
                    paperid = r.pdf_url.split("/")[-1]
                    pubdate = str(r.published).split(" ")[0]
                    paper_sum = f"Title: {r.title}\n"
                    paper_sum += f"Summary: {r.summary}\n"
                    paper_sum += f"Publication Date: {pubdate}\n"
                    #paper_sum += f"Categories: {' '.join(r.categories)}\n"
                    paper_sum += f"arXiv paper ID: {paperid}\n"
                    paper_sums.append(paper_sum)
                time.sleep(2.0)
                return "\n".join(paper_sums)
                
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2 * retry_count)
                    continue
        return None

    def retrieve_full_paper_text(self, query, MAX_LEN=50000):
        pdf_text = str()
        paper = next(arxiv.Client().results(arxiv.Search(id_list=[query])))
        # Download the PDF to the PWD with a custom filename.
        paper.download_pdf(filename="downloaded-paper.pdf")
        # creating a pdf reader object
        reader = PdfReader('downloaded-paper.pdf')
        # Iterate over all the pages
        for page_number, page in enumerate(reader.pages, start=1):
            # Extract text from the page
            try:
                text = page.extract_text()
            except Exception as e:
                os.remove("downloaded-paper.pdf")
                time.sleep(2.0)
                return "EXTRACTION FAILED"

            # Do something with the text (e.g., print it)
            pdf_text += f"--- Page {page_number} ---"
            pdf_text += text
            pdf_text += "\n"
        os.remove("downloaded-paper.pdf")
        time.sleep(2.0)
        return pdf_text[:MAX_LEN]
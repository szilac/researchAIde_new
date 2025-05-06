import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import PyPDF2 # Added import
import spacy # Added import
import re # Added import

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load spaCy model (consider loading once outside the class if used frequently)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.error("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    # Handle the error appropriately - maybe raise an exception or have a fallback
    nlp = None

class PDFProcessorBase(ABC):
    """
    Abstract base class for PDF processing.

    Defines the common interface for different PDF extraction methods.
    Requires subclasses to implement core processing logic.
    Includes basic error handling and logging.
    """

    def __init__(self, pdf_path: str | Path):
        """
        Initializes the processor with the path to the PDF file.

        Args:
            pdf_path: Path to the PDF file to be processed.
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.is_file() or self.pdf_path.suffix.lower() != '.pdf':
            raise ValueError(f"Invalid PDF path: {self.pdf_path}")
        logger.info(f"Initialized PDF processor for: {self.pdf_path.name}")

    @abstractmethod
    def extract_text(self) -> str:
        """
        Extracts raw text content from the entire PDF document.

        Must be implemented by subclasses using specific library methods.

        Returns:
            A string containing the extracted text.
        """
        pass

    @abstractmethod
    def extract_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyzes the extracted text to identify document structure.
        (e.g., sections, paragraphs, references).

        Must be implemented by subclasses, potentially using NLP techniques.

        Args:
            text: The raw text extracted from the PDF.

        Returns:
            A dictionary representing the document structure.
            The exact format will depend on the implementation.
        """
        pass

    @abstractmethod
    def clean_text(self, text: str) -> str:
        """
        Cleans and normalizes the extracted text.
        (e.g., remove headers/footers, fix hyphenation).

        Must be implemented by subclasses.

        Args:
            text: The raw text extracted from the PDF.

        Returns:
            A string containing the cleaned text.
        """
        pass

    def process(self) -> Dict[str, Any]:
        """
        Orchestrates the PDF processing workflow: extract, clean, structure.

        Returns:
            A dictionary containing the processing results (e.g., cleaned text, structure).
            Returns an empty dict if processing fails.
        """
        logger.info(f"Starting processing for {self.pdf_path.name}")
        results = {}
        try:
            raw_text = self.extract_text()
            if not raw_text:
                logger.warning(f"No text extracted from {self.pdf_path.name}")
                return results

            cleaned_text = self.clean_text(raw_text)
            if not cleaned_text:
                logger.warning(f"Text cleaning resulted in empty string for {self.pdf_path.name}")
                # Decide if we should proceed with raw text or stop
                cleaned_text = raw_text # Fallback for now

            structure = self.extract_structure(cleaned_text) # Use cleaned text for structure analysis

            results = {
                "raw_text_preview": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text, # For logging/preview
                "cleaned_text": cleaned_text,
                "structure": structure,
                "source_filename": self.pdf_path.name
            }
            logger.info(f"Successfully processed {self.pdf_path.name}")

        except Exception as e:
            logger.error(f"Error processing {self.pdf_path.name}: {e}", exc_info=True)
            # Optionally, return partial results or specific error info
            results = {"error": str(e), "source_filename": self.pdf_path.name}

        return results

    # --- Optional Common Utilities ---

    def _common_utility_example(self):
        """Example of a common utility method subclasses might use."""
        logger.debug("Executing common utility")
        # Implementation here
        pass

# --- Concrete Implementations ---

class PyPDF2Processor(PDFProcessorBase):
    """
    Concrete implementation of PDFProcessorBase using the PyPDF2 library.
    Focuses on basic text extraction.
    """

    def extract_text(self) -> str:
        """
        Extracts text from the PDF using PyPDF2.

        Returns:
            The extracted text as a single string, or an empty string if extraction fails.
        """
        logger.info(f"Extracting text using PyPDF2 for {self.pdf_path.name}...")
        text = ""
        try:
            with open(self.pdf_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(reader.pages)
                logger.debug(f"Found {num_pages} pages.")
                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n" # Add newline between pages
            logger.info(f"Successfully extracted text using PyPDF2 from {self.pdf_path.name}")
            return text.strip()
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"PyPDF2 error reading {self.pdf_path.name}: {e}")
            # Potentially try other methods or raise specific exception
            return "" # Return empty on read error for now
        except Exception as e:
            logger.error(f"Unexpected error during PyPDF2 extraction for {self.pdf_path.name}: {e}", exc_info=True)
            return ""

    def extract_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyzes extracted text to identify structure (paragraphs, headers, references).
        Uses basic regex for headers/references and newline heuristics for paragraphs.
        Reflects work for subtasks 6.6 and incorporates regex from 6.4.
        """
        logger.info(f"Extracting structure using spaCy/regex for {self.pdf_path.name}...")
        if not nlp:
            logger.error("spaCy model not loaded. Cannot extract structure.")
            return {}

        structure = {
            "paragraphs": [],
            "headers": [],
            "references": []
        }
        # Regex patterns (simple examples, can be expanded)
        # Header: Starts with I., II., 1., 1.1., A., etc. followed by text
        header_pattern = re.compile(r"^([IVXLCDM]+|[A-Z]|[0-9]+(?:\.[0-9]+)*)\.\s+.+")
        # Reference: Starts with [1] or (1)
        ref_pattern = re.compile(r"^\s*[\[\(]\d+[\]\)]\s+.+")

        try:
            # Split into potential lines/blocks based on newlines first
            lines = text.split('\n')
            current_paragraph = ""

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    # Empty line often signifies paragraph break
                    if current_paragraph:
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    continue

                is_header = header_pattern.match(line_stripped)
                is_reference = ref_pattern.match(line_stripped)

                if is_header:
                    if current_paragraph: # End previous paragraph
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    structure["headers"].append(line_stripped)
                elif is_reference:
                    if current_paragraph: # End previous paragraph
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    structure["references"].append(line_stripped)
                else:
                    # Append to current paragraph
                    current_paragraph += (" " if current_paragraph else "") + line_stripped

            # Add any trailing paragraph
            if current_paragraph:
                structure["paragraphs"].append(current_paragraph.strip())

            # SpaCy processing can be added here for more detailed analysis if needed
            # doc = nlp(text) # Process full text
            # sentences = [sent.text.strip() for sent in doc.sents] # Example

            logger.info(f"Successfully extracted structure for {self.pdf_path.name}")

        except Exception as e:
            logger.error(f"Error during structure extraction for {self.pdf_path.name}: {e}", exc_info=True)
            return {} # Return empty dict on error

        return structure

    def clean_text(self, text: str) -> str:
        """
        Cleans and normalizes the extracted text using basic regex operations.
        Focuses on fixing hyphenation and normalizing whitespace.
        More advanced cleaning (headers/footers) can be added later.

        Args:
            text: The raw text extracted from the PDF.

        Returns:
            A string containing the cleaned text.
        """
        logger.info(f"Cleaning text for {self.pdf_path.name}...")
        if not text:
            return ""

        cleaned_text = text

        # 1. Fix hyphenation across line breaks
        # Looks for a word ending in hyphen, followed by newline, then a word starting with lowercase letter
        cleaned_text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", cleaned_text)

        # 2. Normalize whitespace
        # Replace multiple spaces/tabs with a single space
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        # Replace multiple newlines with a single newline (or double for paragraphs if preferred)
        # Let's keep double newlines for paragraph structure identified in extract_structure
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        # Remove leading/trailing whitespace from the whole text and individual lines
        cleaned_text = "\n".join([line.strip() for line in cleaned_text.strip().split('\n')])

        # 3. Handle special characters (Optional - basic example: replace ligatures)
        # This is highly dependent on the content and desired output
        # cleaned_text = cleaned_text.replace('\ufb01', 'fi').replace('\ufb02', 'fl') # Example for fi/fl ligatures

        # 4. TODO: Add logic for header/footer removal if feasible patterns exist

        logger.info(f"Successfully cleaned text for {self.pdf_path.name}")
        return cleaned_text

# Example of how a subclass might look (to be implemented in later subtasks)
# class PyPDF2Processor(PDFProcessorBase):
#     def extract_text(self) -> str:
#         # Implementation using PyPDF2
#         logger.info("Extracting text using PyPDF2...")
#         return "Text extracted via PyPDF2"

#     def extract_structure(self, text: str) -> Dict[str, Any]:
#         logger.info("Extracting structure (basic) after PyPDF2...")
#         # Basic structure extraction or call to NLP service
#         return {"sections": ["Introduction", "Conclusion"]}

#     def clean_text(self, text: str) -> str:
#         logger.info("Cleaning text after PyPDF2...")
#         # Basic cleaning
#         return text.strip() 
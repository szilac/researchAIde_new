import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import PyPDF2 # Added import
import spacy # Added import
import re # Added import
import asyncio # Added
import aiohttp # Added
import tempfile # Added

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

    def __init__(self, pdf_url_or_path: Union[str, Path]):
        """
        Initializes the processor with the path or URL to the PDF file.

        Args:
            pdf_url_or_path: URL string or Path object for the PDF file.
        """
        self.input_location = pdf_url_or_path # Store original input
        self.pdf_path: Optional[Path] = None # Will be set after download/validation
        self._is_temp_file: bool = False
        self._temp_file_path: Optional[Path] = None
        # Validation happens in process or a dedicated setup method

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

    async def _download_if_url(self) -> None:
        """Downloads the PDF if input_location is a URL, sets self.pdf_path to temp path."""
        if isinstance(self.input_location, str) and self.input_location.startswith(('http://', 'https://')):
            logger.info(f"Input is a URL, attempting download: {self.input_location}")
            try:
                # Create a temp file first
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    self._temp_file_path = Path(tmp_file.name)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.input_location) as response:
                        response.raise_for_status() # Raise exception for bad status codes
                        # Write content to the temp file
                        with open(self._temp_file_path, 'wb') as f_out:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                        self.pdf_path = self._temp_file_path
                        self._is_temp_file = True
                        logger.info(f"Successfully downloaded URL to temporary file: {self.pdf_path}")
            except Exception as e:
                logger.error(f"Failed to download PDF from URL {self.input_location}: {e}", exc_info=True)
                # Clean up temp file if download failed partially
                if self._temp_file_path and self._temp_file_path.exists():
                    try: self._temp_file_path.unlink() 
                    except OSError: pass
                raise IOError(f"Failed to download PDF from {self.input_location}") from e
        elif isinstance(self.input_location, Path):
            logger.info(f"Input is a Path object: {self.input_location}")
            self.pdf_path = self.input_location
            self._is_temp_file = False
        elif isinstance(self.input_location, str):
             logger.info(f"Input is a string, assuming local path: {self.input_location}")
             self.pdf_path = Path(self.input_location)
             self._is_temp_file = False
        else:
             raise ValueError(f"Invalid input type for pdf_url_or_path: {type(self.input_location)}")
        
        # Final validation of the determined self.pdf_path
        if not self.pdf_path or not self.pdf_path.is_file() or self.pdf_path.suffix.lower() != '.pdf':
             raise ValueError(f"Invalid or non-existent PDF path determined: {self.pdf_path}")

    async def process(self) -> Dict[str, Any]:
        """
        Orchestrates the PDF processing workflow: download (if URL), extract, clean, structure.
        Cleans up temporary file if one was created.

        Returns:
            A dictionary containing the processing results (e.g., cleaned text, structure).
            Includes an 'error' key if processing fails.
        """
        results = {}
        try:
            await self._download_if_url() # Handles download and sets self.pdf_path
            logger.info(f"Starting processing for {self.pdf_path.name} (Path: {self.pdf_path})")
            
            # Run synchronous methods in thread pool
            raw_text = await asyncio.to_thread(self.extract_text)
            if not raw_text:
                logger.warning(f"No text extracted from {self.pdf_path.name}")
                # Decide if we want to return error or empty results
                return {"error": "No text extracted", "source_filename": self.pdf_path.name}

            cleaned_text = await asyncio.to_thread(self.clean_text, raw_text)
            if not cleaned_text:
                logger.warning(f"Text cleaning resulted in empty string for {self.pdf_path.name}")
                cleaned_text = raw_text # Fallback

            structure = await asyncio.to_thread(self.extract_structure, cleaned_text)

            results = {
                "raw_text_preview": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text,
                "cleaned_text": cleaned_text,
                "structure": structure,
                "source_filename": self.pdf_path.name
            }
            logger.info(f"Successfully processed {self.pdf_path.name}")

        except Exception as e:
            logger.error(f"Error processing {self.input_location}: {e}", exc_info=True)
            results = {"error": str(e), "source_filename": getattr(self.pdf_path, 'name', str(self.input_location))}
        finally:
            # Clean up the temporary file if it was created
            if self._is_temp_file and self.pdf_path and self.pdf_path.exists():
                try:
                    self.pdf_path.unlink()
                    logger.info(f"Cleaned up temporary file: {self.pdf_path}")
                except Exception as e_unlink:
                    logger.error(f"Error deleting temporary file {self.pdf_path}: {e_unlink}")
                    # Log error but don't necessarily overwrite primary error in results

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
    Now handles URLs via inherited async process method.
    """

    def extract_text(self) -> str:
        """
        Extracts text from the PDF using PyPDF2.
        Expects self.pdf_path to be set by the process() method.

        Returns:
            The extracted text as a single string, or an empty string if extraction fails.
        """
        if not self.pdf_path:
            logger.error("extract_text called but self.pdf_path is not set.")
            return ""
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
            return "" 
        except Exception as e:
            logger.error(f"Unexpected error during PyPDF2 extraction for {self.pdf_path.name}: {e}", exc_info=True)
            return ""

    def extract_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyzes extracted text to identify structure (paragraphs, headers, references).
        Uses basic regex for headers/references and newline heuristics for paragraphs.
        Reflects work for subtasks 6.6 and incorporates regex from 6.4.
        Expects self.pdf_path to be set by the process() method.
        """
        if not self.pdf_path:
             logger.error("extract_structure called but self.pdf_path is not set.")
             return {}
        logger.info(f"Extracting structure using spaCy/regex for {self.pdf_path.name}...")
        if not nlp:
            logger.error("spaCy model not loaded. Cannot extract structure.")
            return {}
        
        structure = {
            "paragraphs": [],
            "headers": [],
            "references": []
        }
        header_pattern = re.compile(r"^([IVXLCDM]+|[A-Z]|[0-9]+(?:\.[0-9]+)*)\.\s+.+")
        ref_pattern = re.compile(r"^\s*[\[\(]\d+[\]\)]\s+.+")

        try:
            lines = text.split('\n')
            current_paragraph = ""
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    if current_paragraph:
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    continue
                is_header = header_pattern.match(line_stripped)
                is_reference = ref_pattern.match(line_stripped)
                if is_header:
                    if current_paragraph:
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    structure["headers"].append(line_stripped)
                elif is_reference:
                    if current_paragraph:
                        structure["paragraphs"].append(current_paragraph.strip())
                        current_paragraph = ""
                    structure["references"].append(line_stripped)
                else:
                    current_paragraph += (" " if current_paragraph else "") + line_stripped
            if current_paragraph:
                structure["paragraphs"].append(current_paragraph.strip())
            logger.info(f"Successfully extracted structure for {self.pdf_path.name}")
        except Exception as e:
            logger.error(f"Error during structure extraction for {self.pdf_path.name}: {e}", exc_info=True)
            return {}

        return structure

    def clean_text(self, text: str) -> str:
        """
        Cleans and normalizes the extracted text using basic regex operations.
        Focuses on fixing hyphenation and normalizing whitespace.
        Expects self.pdf_path to be set by the process() method.

        Args:
            text: The raw text extracted from the PDF.

        Returns:
            A string containing the cleaned text.
        """
        if not self.pdf_path:
             logger.error("clean_text called but self.pdf_path is not set.")
             return ""
        logger.info(f"Cleaning text for {self.pdf_path.name}...")
        if not text:
            return ""

        cleaned_text = text
        cleaned_text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", cleaned_text)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        cleaned_text = "\n".join([line.strip() for line in cleaned_text.strip().split('\n')])

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
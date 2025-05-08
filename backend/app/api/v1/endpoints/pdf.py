import logging
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.pdf_processor import PyPDF2Processor # Assuming PyPDF2Processor is the one to use for now

logger = logging.getLogger(__name__)

router = APIRouter()

# Define Pydantic model for the response
class PDFProcessResponse(BaseModel):
    cleaned_text: str
    structure: Dict[str, Any] = {} # Default to empty dict if structure fails
    source_filename: str
    raw_text_preview: Optional[str] = None
    # Note: We handle errors via HTTPException now, so 'error' key might not be needed here
    # If processor.process() might return an 'error' key even on success, add it back:
    # error: Optional[str] = None

@router.post(
    "/process/",
    response_model=PDFProcessResponse, # Added response model
    tags=["PDF Processing"]
)
async def process_pdf_endpoint(
    file: UploadFile = File(..., description="PDF file to process")
):
    """
    Processes an uploaded PDF file to extract text and basic structure.

    - Accepts a PDF file.
    - Uses the PyPDF2Processor to extract and clean text, and identify basic structure.
    - Returns the processed data or an error message.
    """
    logger.info(f"Received file for processing: {file.filename}, content type: {file.content_type}")

    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type uploaded: {file.content_type} for file {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are accepted.")

    temp_pdf_path: Optional[Path] = None
    try:
        # Save UploadFile to a temporary file to pass its path to the processor
        # PyPDF2Processor expects a file path
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_pdf_path = Path(temp_file.name)
        logger.debug(f"Saved uploaded file to temporary path: {temp_pdf_path}")

        # Instantiate processor using the correct keyword argument
        processor = PyPDF2Processor(pdf_url_or_path=temp_pdf_path)
        # Await the now async process() method
        results = await processor.process() 

        if not results or results.get("error"):
            error_detail = results.get("error", "Unknown processing error")
            logger.error(f"Processing failed for {file.filename}: {error_detail}")
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {error_detail}")

        logger.info(f"Successfully processed file: {file.filename}")
        if "structure" not in results:
            results["structure"] = {}
        results["source_filename"] = file.filename
        return results # FastAPI will validate this against PDFProcessResponse

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        if temp_pdf_path and temp_pdf_path.exists():
            try:
                temp_pdf_path.unlink() # Clean up the temporary file
                logger.debug(f"Cleaned up temporary file: {temp_pdf_path}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary file {temp_pdf_path}: {e}", exc_info=True)
        await file.close() # Ensure the uploaded file stream is closed 
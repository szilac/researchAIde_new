import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# import logging # Removed placeholder import

from app.api.v1.api import api_router as api_v1_router
from app.middleware.session_middleware import SessionMiddleware # Added import
from app.tasks.session_cleanup import run_cleanup_task # Added import

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

# Get logger instance (optional, can use logging directly)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background task
    logger.info("Application startup: Starting session cleanup task...")
    # Run hourly by default
    cleanup_task = asyncio.create_task(run_cleanup_task(interval_seconds=3600))
    yield
    # Shutdown: Cancel the background task
    logger.info("Application shutdown: Stopping session cleanup task...")
    cleanup_task.cancel()
    try:
        # Wait for the task to finish cancellation
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Session cleanup task successfully cancelled.")
    except Exception as e:
        # Log any other errors during task shutdown
        logger.error(f"Error during cleanup task shutdown: {e}", exc_info=True)

# Pass lifespan context manager to FastAPI app
app = FastAPI(lifespan=lifespan)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Use the configured logger
    logger.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Session Validation Middleware (added)
app.add_middleware(SessionMiddleware)

app.include_router(api_v1_router, prefix="/api/v1")

# The old root endpoint is removed. 
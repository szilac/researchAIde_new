# ResearchAIde

AI-powered research assistant to help manage, search, and summarize research papers.

## Project Structure

```
researchAIde_new/
├── backend/         # FastAPI backend application
│   └── requirements.txt
├── frontend/        # React frontend application
│   └── package.json
├── data/            # Data storage
│   ├── chroma_db/   # Chroma vector database files
│   ├── papers/      # Original PDF paper storage
│   └── uploads/     # Temporary upload storage
├── docs/            # Project documentation
├── scripts/         # Utility and helper scripts
├── tasks/           # Task management files (Taskmaster)
├── .cursor/
├── .env.example     # Example environment variables
├── .gitignore
├── .taskmasterconfig # Taskmaster configuration
└── README.md
```

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

### Backend Setup

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Frontend Setup

1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    # or
    # yarn install
    ```

### Environment Variables

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Fill in the required values in the `.env` file.

## Running the Application

*(Instructions to be added)*

## Contributing

*(Contribution guidelines to be added)*

## Vector Store Integration (ChromaDB)

The application uses ChromaDB as its local vector store for enabling semantic search and analysis of research papers. This integration allows for efficient storage, indexing, and retrieval of document chunks based on their semantic similarity to a query.

### Key Services

The core functionality is managed by the following services located in `backend/app/services/`:

*   **`VectorDBClient` (`vector_db_client.py`)**: Provides a low-level wrapper around the ChromaDB client. It handles the direct initialization of the `chromadb.PersistentClient` and offers basic methods for managing collections (create, list, get, delete) and data within them (add, query).

*   **`CollectionManager` (`collection_manager.py`)**: Sits on top of the `VectorDBClient` and enforces application-specific logic for research collections. This includes standardized naming conventions (e.g., `research_session_<session_id>`) and ensures required metadata (like `session_id`, `research_area`) is associated with collections.

*   **`EmbeddingService` (`embedding_service.py`)**: Responsible for generating vector embeddings from text. It currently uses local sentence-transformer models (e.g., `all-MiniLM-L6-v2`) but is designed to be extensible for other embedding providers.

*   **`ChunkingService` (`chunking_service.py`)**: Contains utilities for breaking down large text documents into smaller, manageable chunks suitable for embedding. Currently implements fixed-size chunking with overlap using `langchain_text_splitters`.

*   **`IngestionService` (`ingestion_service.py`)**: Orchestrates the entire document ingestion pipeline. It uses the `CollectionManager` to identify the target collection, the `ChunkingService` to process text, the `EmbeddingService` to generate embeddings, and the `VectorDBClient` to store the processed chunks, embeddings, and their metadata into ChromaDB.

*   **`SearchService` (`search_service.py`)**: Provides the semantic search functionality. It takes a user query and a session ID, generates a query embedding, and then queries the appropriate ChromaDB collection to find and return the most relevant document chunks, along with similarity scores.

### Configuration

The primary configuration for ChromaDB is its persistence path:

*   **`CHROMA_DB_PATH`**: Set this environment variable (e.g., in your `.env` file) to specify the directory where ChromaDB should store its data. If not set, it defaults to `data/chroma_db` relative to the project root (as defined in `backend/app/config.py`).

    Example `.env` entry:
    ```
    CHROMA_DB_PATH=./my_chroma_data/
    ```

### Basic Usage Examples

Below are conceptual examples of how these services might be used. (Note: These are illustrative and might require an async context or specific initialization steps not shown).

**1. Initializing Services (Conceptual)**

```python
# main.py or an initialization script
from backend.app.config import get_settings
from backend.app.services.vector_db_client import VectorDBClient
from backend.app.services.collection_manager import CollectionManager
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.ingestion_service import IngestionService
from backend.app.services.search_service import SearchService

settings = get_settings()

# Initialize core components
vector_db = VectorDBClient(settings=settings)
embedding_service = EmbeddingService() # Default model
collection_manager = CollectionManager(vector_db_client=vector_db)

# Initialize services that depend on the above
ingestion_service = IngestionService(
    vector_db_client=vector_db,
    collection_manager=collection_manager,
    embedding_service=embedding_service
)
search_service = SearchService(
    vector_db_client=vector_db,
    collection_manager=collection_manager,
    embedding_service=embedding_service
)

print("Services initialized.")
```

**2. Creating a Research Collection**

```python
# Assume collection_manager is initialized

session_id = "unique_session_abc123"
research_area = "Quantum Computing"
research_topic = "Entanglement Algorithms"

collection = collection_manager.create_research_collection(
    session_id=session_id,
    research_area=research_area,
    research_topic=research_topic
)

if collection:
    print(f"Collection '{collection.name}' created/accessed successfully.")
else:
    print(f"Failed to create/access collection for session '{session_id}'.")
```

**3. Ingesting a Document**

```python
# Assume ingestion_service and collection are set up

document_text = "This is the full text of a research paper about quantum entanglement..."
document_id = "paper_001"

# Ensure the collection for this session_id exists first (as shown in example 2)
success = ingestion_service.ingest_document(
    session_id=session_id, # Same session_id as collection creation
    document_id=document_id,
    document_text=document_text,
    document_metadata={"source": "arxiv_v1", "year": 2023}
)

if success:
    print(f"Document '{document_id}' ingested successfully into session '{session_id}'.")
else:
    print(f"Failed to ingest document '{document_id}'.")
```

**4. Performing a Semantic Search**

```python
# Assume search_service is initialized and documents have been ingested for the session_id

query = "What are the latest developments in quantum entanglement algorithms?"

# This is an async function
async def run_search():
    results = await search_service.semantic_search(
        session_id=session_id, # Same session_id used for ingestion
        query_text=query,
        n_results=5
    )

    if results:
        print(f"Found {len(results)} search results for query: '{query}'")
        for i, res in enumerate(results):
            print(f"  {i+1}. ID: {res['id']}, Score: {res['score']:.4f}")
            print(f"     Text: {res['text'][:100]}...")
            print(f"     Metadata: {res['metadata']}")
    else:
        print(f"No results found for query: '{query}'")

# Example of running the async search (in a real app, use an event loop manager)
# import asyncio
# asyncio.run(run_search())
```

This integration provides a robust foundation for semantic understanding and retrieval of textual data within the ResearchAIde application.

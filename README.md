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

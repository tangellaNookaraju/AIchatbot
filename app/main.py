import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environmental configurations
load_dotenv()

# Configure logging format and severity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")

from app.routes import chat
from app.vectorstore.vector_store import VectorStoreManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan management for startup/shutdown tasks.
    """
    logger.info("Starting up FastAPI application...")
    try:
        # Pre-initialize embedding service and Chroma vector database
        docs_path = os.getenv("DOCS_JSON_PATH", "docs.json")
        logger.info("Initializing knowledge base indexing...")
        VectorStoreManager.initialize_database(docs_path)
    except Exception as e:
        logger.error(f"Error during application startup initialization: {e}", exc_info=True)
    yield
    logger.info("Shutting down FastAPI application...")

# Initialize FastAPI App
app = FastAPI(
    title="GenAI RAG Support Assistant",
    description="A production-grade customer support chatbot utilizing retrieval-augmented generation.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for external access/frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production configurations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(chat.router)

# Register health check endpoint
@app.get("/health", status_code=200, tags=["System"])
def health_check():
    """
    Simple health verification endpoint for load balancers or monitoring.
    Reports if the Gemini API key is configured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    return {
        "status": "healthy",
        "llm_configured": bool(api_key)
    }

# Mount frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    logger.info(f"Serving static frontend files from: {frontend_dir}")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning(
        f"Static frontend directory '{frontend_dir}' was not found. "
        "The backend will run, but static pages will not be served."
    )

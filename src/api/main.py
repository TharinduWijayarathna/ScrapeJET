import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from loguru import logger
import uvicorn

# Import our modules
import sys
sys.path.append('/app')

from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, BedrockInterface, RAGSystem


# Pydantic models
class ScrapeRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 100
    max_workers: int = 10
    output_format: str = "both"  # "json", "markdown", "both"
    llm_provider: str = "openai"  # "openai" or "bedrock"
    llm_model: Optional[str] = None


class QueryRequest(BaseModel):
    question: str
    n_results: int = 5


class ScrapeResponse(BaseModel):
    message: str
    files: Dict[str, str]
    total_pages: int


class QueryResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]


# Global variables
rag_system = None
current_data = []


def initialize_rag_system(llm_provider: str = "openai", llm_model: Optional[str] = None):
    """Initialize the RAG system"""
    global rag_system
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Initialize LLM interface
    if llm_provider == "openai":
        llm_interface = OpenAIInterface(model=llm_model or "gpt-3.5-turbo")
    elif llm_provider == "bedrock":
        llm_interface = BedrockInterface(model_id=llm_model or "anthropic.claude-v2")
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    
    # Initialize RAG system
    rag_system = RAGSystem(vector_store, llm_interface)
    
    logger.info(f"RAG system initialized with {llm_provider}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI"""
    # Startup
    try:
        initialize_rag_system()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="Web Scraper with RAG",
    description="A comprehensive web scraper with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Web Scraper with RAG API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "/scrape",
            "query": "/query",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "rag_system_initialized": rag_system is not None}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape a website and store data for RAG"""
    global current_data, rag_system
    
    try:
        # Initialize RAG system if needed
        if rag_system is None:
            initialize_rag_system(request.llm_provider, request.llm_model)
        
        # Create scraper
        scraper = UniversalScraper(
            base_url=str(request.url),
            max_pages=request.max_pages,
            max_workers=request.max_workers
        )
        
        # Scrape the website
        logger.info(f"Starting to scrape {request.url}")
        data = await scraper.scrape_site()
        
        # Save data
        domain = str(request.url).replace("://", "_").replace("/", "_").replace(".", "_")
        filename = f"scraped_{domain}"
        
        saved_files = {}
        
        if request.output_format in ["json", "both"]:
            scraper.save_to_json(data, filename)
            saved_files['json'] = str(scraper.output_dir / f"{filename}.json")
        
        if request.output_format in ["markdown", "both"]:
            scraper.save_to_markdown(data, filename)
            saved_files['markdown'] = str(scraper.output_dir / f"{filename}.md")
        
        # Add to RAG system
        current_data = data
        rag_system.add_documents(data)
        
        return ScrapeResponse(
            message=f"Successfully scraped {len(data)} pages from {request.url}",
            files=saved_files,
            total_pages=len(data)
        )
        
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No data available. Please scrape a website first.")
    
    try:
        # Get answer from RAG system
        answer = rag_system.query(request.question, request.n_results)
        
        # Get relevant context
        context = rag_system.get_relevant_context(request.question, request.n_results)
        
        return QueryResponse(
            answer=answer,
            context=context
        )
        
    except Exception as e:
        logger.error(f"Error querying RAG system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/status")
async def get_data_status():
    """Get status of current data"""
    global current_data, rag_system
    
    return {
        "data_loaded": len(current_data) > 0,
        "total_pages": len(current_data),
        "rag_system_initialized": rag_system is not None
    }


@app.delete("/data/clear")
async def clear_data():
    """Clear all data and reset RAG system"""
    global current_data, rag_system
    
    try:
        if rag_system:
            rag_system.vector_store.clear()
        current_data = []
        
        return {"message": "Data cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/reinitialize")
async def reinitialize_rag(request: ScrapeRequest):
    """Reinitialize RAG system with different LLM provider"""
    global rag_system
    
    try:
        initialize_rag_system(request.llm_provider, request.llm_model)
        return {"message": f"RAG system reinitialized with {request.llm_provider}"}
        
    except Exception as e:
        logger.error(f"Error reinitializing RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

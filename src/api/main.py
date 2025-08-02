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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    site_name: Optional[str] = None  # Optional site-specific query


class ScrapeResponse(BaseModel):
    message: str
    files: Dict[str, str]
    total_pages: int


class QueryResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]
    site_name: Optional[str] = None


class SiteInfo(BaseModel):
    site_name: str
    total_chunks: int
    unique_chunks: int
    duplicate_chunks: int
    deduplication_ratio: float


class SitesResponse(BaseModel):
    sites: List[str]
    statistics: Dict[str, SiteInfo]


# Global variables
rag_system = None
current_data = []


def initialize_rag_system(llm_provider: str = "openai", llm_model: Optional[str] = None):
    """Initialize the RAG system"""
    global rag_system
    
    try:
        # Check if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found in environment variables")
            rag_system = None
            return
        
        logger.info(f"Initializing RAG system with {llm_provider}")
        
        # Initialize vector store
        vector_store = VectorStore()
        logger.info("Vector store initialized successfully")
        
        # Initialize LLM interface
        if llm_provider == "openai":
            llm_interface = OpenAIInterface(model=llm_model or "gpt-3.5-turbo")
        elif llm_provider == "bedrock":
            llm_interface = BedrockInterface(model_id=llm_model or "anthropic.claude-v2")
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        logger.info("LLM interface initialized successfully")
        
        # Initialize RAG system
        rag_system = RAGSystem(vector_store, llm_interface)
        logger.info(f"RAG system initialized successfully with {llm_provider}")
        
    except Exception as e:
        logger.error(f"Could not initialize LLM system: {e}")
        logger.info("Continuing without RAG functionality - scraping only")
        rag_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI"""
    # Startup
    try:
        # Don't initialize RAG system at startup - let it be initialized on first scrape
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
            # Check if initialization was successful
            if rag_system is None:
                logger.warning("RAG system initialization failed, continuing with scraping only")
        
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
        
        # Add to RAG system if available
        current_data = data
        if rag_system is not None:
            rag_system.add_documents(data)
        else:
            logger.info("RAG system not available - skipping document addition")
        
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
    """Query the RAG system, optionally for a specific site"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No data available. Please scrape a website first.")
    
    try:
        # Get answer from RAG system
        if request.site_name:
            # Site-specific query
            answer = rag_system.query_site_specific(request.question, request.site_name, request.n_results)
            context = rag_system.get_relevant_context(request.question, request.n_results, request.site_name)
        else:
            # Query across all sites
            answer = rag_system.query(request.question, request.n_results)
            context = rag_system.get_relevant_context(request.question, request.n_results)
        
        return QueryResponse(
            answer=answer,
            context=context,
            site_name=request.site_name
        )
        
    except Exception as e:
        logger.error(f"Error querying RAG system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sites", response_model=SitesResponse)
async def get_sites():
    """Get list of available sites and their statistics"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="RAG system not initialized. Please scrape a website first.")
    
    try:
        sites = rag_system.get_sites()
        statistics = rag_system.get_all_sites_stats()
        
        # Convert statistics to SiteInfo objects
        site_info = {}
        for site_name, stats in statistics.items():
            if 'error' not in stats:
                site_info[site_name] = SiteInfo(
                    site_name=site_name,
                    total_chunks=stats.get('total_chunks', 0),
                    unique_chunks=stats.get('unique_chunks', 0),
                    duplicate_chunks=stats.get('duplicate_chunks', 0),
                    deduplication_ratio=stats.get('deduplication_ratio', 0.0)
                )
        
        return SitesResponse(
            sites=sites,
            statistics=site_info
        )
        
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sites/{site_name}/stats")
async def get_site_stats(site_name: str):
    """Get statistics for a specific site"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="RAG system not initialized. Please scrape a website first.")
    
    try:
        stats = rag_system.get_site_stats(site_name)
        
        if 'error' in stats:
            raise HTTPException(status_code=404, detail=stats['error'])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sites/{site_name}")
async def clear_site(site_name: str):
    """Clear a specific site from the vector store"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="RAG system not initialized.")
    
    try:
        rag_system.clear_site(site_name)
        return {"message": f"Site '{site_name}' cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing site: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/site/{site_name}")
async def query_site_specific(site_name: str, request: QueryRequest):
    """Query a specific site"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No data available. Please scrape a website first.")
    
    try:
        # Override site_name from path parameter
        request.site_name = site_name
        
        # Get answer from RAG system for specific site
        answer = rag_system.query_site_specific(request.question, site_name, request.n_results)
        context = rag_system.get_relevant_context(request.question, request.n_results, site_name)
        
        return QueryResponse(
            answer=answer,
            context=context,
            site_name=site_name
        )
        
    except Exception as e:
        logger.error(f"Error querying site {site_name}: {e}")
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


@app.get("/data/optimization")
async def get_optimization_stats():
    """Get vector store optimization statistics"""
    try:
        if rag_system and rag_system.vector_store:
            stats = rag_system.vector_store.get_optimization_stats()
            return {
                "status": "success",
                "optimization_stats": stats,
                "message": f"Storage efficiency: {stats['storage_efficiency']}%, Deduplication ratio: {stats['deduplication_ratio']}%"
            }
        else:
            return {
                "status": "error",
                "message": "RAG system not available"
            }
    except Exception as e:
        logger.error(f"Error getting optimization stats: {e}")
        return {
            "status": "error",
            "message": f"Error retrieving optimization statistics: {str(e)}"
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

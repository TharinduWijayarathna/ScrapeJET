import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    url: str
    max_pages: int = 50
    max_workers: int = 5
    output_format: str = "json"


class QueryRequest(BaseModel):
    question: str
    n_results: int = 5
    site_name: Optional[str] = None  # Optional site-specific query


class ScrapeResponse(BaseModel):
    message: str
    files: Dict[str, str]
    total_pages: int
    optimization_stats: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]
    site_name: Optional[str] = None
    conversation_id: Optional[str] = None


class SitesResponse(BaseModel):
    sites: List[str]
    stats: Dict[str, Dict[str, Any]]


class ConversationResponse(BaseModel):
    history: List[Dict[str, str]]
    total_messages: int


class CacheResponse(BaseModel):
    cached_queries: int
    cache_size: int


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
    title="Web Scraper API",
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


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    global rag_system
    try:
        # Initialize RAG system on first use instead of startup
        logger.info("API startup complete - RAG system will be initialized on first scrape")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API shutting down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Web Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "POST /scrape",
            "query": "POST /query",
            "sites": "GET /sites",
            "health": "GET /health",
            "conversation": "GET /conversation",
            "clear_conversation": "DELETE /conversation",
            "cache_stats": "GET /cache/stats",
            "clear_cache": "DELETE /cache",
            "optimization_stats": "GET /optimization/stats"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "rag_system_initialized": rag_system is not None}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape a website and optionally add to RAG system with automatic optimization"""
    global rag_system
    
    try:
        # Initialize scraper
        scraper = UniversalScraper(
            base_url=request.url,
            max_pages=request.max_pages,
            max_workers=request.max_workers
        )
        
        # Scrape the website (synchronous method with optimization)
        data = scraper.scrape_site()
        
        # Get optimization statistics
        optimization_stats = scraper.get_optimization_stats()
        logger.info(f"Optimization stats: {optimization_stats}")
        
        # Save data to files
        saved_files = {}
        if data:
            # Generate filename based on URL
            domain = request.url.replace("://", "_").replace("/", "_").replace(".", "_")
            filename = f"scraped_{domain}"
            
            # Save as JSON
            scraper.save_to_json(data, filename)
            saved_files['json'] = str(scraper.output_dir / f"{filename}.json")
            
            # Save optimization stats
            stats_file = scraper.output_dir / f"{filename}_optimization_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(optimization_stats, f, indent=2)
            saved_files['optimization_stats'] = str(stats_file)
        
        # Initialize RAG system if not already done
        if rag_system is None:
            initialize_rag_system()
        
        # Add documents to RAG system if available
        if rag_system is not None and data:
            try:
                rag_system.add_documents(data)
                logger.info(f"Added {len(data)} documents to RAG system")
            except Exception as e:
                logger.error(f"Error adding documents to RAG system: {e}")
        
        response_data = {
            "message": f"Successfully scraped {len(data)} pages from {request.url} with {optimization_stats.get('optimization_ratio', 0):.1f}% optimization",
            "files": saved_files,
            "total_pages": len(data),
            "optimization_stats": optimization_stats
        }
        logger.info(f"Response data: {response_data}")
        
        # Return proper ScrapeResponse with optimization stats
        return ScrapeResponse(
            message=response_data["message"],
            files=response_data["files"],
            total_pages=response_data["total_pages"],
            optimization_stats=response_data["optimization_stats"]
        )
        
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system with enhanced features"""
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
        return SitesResponse(sites=[], stats={})
    
    try:
        sites = rag_system.get_sites()
        stats = rag_system.get_all_sites_stats()
        
        return SitesResponse(sites=sites, stats=stats)
        
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sites/{site_name}")
async def clear_site(site_name: str):
    """Clear all documents for a specific site"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No RAG system available.")
    
    try:
        rag_system.clear_site(site_name)
        return {"message": f"Cleared all documents for site: {site_name}"}
        
    except Exception as e:
        logger.error(f"Error clearing site {site_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/site/{site_name}")
async def query_site_specific(site_name: str, request: QueryRequest):
    """Query a specific site with enhanced features"""
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
    global rag_system
    
    if rag_system is None:
        return {"status": "no_rag_system", "message": "RAG system not initialized"}
    
    try:
        sites = rag_system.get_sites()
        stats = rag_system.get_all_sites_stats()
        
        return {
            "status": "available",
            "sites": sites,
            "stats": stats,
            "total_sites": len(sites)
        }
        
    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/data/optimization")
async def get_optimization_stats():
    """Get optimization statistics"""
    global rag_system
    
    if rag_system is None:
        return {"message": "No RAG system available"}
    
    try:
        stats = rag_system.get_all_sites_stats()
        
        # Calculate overall optimization metrics
        total_chunks = 0
        total_unique = 0
        
        for site_stats in stats.values():
            if 'total_chunks' in site_stats:
                total_chunks += site_stats['total_chunks']
            if 'unique_chunks' in site_stats:
                total_unique += site_stats['unique_chunks']
        
        overall_deduplication = round((total_chunks - total_unique) / max(total_chunks, 1) * 100, 2)
        
        return {
            "overall_stats": {
                "total_chunks": total_chunks,
                "unique_chunks": total_unique,
                "duplicate_chunks": total_chunks - total_unique,
                "deduplication_ratio": overall_deduplication
            },
            "site_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/optimization/stats")
async def get_scrape_optimization_stats():
    """Get optimization statistics from the last scrape"""
    global rag_system
    
    if rag_system is None:
        return {"message": "No RAG system available"}
    
    try:
        # This endpoint is primarily for the frontend to show optimization stats
        # from the last scrape, not the current optimization stats of the RAG system.
        # For that, use /data/optimization.
        # This endpoint is a placeholder to expose the optimization stats directly.
        # In a real scenario, you might need to store these stats in a global variable
        # or pass them from the scraper to the API.
        # For now, we'll return a placeholder or raise an error if no data is available.
        # A more robust solution would involve a global variable or a shared state.
        
        # Example: If you want to expose the last scrape's optimization stats
        # from the RAG system's state, you'd need to store it.
        # For now, we'll return a placeholder.
        return {"message": "Optimization stats from last scrape are not directly available in this endpoint. Use /data/optimization for current stats."}
        
    except Exception as e:
        logger.error(f"Error getting scrape optimization stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation", response_model=ConversationResponse)
async def get_conversation_history():
    """Get conversation history"""
    global rag_system
    
    if rag_system is None:
        return ConversationResponse(history=[], total_messages=0)
    
    try:
        history = rag_system.get_conversation_history()
        return ConversationResponse(
            history=history,
            total_messages=len(history)
        )
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversation")
async def clear_conversation_history():
    """Clear conversation history"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No RAG system available.")
    
    try:
        rag_system.clear_conversation_history()
        return {"message": "Conversation history cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/stats", response_model=CacheResponse)
async def get_cache_stats():
    """Get cache statistics"""
    global rag_system
    
    if rag_system is None:
        return CacheResponse(cached_queries=0, cache_size=0)
    
    try:
        cache = rag_system.query_cache
        return CacheResponse(
            cached_queries=len(cache),
            cache_size=len(cache)
        )
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cache")
async def clear_cache():
    """Clear query cache"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No RAG system available.")
    
    try:
        rag_system.query_cache.clear()
        return {"message": "Query cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/enhanced")
async def enhanced_query(request: QueryRequest):
    """Enhanced query with conversation context and better filtering"""
    global rag_system
    
    if rag_system is None:
        raise HTTPException(status_code=400, detail="No data available. Please scrape a website first.")
    
    try:
        # Get conversation history for context
        history = rag_system.get_conversation_history()
        
        # Get answer with enhanced features
        if request.site_name:
            answer = rag_system.query_site_specific(request.question, request.site_name, request.n_results)
            context = rag_system.get_relevant_context(request.question, request.n_results, request.site_name)
        else:
            answer = rag_system.query(request.question, request.n_results)
            context = rag_system.get_relevant_context(request.question, request.n_results)
        
        return {
            "answer": answer,
            "context": context,
            "site_name": request.site_name,
            "conversation_length": len(history),
            "cache_hit": len(rag_system.query_cache) > 0
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

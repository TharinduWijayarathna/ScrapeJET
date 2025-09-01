#!/usr/bin/env python3
"""
Simplified API for Web Scraper with RAG
"""

import os
import json
import uuid
import time
import asyncio
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
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, BedrockInterface, RAGSystem


# Pydantic models
class ScrapeRequest(BaseModel):
    url: str
    expected_pages: int = 100
    output_format: str = "json"


class QueryRequest(BaseModel):
    question: str
    n_results: int = 5
    site_name: Optional[str] = None


class SiteQueryRequest(BaseModel):
    question: str
    site_name: str
    n_results: int = 5
    page_type: Optional[str] = None  # Filter by page type (product, category, contact, etc.)


class ScrapeResponse(BaseModel):
    message: str
    job_id: str
    status: str = "started"


class ScrapeProgressResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    pages_scraped: int
    total_pages: int
    current_page: str
    time_elapsed: float
    message: str


class ScrapeResultResponse(BaseModel):
    message: str
    files: Dict[str, str]
    total_pages: int
    stats: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]
    site_name: Optional[str] = None


class SitesResponse(BaseModel):
    sites: List[str]
    stats: Dict[str, Dict[str, Any]]


# Global variables
rag_system = None
current_data = []
scraping_jobs = {}  # Store active scraping jobs


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
            logger.error(f"Unsupported LLM provider: {llm_provider}")
            rag_system = None
            return

        # Initialize RAG system
        rag_system = RAGSystem(vector_store, llm_interface)
        logger.info("RAG system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        rag_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Scraper API...")
    initialize_rag_system()
    yield
    # Shutdown
    logger.info("Shutting down Scraper API...")


# Create FastAPI app
app = FastAPI(
    title="Scraper API",
    description="Advanced Web Scraper with RAG capabilities",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "rag_system": rag_system is not None}


async def run_scraping_job(job_id: str, url: str, expected_pages: int, output_format: str):
    """Background task to run scraping job"""
    try:
        # Initialize job status
        scraping_jobs[job_id] = {
            "status": "running",
            "progress": 0.0,
            "pages_scraped": 0,
            "total_pages": expected_pages,
            "current_page": "Initializing...",
            "start_time": time.time(),
            "message": "Starting scraper...",
            "data": [],
            "files": {},
            "stats": {}
        }

        logger.info(f"Starting scraping job {job_id} for {url}")

        # Progress callback function
        def update_progress(progress_data):
            scraping_jobs[job_id].update({
                "progress": progress_data["progress"],
                "pages_scraped": progress_data["pages_scraped"],
                "current_page": progress_data["current_page"],
                "message": progress_data["message"]
            })

        # Initialize scraper with expected pages and progress callback
        scraper = UniversalScraper(base_url=url, expected_pages=expected_pages, progress_callback=update_progress)
        
        # Update job status
        scraping_jobs[job_id]["message"] = "Scraper initialized, starting to scrape..."

        # Scrape the site
        data = scraper.scrape_site()
        
        # Update job status with final data
        scraping_jobs[job_id]["pages_scraped"] = len(data)
        scraping_jobs[job_id]["total_pages"] = expected_pages
        scraping_jobs[job_id]["progress"] = 100.0
        scraping_jobs[job_id]["current_page"] = "Completed"
        scraping_jobs[job_id]["message"] = f"Successfully scraped {len(data)} pages from {url}"
        scraping_jobs[job_id]["data"] = data

        # Save data
        saved_files = scraper.scrape_and_save(output_format)
        scraping_jobs[job_id]["files"] = saved_files

        # Get stats
        stats = scraper.get_optimization_stats()
        scraping_jobs[job_id]["stats"] = stats

        # Add to RAG system if available
        if rag_system and data:
            scraping_jobs[job_id]["message"] = "Adding data to RAG system..."
            try:
                # Check if add_documents is async
                if hasattr(rag_system, 'add_documents') and asyncio.iscoroutinefunction(rag_system.add_documents):
                    await rag_system.add_documents(data)
                else:
                    rag_system.add_documents(data)
            except Exception as e:
                logger.error(f"Error adding documents to RAG: {e}")
                # Continue even if RAG fails

        # Update global data
        global current_data
        current_data.extend(data)

        # Mark job as completed
        scraping_jobs[job_id]["status"] = "completed"
        scraping_jobs[job_id]["message"] = f"Successfully scraped {len(data)} pages from {url}"

        logger.info(f"Scraping job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error in scraping job {job_id}: {e}")
        scraping_jobs[job_id]["status"] = "failed"
        scraping_jobs[job_id]["message"] = f"Scraping failed: {str(e)}"


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start scraping a website"""
    try:
        logger.info(f"Starting scrape of {request.url} with {request.expected_pages} expected pages")

        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Add background task
        background_tasks.add_task(
            run_scraping_job, 
            job_id, 
            request.url, 
            request.expected_pages, 
            request.output_format
        )

        return ScrapeResponse(
            message=f"Scraping job started for {request.url}",
            job_id=job_id,
            status="started"
        )

    except Exception as e:
        logger.error(f"Error starting scrape for {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")


@app.get("/scrape/{job_id}/progress", response_model=ScrapeProgressResponse)
async def get_scrape_progress(job_id: str):
    """Get real-time progress of a scraping job"""
    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = scraping_jobs[job_id]
    time_elapsed = time.time() - job.get("start_time", time.time())
    
    return ScrapeProgressResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        pages_scraped=job["pages_scraped"],
        total_pages=job.get("total_pages", job["pages_scraped"]),
        current_page=job["current_page"],
        time_elapsed=time_elapsed,
        message=job["message"]
    )


@app.get("/scrape/{job_id}/result", response_model=ScrapeResultResponse)
async def get_scrape_result(job_id: str):
    """Get the final result of a completed scraping job"""
    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = scraping_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed. Status: {job['status']}")
    
    return ScrapeResultResponse(
        message=job["message"],
        files=job["files"],
        total_pages=job["pages_scraped"],
        stats=job["stats"]
    )


@app.delete("/scrape/{job_id}")
async def cancel_scrape_job(job_id: str):
    """Cancel a running scraping job"""
    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = scraping_jobs[job_id]
    if job["status"] == "running":
        job["status"] = "cancelled"
        job["message"] = "Job cancelled by user"
        return {"message": "Job cancelled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Job is not running")


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query scraped data using RAG"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        # Query the RAG system
        if request.site_name:
            # Site-specific query
            answer = rag_system.query_site_specific(
                request.question,
                request.site_name,
                n_results=request.n_results
            )
            context = rag_system.get_relevant_context(request.question, request.n_results, request.site_name)
        else:
            # General query across all sites
            answer = rag_system.query(
                request.question,
                n_results=request.n_results
            )
            context = rag_system.get_relevant_context(request.question, request.n_results)

        return QueryResponse(
            answer=answer,
            context=context,
            site_name=request.site_name
        )

    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/sites", response_model=SitesResponse)
async def get_sites():
    """Get list of available sites and their statistics"""
    if not rag_system:
        return SitesResponse(sites=[], stats={})

    try:
        sites = rag_system.get_sites()
        stats = {}

        for site in sites:
            site_stats = rag_system.get_site_stats(site)
            stats[site] = site_stats

        return SitesResponse(sites=sites, stats=stats)

    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sites: {str(e)}")


@app.delete("/sites/{site_name}")
async def clear_site(site_name: str):
    """Clear data for a specific site"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        rag_system.clear_site(site_name)
        return {"message": f"Cleared data for site: {site_name}"}

    except Exception as e:
        logger.error(f"Error clearing site {site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear site: {str(e)}")


@app.post("/ask/site/{site_name}")
async def ask_site_specific(request: SiteQueryRequest):
    """Ask questions about a specific site with advanced filtering"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        # Query the RAG system for specific site with filters
        answer = rag_system.query_site_specific(
            question=request.question,
            site_name=request.site_name,
            n_results=request.n_results
        )
        context = rag_system.get_relevant_context(request.question, request.n_results, request.site_name)

        return QueryResponse(
            answer=answer,
            context=context,
            site_name=request.site_name
        )

    except Exception as e:
        logger.error(f"Error querying site {request.site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/analytics")
async def get_analytics():
    """Get system analytics and statistics"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        sites = rag_system.get_sites()
        total_sites = len(sites)
        total_pages = 0
        total_products = 0
        total_chunks = 0

        for site in sites:
            site_stats = rag_system.get_site_stats(site)
            total_pages += site_stats.get('total_pages', 0)
            total_chunks += site_stats.get('total_chunks', 0)
            # Estimate products (this is a rough estimate)
            total_products += site_stats.get('total_pages', 0) // 2

        return {
            "total_sites": total_sites,
            "total_pages": total_pages,
            "total_products": total_products,
            "total_chunks": total_chunks,
            "recent_activity": [
                {
                    "type": "scrape",
                    "message": f"Scraped {total_sites} sites",
                    "timestamp": time.time()
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@app.get("/sites/{site_name}/info")
async def get_site_info(site_name: str):
    """Get detailed information about a specific site"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        site_stats = rag_system.get_site_stats(site_name)
        site_info = {
            "name": site_name,
            "total_pages": site_stats.get('total_pages', 0),
            "total_chunks": site_stats.get('total_chunks', 0),
            "last_updated": time.time(),
            "status": "active",
            "url": f"https://{site_name}" if not site_name.startswith('http') else site_name
        }
        
        return {
            "site_name": site_name,
            "info": site_info
        }

    except Exception as e:
        logger.error(f"Error getting site info for {site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get site info: {str(e)}")


@app.get("/sites/{site_name}/pages")
async def get_site_pages(site_name: str, page_type: Optional[str] = None):
    """Get pages from a specific site with optional filtering"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        pages = rag_system.get_site_pages(site_name, page_type=page_type)
        return {
            "site_name": site_name,
            "page_type": page_type,
            "pages": pages
        }

    except Exception as e:
        logger.error(f"Error getting pages for site {site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pages: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

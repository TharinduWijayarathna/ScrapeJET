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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from loguru import logger
import uvicorn
from dotenv import load_dotenv
from celery.result import AsyncResult
import redis

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
from src.celery_app import celery_app
from src.tasks import scrape_website_task, scrape_business_task, query_business_insights


# Pydantic models
class ScrapeRequest(BaseModel):
    url: str
    expected_pages: int = 100
    output_format: str = "json"
    priority: int = 5  # Task priority (0-9, higher is more priority)


class BusinessScrapeRequest(BaseModel):
    url: str
    pages_to_scrape: Optional[List[str]] = None
    priority: int = 5


class BusinessInsightRequest(BaseModel):
    site_name: str
    questions: List[str] = [
        "What does this company do?",
        "What are their main products or services?", 
        "How can I contact them?",
        "Where are they located?",
        "What is their company mission or values?"
    ]


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

# Redis connection for job status caching
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None


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
    """Health check endpoint with system status"""
    
    # Check Celery worker status
    celery_status = "unknown"
    active_workers = 0
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            active_workers = len(stats)
            celery_status = "healthy"
        else:
            celery_status = "no_workers"
    except Exception as e:
        celery_status = f"error: {str(e)}"
    
    # Check Redis status
    redis_status = "healthy" if redis_client else "unavailable"
    if redis_client:
        try:
            redis_client.ping()
        except:
            redis_status = "connection_failed"
    
    return {
        "status": "healthy",
        "rag_system": rag_system is not None,
        "celery_workers": celery_status,
        "active_workers": active_workers,
        "redis": redis_status,
        "queue_system": "celery+redis"
    }


def get_task_progress(task_id: str) -> Dict[str, Any]:
    """Get task progress from Celery result backend"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                "status": "pending",
                "progress": 0.0,
                "pages_scraped": 0,
                "total_pages": 0,
                "current_page": "Waiting to start...",
                "message": "Task is waiting in queue"
            }
        elif result.state == 'PROGRESS':
            return result.info
        elif result.state == 'SUCCESS':
            return {
                "status": "completed",
                "progress": 100.0,
                "result": result.result
            }
        elif result.state == 'FAILURE':
            return {
                "status": "failed",
                "progress": 0.0,
                "error": str(result.info)
            }
        else:
            return {
                "status": result.state.lower(),
                "progress": 0.0,
                "message": f"Task state: {result.state}"
            }
    except Exception as e:
        logger.error(f"Error getting task progress: {e}")
        return {
            "status": "error",
            "progress": 0.0,
            "error": str(e)
        }


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest):
    """Start scraping a website using Celery"""
    try:
        logger.info(f"Starting scrape of {request.url} with {request.expected_pages} expected pages")

        # Start Celery task
        task = scrape_website_task.apply_async(
            args=[request.url, request.expected_pages, request.output_format],
            priority=request.priority,
            queue="scraping"
        )

        return ScrapeResponse(
            message=f"Scraping job started for {request.url}",
            job_id=task.id,
            status="started"
        )

    except Exception as e:
        logger.error(f"Error starting scrape for {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")


@app.get("/scrape/{job_id}/progress", response_model=ScrapeProgressResponse)
async def get_scrape_progress(job_id: str):
    """Get real-time progress of a scraping job"""
    try:
        progress_data = get_task_progress(job_id)
        
        if progress_data["status"] == "error":
            raise HTTPException(status_code=404, detail="Job not found or error occurred")
        
        # Calculate time elapsed
        time_elapsed = 0.0
        if "start_time" in progress_data:
            time_elapsed = time.time() - progress_data["start_time"]
        
        return ScrapeProgressResponse(
            job_id=job_id,
            status=progress_data.get("status", "unknown"),
            progress=progress_data.get("progress", 0.0),
            pages_scraped=progress_data.get("pages_scraped", 0),
            total_pages=progress_data.get("total_pages", 0),
            current_page=progress_data.get("current_page", "Unknown"),
            time_elapsed=time_elapsed,
            message=progress_data.get("message", "No status message")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job progress: {str(e)}")


@app.get("/scrape/{job_id}/result", response_model=ScrapeResultResponse)
async def get_scrape_result(job_id: str):
    """Get the final result of a completed scraping job"""
    try:
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            raise HTTPException(status_code=400, detail="Job is still pending")
        elif result.state == 'PROGRESS':
            raise HTTPException(status_code=400, detail="Job is still in progress")
        elif result.state == 'FAILURE':
            raise HTTPException(status_code=500, detail=f"Job failed: {result.info}")
        elif result.state == 'SUCCESS':
            job_result = result.result
            return ScrapeResultResponse(
                message=job_result.get("message", "Job completed"),
                files=job_result.get("files", {}),
                total_pages=job_result.get("pages_scraped", 0),
                stats=job_result.get("stats", {})
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job state: {result.state}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting result for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job result: {str(e)}")


@app.delete("/scrape/{job_id}")
async def cancel_scrape_job(job_id: str):
    """Cancel a running scraping job"""
    try:
        # Revoke the Celery task
        celery_app.control.revoke(job_id, terminate=True)
        
        # Check if task was successfully revoked
        result = AsyncResult(job_id, app=celery_app)
        if result.state in ['REVOKED', 'FAILURE']:
            return {"message": "Job cancelled successfully", "job_id": job_id}
        else:
            return {"message": "Job cancellation requested", "job_id": job_id, "note": "Task may still be running"}
            
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@app.post("/scrape/business", response_model=ScrapeResponse)
async def scrape_business_pages(request: BusinessScrapeRequest):
    """Scrape business-specific pages (about, contact, terms, etc.)"""
    try:
        logger.info(f"Starting business scrape of {request.url}")

        # Start Celery task for business scraping
        task = scrape_business_task.apply_async(
            args=[request.url, request.pages_to_scrape],
            priority=request.priority,
            queue="business"
        )

        return ScrapeResponse(
            message=f"Business scraping job started for {request.url}",
            job_id=task.id,
            status="started"
        )

    except Exception as e:
        logger.error(f"Error starting business scrape for {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start business scraping: {str(e)}")


@app.post("/business/insights")
async def get_business_insights(request: BusinessInsightRequest):
    """Get business insights for a specific site using RAG"""
    try:
        logger.info(f"Getting business insights for {request.site_name}")

        # Start Celery task for business insights
        task = query_business_insights.apply_async(
            args=[request.site_name, request.questions],
            queue="rag"
        )

        return {
            "message": f"Business insights query started for {request.site_name}",
            "task_id": task.id,
            "status": "started"
        }

    except Exception as e:
        logger.error(f"Error getting business insights for {request.site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get business insights: {str(e)}")


@app.get("/business/insights/{task_id}")
async def get_business_insights_result(task_id: str):
    """Get the result of a business insights query"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {"status": "pending", "message": "Query is waiting in queue"}
        elif result.state == 'PROGRESS':
            return {"status": "processing", "message": "Query is being processed"}
        elif result.state == 'FAILURE':
            raise HTTPException(status_code=500, detail=f"Query failed: {result.info}")
        elif result.state == 'SUCCESS':
            return {
                "status": "completed",
                "result": result.result
            }
        else:
            return {"status": result.state.lower(), "message": f"Query state: {result.state}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting business insights result for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights result: {str(e)}")


@app.get("/queue/status")
async def get_queue_status():
    """Get current queue status and worker information"""
    try:
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active_tasks = inspect.active() or {}
        
        # Get scheduled tasks
        scheduled_tasks = inspect.scheduled() or {}
        
        # Get queue lengths
        queue_lengths = {}
        try:
            if redis_client:
                for queue_name in ['default', 'scraping', 'business', 'rag']:
                    length = redis_client.llen(f"celery:{queue_name}")
                    queue_lengths[queue_name] = length
        except Exception as e:
            logger.warning(f"Could not get queue lengths: {e}")
        
        # Get worker stats
        worker_stats = inspect.stats() or {}
        
        return {
            "active_tasks": active_tasks,
            "scheduled_tasks": scheduled_tasks,
            "queue_lengths": queue_lengths,
            "worker_stats": worker_stats,
            "total_workers": len(worker_stats),
            "system_status": "healthy" if worker_stats else "no_workers"
        }
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


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

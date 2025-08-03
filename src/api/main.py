#!/usr/bin/env python3
"""
Simplified API for Web Scraper with RAG
"""

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
        logger.info("RAG system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")
        rag_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API server...")
    initialize_rag_system()
    yield
    # Shutdown
    logger.info("Shutting down API server...")


# Create FastAPI app
app = FastAPI(
    title="Web Scraper with RAG API",
    description="A simplified API for web scraping and RAG-based querying",
    version="2.0.0",
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
        "version": "2.0.0",
        "endpoints": {
            "scrape": "POST /scrape - Scrape a website",
            "query": "POST /query - Query scraped data with RAG",
            "sites": "GET /sites - List available sites",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "rag_system": rag_system is not None}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape a website"""
    try:
        logger.info(f"Starting scrape of {request.url}")
        
        # Initialize scraper with expected pages
        scraper = UniversalScraper(base_url=request.url, expected_pages=request.expected_pages)
        
        # Scrape the site
        data = scraper.scrape_site()
        
        # Save data
        saved_files = scraper.scrape_and_save(request.output_format)
        
        # Add to RAG system if available
        if rag_system and data:
            background_tasks.add_task(rag_system.add_documents, data)
        
        # Update global data
        global current_data
        current_data.extend(data)
        
        stats = scraper.get_optimization_stats()
        
        return ScrapeResponse(
            message=f"Successfully scraped {len(data)} pages from {request.url}",
            files=saved_files,
            total_pages=len(data),
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error scraping {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


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


@app.get("/sites/{site_name}/info")
async def get_site_info(site_name: str):
    """Get detailed information about a specific site"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        site_info = rag_system.get_site_detailed_info(site_name)
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

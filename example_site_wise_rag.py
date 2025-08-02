#!/usr/bin/env python3
"""
Example script demonstrating site-wise RAG functionality
"""

import asyncio
from loguru import logger
from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, RAGSystem


async def demo_site_wise_rag():
    """Demonstrate site-wise RAG functionality"""
    
    # Example URLs to scrape
    urls = [
        "https://example.com",
        "https://demo.testfire.net",
        "https://httpbin.org"
    ]
    
    logger.info("Starting site-wise RAG demonstration...")
    
    # Initialize RAG system
    vector_store = VectorStore()
    llm_interface = OpenAIInterface()  # Make sure OPENAI_API_KEY is set
    rag_system = RAGSystem(vector_store, llm_interface)
    
    # Scrape multiple sites
    for url in urls:
        try:
            logger.info(f"Scraping {url}...")
            scraper = UniversalScraper(base_url=url, max_pages=5, max_workers=3)
            data = await scraper.scrape_site()
            
            if data:
                # Add documents (will be automatically organized by site)
                rag_system.add_documents(data)
                logger.info(f"Added {len(data)} pages from {url}")
            else:
                logger.warning(f"No data scraped from {url}")
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
    
    # Show available sites
    sites = rag_system.get_sites()
    logger.info(f"Available sites: {sites}")
    
    # Show statistics
    stats = rag_system.get_all_sites_stats()
    logger.info("Site Statistics:")
    for site, stat in stats.items():
        if 'error' not in stat:
            logger.info(f"  {site}: {stat['total_chunks']} chunks, {stat['unique_chunks']} unique")
    
    # Demo queries
    queries = [
        "What is the main content of this website?",
        "Are there any contact information?",
        "What products or services are offered?"
    ]
    
    logger.info("\n=== Demo Queries ===")
    
    for query in queries:
        logger.info(f"\nQuery: {query}")
        
        # Query across all sites
        logger.info("--- Across all sites ---")
        answer_all = rag_system.query(query)
        print(f"Answer: {answer_all}")
        
        # Query specific sites
        for site in sites[:2]:  # Just demo first 2 sites
            logger.info(f"--- Site: {site} ---")
            answer_site = rag_system.query_site_specific(query, site)
            print(f"Answer: {answer_site}")


async def interactive_demo():
    """Interactive demo of site-wise RAG"""
    logger.info("Starting interactive demo...")
    
    # Initialize RAG system
    vector_store = VectorStore()
    llm_interface = OpenAIInterface()
    rag_system = RAGSystem(vector_store, llm_interface)
    
    # Check if we have any sites
    sites = rag_system.get_sites()
    if not sites:
        logger.info("No sites available. Please scrape some websites first.")
        return
    
    logger.info(f"Available sites: {sites}")
    
    # Interactive query session
    while True:
        try:
            question = input("\nEnter your question (or 'quit' to exit): ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if not question:
                continue
            
            # Ask user which site to query
            print(f"\nAvailable sites: {', '.join(sites)}")
            site_choice = input("Enter site name (or 'all' for all sites): ").strip()
            
            if site_choice.lower() == 'all':
                answer = rag_system.query(question)
                print(f"\nAnswer (all sites): {answer}")
            elif site_choice in sites:
                answer = rag_system.query_site_specific(question, site_choice)
                print(f"\nAnswer ({site_choice}): {answer}")
            else:
                print(f"Site '{site_choice}' not found")
                
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_demo())
    else:
        asyncio.run(demo_site_wise_rag()) 
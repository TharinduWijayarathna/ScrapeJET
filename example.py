#!/usr/bin/env python3
"""
Example usage of the Web Scraper with RAG
"""

import asyncio
import os
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, RAGSystem


async def example_scrape_and_query():
    """Example: Scrape a website and query the RAG system"""
    
    # Example URL (replace with your target)
    url = "https://httpbin.org"
    
    logger.info(f"Starting example with URL: {url}")
    
    try:
        # 1. Scrape the website
        logger.info("Step 1: Scraping website...")
        scraper = UniversalScraper(base_url=url, max_pages=2)
        data = await scraper.scrape_site()
        
        logger.info(f"Scraped {len(data)} pages")
        
        # Save data
        scraper.save_to_json(data, "example_scrape")
        scraper.save_to_markdown(data, "example_scrape")
        
        # 2. Setup RAG system
        logger.info("Step 2: Setting up RAG system...")
        
        # Check for OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("No OpenAI API key found. Skipping RAG setup.")
            logger.info("To use RAG, set OPENAI_API_KEY environment variable")
            return
        
        vector_store = VectorStore()
        llm_interface = OpenAIInterface()
        rag_system = RAGSystem(vector_store, llm_interface)
        
        # Add documents to RAG
        rag_system.add_documents(data)
        
        # 3. Query the RAG system
        logger.info("Step 3: Querying RAG system...")
        
        questions = [
            "What is this website about?",
            "What are the main features?",
            "What content is available?"
        ]
        
        for question in questions:
            logger.info(f"\nQuestion: {question}")
            answer = rag_system.query(question)
            logger.info(f"Answer: {answer}")
        
        logger.info("\n✅ Example completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


async def example_without_llm():
    """Example: Scrape without LLM (for testing)"""
    
    url = "https://httpbin.org"
    
    logger.info(f"Starting example without LLM: {url}")
    
    try:
        # Scrape website
        scraper = UniversalScraper(base_url=url, max_pages=1)
        data = await scraper.scrape_site()
        
        logger.info(f"Scraped {len(data)} pages")
        
        # Save data
        scraper.save_to_json(data, "example_no_llm")
        scraper.save_to_markdown(data, "example_no_llm")
        
        # Show some extracted data
        for i, page in enumerate(data[:2]):  # Show first 2 pages
            logger.info(f"\nPage {i+1}:")
            logger.info(f"  URL: {page.get('url', 'N/A')}")
            logger.info(f"  Title: {page.get('title', 'N/A')}")
            logger.info(f"  Links found: {len(page.get('links', []))}")
            logger.info(f"  Images found: {len(page.get('images', []))}")
            
            if page.get('contact_info'):
                logger.info(f"  Contact info: {page['contact_info']}")
        
        logger.info("\n✅ Example without LLM completed!")
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web Scraper Example")
    parser.add_argument("--no-llm", action="store_true", help="Run without LLM (no API key needed)")
    parser.add_argument("--url", default="https://httpbin.org", help="URL to scrape")
    
    args = parser.parse_args()
    
    if args.no_llm:
        asyncio.run(example_without_llm())
    else:
        asyncio.run(example_scrape_and_query())


if __name__ == "__main__":
    main() 
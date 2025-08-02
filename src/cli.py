#!/usr/bin/env python3
"""
Command-line interface for the Web Scraper with RAG
"""

import asyncio
import argparse
import json
from pathlib import Path
from typing import Optional
from loguru import logger

from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, BedrockInterface, RAGSystem


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


async def scrape_website(url: str, max_pages: int = 100, output_format: str = "both", max_workers: int = 10):
    """Scrape a website"""
    logger.info(f"Starting to scrape {url} with {max_workers} workers")
    
    scraper = UniversalScraper(base_url=url, max_pages=max_pages, max_workers=max_workers)
    data = await scraper.scrape_site()
    
    # Save data
    domain = url.replace("://", "_").replace("/", "_").replace(".", "_")
    filename = f"scraped_{domain}"
    
    saved_files = {}
    
    if output_format in ["json", "both"]:
        scraper.save_to_json(data, filename)
        saved_files['json'] = str(scraper.output_dir / f"{filename}.json")
    
    if output_format in ["markdown", "both"]:
        scraper.save_to_markdown(data, filename)
        saved_files['markdown'] = str(scraper.output_dir / f"{filename}.md")
    
    logger.info(f"Scraping completed. Processed {len(data)} pages.")
    logger.info(f"Files saved: {list(saved_files.values())}")
    
    return data, saved_files


async def setup_rag(data: list, llm_provider: str = "openai", llm_model: Optional[str] = None):
    """Setup RAG system with scraped data"""
    logger.info("Setting up RAG system...")
    
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
    
    # Add documents
    rag_system.add_documents(data)
    
    logger.info("RAG system setup completed")
    return rag_system


async def interactive_query(rag_system: RAGSystem):
    """Interactive query mode"""
    logger.info("Entering interactive query mode. Type 'quit' to exit.")
    
    while True:
        try:
            question = input("\nEnter your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if not question:
                continue
            
            logger.info("Processing query...")
            answer = rag_system.query(question)
            
            print(f"\nAnswer: {answer}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error processing query: {e}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Web Scraper with RAG")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum pages to scrape")
    parser.add_argument("--max-workers", type=int, default=10, help="Maximum number of worker threads for parallel scraping")
    parser.add_argument("--output-format", choices=["json", "markdown", "both"], default="both", help="Output format")
    parser.add_argument("--llm-provider", choices=["openai", "bedrock"], default="openai", help="LLM provider")
    parser.add_argument("--llm-model", help="LLM model name")
    parser.add_argument("--interactive", action="store_true", help="Start interactive query mode")
    parser.add_argument("--query", help="Single query to run")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    async def run():
        try:
            # Scrape website
            data, saved_files = await scrape_website(
                args.url, 
                args.max_pages, 
                args.output_format,
                args.max_workers
            )
            
            # Setup RAG if needed
            if args.interactive or args.query:
                rag_system = await setup_rag(data, args.llm_provider, args.llm_model)
                
                if args.interactive:
                    await interactive_query(rag_system)
                elif args.query:
                    logger.info(f"Processing query: {args.query}")
                    answer = rag_system.query(args.query)
                    print(f"\nAnswer: {answer}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return 1
        
        return 0
    
    exit_code = asyncio.run(run())
    exit(exit_code)


if __name__ == "__main__":
    main() 
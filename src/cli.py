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
    
    # Add documents (will be automatically organized by site)
    rag_system.add_documents(data)
    
    logger.info("RAG system setup completed")
    return rag_system


async def interactive_query(rag_system: RAGSystem):
    """Interactive query mode with site-wise support"""
    logger.info("Entering interactive query mode. Type 'quit' to exit.")
    logger.info("Available commands:")
    logger.info("  - 'sites' to list available sites")
    logger.info("  - 'stats' to show site statistics")
    logger.info("  - 'site <site_name>' to query a specific site")
    logger.info("  - 'all' to query across all sites")
    
    current_site = None
    
    while True:
        try:
            question = input("\nEnter your question (or command): ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if not question:
                continue
            
            # Handle commands
            if question.lower() == 'sites':
                sites = rag_system.get_sites()
                if sites:
                    logger.info(f"Available sites: {', '.join(sites)}")
                else:
                    logger.info("No sites available")
                continue
            
            elif question.lower() == 'stats':
                stats = rag_system.get_all_sites_stats()
                if stats:
                    logger.info("Site Statistics:")
                    for site, stat in stats.items():
                        if 'error' not in stat:
                            logger.info(f"  {site}: {stat['total_chunks']} chunks, {stat['unique_chunks']} unique")
                        else:
                            logger.info(f"  {site}: {stat['error']}")
                else:
                    logger.info("No sites available")
                continue
            
            elif question.lower().startswith('site '):
                site_name = question[5:].strip()
                if site_name in rag_system.get_sites():
                    current_site = site_name
                    logger.info(f"Now querying site: {site_name}")
                else:
                    logger.warning(f"Site '{site_name}' not found")
                continue
            
            elif question.lower() == 'all':
                current_site = None
                logger.info("Now querying across all sites")
                continue
            
            # Process query
            logger.info("Processing query...")
            if current_site:
                answer = rag_system.query_site_specific(question, current_site)
                logger.info(f"Querying site: {current_site}")
            else:
                answer = rag_system.query(question)
                logger.info("Querying across all sites")
            
            print(f"\nAnswer: {answer}")
            
        except KeyboardInterrupt:
            break


async def query_specific_site(rag_system: RAGSystem, question: str, site_name: str):
    """Query a specific site"""
    logger.info(f"Querying site: {site_name}")
    answer = rag_system.query_site_specific(question, site_name)
    print(f"\nAnswer: {answer}")


async def list_sites(rag_system: RAGSystem):
    """List available sites"""
    sites = rag_system.get_sites()
    if sites:
        logger.info(f"Available sites: {', '.join(sites)}")
        
        # Show statistics
        stats = rag_system.get_all_sites_stats()
        logger.info("\nSite Statistics:")
        for site, stat in stats.items():
            if 'error' not in stat:
                logger.info(f"  {site}: {stat['total_chunks']} chunks, {stat['unique_chunks']} unique")
            else:
                logger.info(f"  {site}: {stat['error']}")
    else:
        logger.info("No sites available")


async def clear_site(rag_system: RAGSystem, site_name: str):
    """Clear a specific site"""
    sites = rag_system.get_sites()
    if site_name in sites:
        rag_system.clear_site(site_name)
        logger.info(f"Cleared site: {site_name}")
    else:
        logger.warning(f"Site '{site_name}' not found")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Web Scraper with RAG")
    parser.add_argument("--url", help="URL to scrape")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum pages to scrape")
    parser.add_argument("--max-workers", type=int, default=10, help="Maximum workers for scraping")
    parser.add_argument("--output-format", choices=["json", "markdown", "both"], default="both", help="Output format")
    parser.add_argument("--llm-provider", choices=["openai", "bedrock"], default="openai", help="LLM provider")
    parser.add_argument("--llm-model", help="LLM model name")
    parser.add_argument("--query", help="Query to ask")
    parser.add_argument("--site", help="Specific site to query")
    parser.add_argument("--list-sites", action="store_true", help="List available sites")
    parser.add_argument("--clear-site", help="Clear a specific site")
    parser.add_argument("--interactive", action="store_true", help="Enter interactive mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    async def run():
        if args.list_sites:
            # Just list sites
            vector_store = VectorStore()
            if args.llm_provider == "openai":
                llm_interface = OpenAIInterface(model=args.llm_model or "gpt-3.5-turbo")
            elif args.llm_provider == "bedrock":
                llm_interface = BedrockInterface(model_id=args.llm_model or "anthropic.claude-v2")
            else:
                raise ValueError(f"Unsupported LLM provider: {args.llm_provider}")
            
            rag_system = RAGSystem(vector_store, llm_interface)
            await list_sites(rag_system)
            return
        
        if args.clear_site:
            # Clear specific site
            vector_store = VectorStore()
            if args.llm_provider == "openai":
                llm_interface = OpenAIInterface(model=args.llm_model or "gpt-3.5-turbo")
            elif args.llm_provider == "bedrock":
                llm_interface = BedrockInterface(model_id=args.llm_model or "anthropic.claude-v2")
            else:
                raise ValueError(f"Unsupported LLM provider: {args.llm_provider}")
            
            rag_system = RAGSystem(vector_store, llm_interface)
            await clear_site(rag_system, args.clear_site)
            return
        
        if args.query:
            # Query mode
            vector_store = VectorStore()
            if args.llm_provider == "openai":
                llm_interface = OpenAIInterface(model=args.llm_model or "gpt-3.5-turbo")
            elif args.llm_provider == "bedrock":
                llm_interface = BedrockInterface(model_id=args.llm_model or "anthropic.claude-v2")
            else:
                raise ValueError(f"Unsupported LLM provider: {args.llm_provider}")
            
            rag_system = RAGSystem(vector_store, llm_interface)
            
            if args.site:
                await query_specific_site(rag_system, args.query, args.site)
            else:
                answer = rag_system.query(args.query)
                print(f"\nAnswer: {answer}")
            return
        
        if args.interactive:
            # Interactive mode
            vector_store = VectorStore()
            if args.llm_provider == "openai":
                llm_interface = OpenAIInterface(model=args.llm_model or "gpt-3.5-turbo")
            elif args.llm_provider == "bedrock":
                llm_interface = BedrockInterface(model_id=args.llm_model or "anthropic.claude-v2")
            else:
                raise ValueError(f"Unsupported LLM provider: {args.llm_provider}")
            
            rag_system = RAGSystem(vector_store, llm_interface)
            await interactive_query(rag_system)
            return
        
        if args.url:
            # Scrape mode
            data, saved_files = await scrape_website(
                args.url, 
                args.max_pages, 
                args.output_format, 
                args.max_workers
            )
            
            # Setup RAG if data was scraped
            if data:
                rag_system = await setup_rag(data, args.llm_provider, args.llm_model)
                
                # Enter interactive mode after scraping
                await interactive_query(rag_system)
        else:
            parser.print_help()
    
    asyncio.run(run())


if __name__ == "__main__":
    main() 
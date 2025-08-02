#!/usr/bin/env python3
"""
Example: Using multithreaded web scraping for better performance
"""

import asyncio
import time
from loguru import logger
from src.scraper.universal_scraper import UniversalScraper


async def example_multithreaded_scraping():
    """Example of using multithreaded scraping"""
    
    # Example URLs to scrape
    urls = [
        "https://httpbin.org",
        "https://example.com",
        "https://jsonplaceholder.typicode.com"
    ]
    
    for url in urls:
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping: {url}")
        logger.info(f"{'='*60}")
        
        # Test with different worker counts
        worker_counts = [1, 5, 10]
        
        for workers in worker_counts:
            logger.info(f"\n--- Testing with {workers} workers ---")
            
            # Create scraper
            scraper = UniversalScraper(
                base_url=url,
                max_pages=5,  # Limit for demo
                max_workers=workers
            )
            
            # Measure performance
            start_time = time.time()
            data = await scraper.scrape_site()
            end_time = time.time()
            
            duration = end_time - start_time
            pages_scraped = len(data)
            
            logger.info(f"Results:")
            logger.info(f"  - Workers: {workers}")
            logger.info(f"  - Duration: {duration:.2f} seconds")
            logger.info(f"  - Pages scraped: {pages_scraped}")
            logger.info(f"  - Pages per second: {pages_scraped/duration:.2f}" if duration > 0 else "  - Pages per second: N/A")
            
            # Show some sample data
            if data:
                logger.info(f"  - Sample data from first page:")
                first_page = data[0]
                logger.info(f"    Title: {first_page.get('title', 'N/A')}")
                logger.info(f"    URL: {first_page.get('url', 'N/A')}")
                logger.info(f"    Content length: {len(first_page.get('content', ''))} characters")


async def example_parallel_sites():
    """Example of scraping multiple sites in parallel"""
    
    sites = [
        ("https://httpbin.org", "HTTP Bin"),
        ("https://example.com", "Example.com"),
        ("https://jsonplaceholder.typicode.com", "JSON Placeholder")
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info("PARALLEL SITE SCRAPING EXAMPLE")
    logger.info(f"{'='*60}")
    
    # Create scrapers for each site
    scrapers = []
    for url, name in sites:
        scraper = UniversalScraper(
            base_url=url,
            max_pages=3,
            max_workers=5
        )
        scrapers.append((scraper, name))
    
    # Scrape all sites in parallel
    start_time = time.time()
    
    tasks = []
    for scraper, name in scrapers:
        task = asyncio.create_task(scraper.scrape_site())
        tasks.append((task, name))
    
    # Wait for all to complete
    results = []
    for task, name in tasks:
        try:
            data = await task
            results.append((name, data))
            logger.info(f"✓ Completed scraping {name}: {len(data)} pages")
        except Exception as e:
            logger.error(f"✗ Error scraping {name}: {e}")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    logger.info(f"\nParallel scraping completed in {total_duration:.2f} seconds")
    logger.info(f"Total pages scraped: {sum(len(data) for _, data in results)}")
    
    # Show summary
    for name, data in results:
        logger.info(f"  {name}: {len(data)} pages")


def main():
    """Main function"""
    logger.info("Multithreaded Web Scraping Examples")
    logger.info("=" * 50)
    
    # Run examples
    asyncio.run(example_multithreaded_scraping())
    asyncio.run(example_parallel_sites())
    
    logger.info("\n" + "=" * 50)
    logger.info("Examples completed!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main() 
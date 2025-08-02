#!/usr/bin/env python3
"""
Test script to demonstrate multithreading performance improvement
"""

import asyncio
import time
from loguru import logger
from src.scraper.universal_scraper import UniversalScraper


async def test_scraping_performance(url: str, max_pages: int = 10):
    """Test scraping performance with different worker counts"""
    
    worker_counts = [1, 5, 10, 20]
    results = {}
    
    for workers in worker_counts:
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing with {workers} workers")
        logger.info(f"{'='*50}")
        
        # Create scraper with specific worker count
        scraper = UniversalScraper(
            base_url=url,
            max_pages=max_pages,
            max_workers=workers
        )
        
        # Measure time
        start_time = time.time()
        data = await scraper.scrape_site()
        end_time = time.time()
        
        duration = end_time - start_time
        pages_per_second = len(data) / duration if duration > 0 else 0
        
        results[workers] = {
            'duration': duration,
            'pages_scraped': len(data),
            'pages_per_second': pages_per_second
        }
        
        logger.info(f"Completed in {duration:.2f} seconds")
        logger.info(f"Pages scraped: {len(data)}")
        logger.info(f"Pages per second: {pages_per_second:.2f}")
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("PERFORMANCE SUMMARY")
    logger.info(f"{'='*50}")
    
    for workers, result in results.items():
        logger.info(f"Workers: {workers:2d} | Duration: {result['duration']:6.2f}s | Pages: {result['pages_scraped']:2d} | Rate: {result['pages_per_second']:5.2f} pages/s")
    
    # Calculate speedup
    if 1 in results and results[1]['duration'] > 0:
        baseline_duration = results[1]['duration']
        logger.info(f"\nSpeedup compared to single worker:")
        for workers, result in results.items():
            if workers > 1:
                speedup = baseline_duration / result['duration']
                logger.info(f"  {workers} workers: {speedup:.2f}x faster")


def main():
    """Main function"""
    # Test URL (use a simple site for testing)
    test_url = "https://httpbin.org"
    
    logger.info("Testing multithreading performance improvement")
    logger.info(f"Test URL: {test_url}")
    
    asyncio.run(test_scraping_performance(test_url, max_pages=5))


if __name__ == "__main__":
    main() 
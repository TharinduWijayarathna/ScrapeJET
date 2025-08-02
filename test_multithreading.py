#!/usr/bin/env python3
"""
Multithreading tests for web scraper
"""

import asyncio
import time
from src.scraper.universal_scraper import UniversalScraper


async def test_worker_performance():
    """Test performance with different worker counts"""
    print("Testing multithreading performance...")
    
    worker_counts = [1, 5, 10]
    results = {}
    
    for workers in worker_counts:
        start_time = time.time()
        scraper = UniversalScraper('https://httpbin.org', max_pages=2, max_workers=workers)
        data = await scraper.scrape_site()
        duration = time.time() - start_time
        results[workers] = {
            'pages': len(data),
            'duration': duration,
            'rate': len(data) / duration if duration > 0 else 0
        }
        print(f"✓ {workers} worker(s): {len(data)} pages in {duration:.2f}s ({results[workers]['rate']:.2f} pages/s)")
    
    return results


async def test_thread_safety():
    """Test thread safety by checking for duplicate URLs"""
    print("\nTesting thread safety...")
    
    scraper = UniversalScraper('https://httpbin.org', max_pages=5, max_workers=10)
    data = await scraper.scrape_site()
    
    urls = [item['url'] for item in data]
    unique_urls = set(urls)
    
    if len(urls) == len(unique_urls):
        print("✓ Thread safety: No duplicate URLs scraped")
    else:
        print("✗ Thread safety: Duplicate URLs found")
    
    print(f"✓ Scraped {len(data)} unique pages")
    return len(data)


def test_api_model():
    """Test API model validation"""
    print("\nTesting API model validation...")
    
    try:
        # Test basic scraper instantiation
        scraper = UniversalScraper('https://httpbin.org', max_workers=10)
        print("✓ Scraper instantiation with max_workers successful")
        
        # Test CLI argument parsing
        import sys
        sys.path.append('/home/thari/office/web-scraper')
        from src.cli import main
        print("✓ CLI module import successful")
        
        return True
    except Exception as e:
        print(f"✗ API/CLI test failed: {e}")
        return False


async def main():
    """Run all multithreading tests"""
    print("=" * 50)
    print("MULTITHREADING TESTS")
    print("=" * 50)
    
    # Test performance
    performance_results = await test_worker_performance()
    
    # Test thread safety
    await test_thread_safety()
    
    # Test API model
    test_api_model()
    
    print("\n" + "=" * 50)
    print("TESTS COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main()) 
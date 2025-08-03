#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/thari/office/web-scraper')

from src.scraper.universal_scraper import UniversalScraper

def test_scraper():
    print("Testing Super Scraper with advanced features...")
    
    # Set environment variables for advanced features
    os.environ.setdefault("USE_SELENIUM", "true")
    os.environ.setdefault("USE_PLAYWRIGHT", "true")
    os.environ.setdefault("SCROLL_PAGES", "true")
    os.environ.setdefault("SCREENSHOT_PAGES", "false")
    os.environ.setdefault("WAIT_FOR_JS", "5")
    
    # Test with expected pages parameter
    expected_pages = 20  # Set specific number of pages to scrape
    scraper = UniversalScraper(base_url='https://www.celltronics.lk', expected_pages=expected_pages)
    
    print(f"Starting super scrape with advanced configuration:")
    print(f"Max pages: {scraper.max_pages}")
    print(f"Max workers: {scraper.max_workers}")
    print(f"Timeout: {scraper.timeout}")
    print(f"Retry count: {scraper.retry_count}")
    print(f"Delay: {scraper.delay}")
    print(f"Use Selenium: {scraper.use_selenium}")
    print(f"Use Playwright: {scraper.use_playwright}")
    print(f"Scroll pages: {scraper.scroll_pages}")
    print(f"Screenshot pages: {scraper.screenshot_pages}")
    print(f"Wait for JS: {scraper.wait_for_js} seconds")
    
    try:
        data = scraper.scrape_site()
        print(f"Successfully scraped {len(data)} pages")
        
        # Show comprehensive stats
        stats = scraper.get_optimization_stats()
        print(f"Super scraping stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Save data
        saved_file = scraper.save_data()
        print(f"Data saved to: {saved_file}")
        
        # Show first few URLs if any
        if data:
            print(f"\nFirst page details:")
            print(f"  URL: {data[0].get('url', 'N/A')}")
            print(f"  Title: {data[0].get('title', 'N/A')}")
            print(f"  Page Type: {data[0].get('page_type', 'N/A')}")
            print(f"  Content Summary: {data[0].get('content_summary', 'N/A')}")
            print(f"  Key Topics: {data[0].get('key_topics', [])}")
            print(f"  Word Count: {data[0].get('word_count', 0)}")
            print(f"  Content length: {len(data[0].get('content', ''))}")
            print(f"  Links found: {len(data[0].get('links', []))}")
            print(f"  Images found: {len(data[0].get('images', []))}")
            print(f"  Forms found: {len(data[0].get('forms', []))}")
            print(f"  Scripts found: {len(data[0].get('scripts', []))}")
            print(f"  Styles found: {len(data[0].get('styles', []))}")
        
    except Exception as e:
        print(f"Error during super scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scraper() 
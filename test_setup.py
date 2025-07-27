#!/usr/bin/env python3
"""
Test script to verify the web scraper setup
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from src.scraper.universal_scraper import UniversalScraper
        from src.rag.vector_store import VectorStore
        from src.rag.llm_interface import OpenAIInterface, BedrockInterface, RAGSystem
        logger.info("✅ All imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False

def test_scraper_creation():
    """Test scraper creation"""
    try:
        scraper = UniversalScraper("https://httpbin.org")
        logger.info("✅ Scraper creation successful")
        return True
    except Exception as e:
        logger.error(f"❌ Scraper creation error: {e}")
        return False

def test_vector_store():
    """Test vector store creation"""
    try:
        vector_store = VectorStore()
        logger.info("✅ Vector store creation successful")
        return True
    except Exception as e:
        logger.error(f"❌ Vector store creation error: {e}")
        return False

async def test_simple_scrape():
    """Test simple scraping"""
    try:
        scraper = UniversalScraper("https://httpbin.org", max_pages=1)
        data = await scraper.scrape_site()
        logger.info(f"✅ Simple scrape successful, got {len(data)} pages")
        return True
    except Exception as e:
        logger.error(f"❌ Simple scrape error: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from config import settings
        logger.info("✅ Configuration loading successful")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration loading error: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("Starting setup tests...")
    
    tests = [
        ("Import Test", test_imports),
        ("Scraper Creation", test_scraper_creation),
        ("Vector Store", test_vector_store),
        ("Configuration", test_config),
        ("Simple Scrape", test_simple_scrape),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Setup is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 
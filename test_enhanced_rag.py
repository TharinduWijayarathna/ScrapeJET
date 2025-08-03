#!/usr/bin/env python3
"""
Test script for enhanced RAG functionality
Demonstrates conversation tracking, cache management, and improved precision
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change to your live URL if testing remotely

def test_enhanced_rag():
    """Test the enhanced RAG system with various scenarios"""
    
    print("🧪 Testing Enhanced RAG System")
    print("=" * 50)
    
    # Test 1: Scrape a website
    print("\n1️⃣ Scraping a website...")
    scrape_response = scrape_website("https://httpbin.org", max_pages=3, max_workers=2)
    if scrape_response:
        print(f"✅ Scraped successfully: {scrape_response['total_pages']} pages")
    else:
        print("❌ Scraping failed")
        return
    
    # Wait for processing
    time.sleep(2)
    
    # Test 2: Basic query
    print("\n2️⃣ Testing basic query...")
    query1 = "What information is available on this website?"
    response1 = query_rag(query1)
    if response1:
        print(f"✅ Query 1 response: {response1['answer'][:100]}...")
    
    # Test 3: Similar query (should use cache)
    print("\n3️⃣ Testing similar query (cache test)...")
    query2 = "What data is available on this website?"
    response2 = query_rag(query2)
    if response2:
        print(f"✅ Query 2 response: {response2['answer'][:100]}...")
    
    # Test 4: Different query (should provide new insights)
    print("\n4️⃣ Testing different query...")
    query3 = "What are the main features or services offered?"
    response3 = query_rag(query3)
    if response3:
        print(f"✅ Query 3 response: {response3['answer'][:100]}...")
    
    # Test 5: Enhanced query with conversation context
    print("\n5️⃣ Testing enhanced query...")
    enhanced_response = enhanced_query("Summarize the key information")
    if enhanced_response:
        print(f"✅ Enhanced query response: {enhanced_response['answer'][:100]}...")
        print(f"📊 Conversation length: {enhanced_response['conversation_length']}")
        print(f"💾 Cache hit: {enhanced_response['cache_hit']}")
    
    # Test 6: Check conversation history
    print("\n6️⃣ Checking conversation history...")
    history = get_conversation_history()
    if history:
        print(f"✅ Conversation history: {history['total_messages']} messages")
        for i, msg in enumerate(history['history'][-4:], 1):
            role = msg['role']
            content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            print(f"   {i}. {role}: {content}")
    
    # Test 7: Check cache statistics
    print("\n7️⃣ Checking cache statistics...")
    cache_stats = get_cache_stats()
    if cache_stats:
        print(f"✅ Cache stats: {cache_stats['cached_queries']} cached queries")
    
    # Test 8: Check optimization stats
    print("\n8️⃣ Checking optimization statistics...")
    opt_stats = get_optimization_stats()
    if opt_stats and 'overall_stats' in opt_stats:
        stats = opt_stats['overall_stats']
        print(f"✅ Optimization: {stats['deduplication_ratio']}% deduplication")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Unique chunks: {stats['unique_chunks']}")
    
    # Test 9: Test query diversity
    print("\n9️⃣ Testing query diversity...")
    diverse_queries = [
        "What are the contact details?",
        "What products or services are mentioned?",
        "What is the main purpose of this website?",
        "Are there any specific features highlighted?"
    ]
    
    for i, query in enumerate(diverse_queries, 1):
        print(f"   Query {i}: {query}")
        response = query_rag(query)
        if response:
            print(f"   Response: {response['answer'][:80]}...")
        time.sleep(1)
    
    # Test 10: Clear conversation and test fresh start
    print("\n🔟 Testing conversation clearing...")
    clear_conversation()
    print("✅ Conversation cleared")
    
    # Test fresh query
    fresh_response = query_rag("What is the main content of this website?")
    if fresh_response:
        print(f"✅ Fresh query response: {fresh_response['answer'][:100]}...")
    
    print("\n🎉 Enhanced RAG testing completed!")

def scrape_website(url: str, max_pages: int = 5, max_workers: int = 3) -> Dict[str, Any]:
    """Scrape a website"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/scrape",
            json={
                "url": url,
                "max_pages": max_pages,
                "max_workers": max_workers,
                "output_format": "json"
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return None

def query_rag(question: str, n_results: int = 5) -> Dict[str, Any]:
    """Query the RAG system"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/query",
            json={
                "question": question,
                "n_results": n_results
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Query error: {e}")
        return None

def enhanced_query(question: str, n_results: int = 5) -> Dict[str, Any]:
    """Enhanced query with conversation context"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/query/enhanced",
            json={
                "question": question,
                "n_results": n_results
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Enhanced query error: {e}")
        return None

def get_conversation_history() -> Dict[str, Any]:
    """Get conversation history"""
    try:
        response = requests.get(f"{API_BASE_URL}/conversation", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Conversation history error: {e}")
        return None

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/cache/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Cache stats error: {e}")
        return None

def get_optimization_stats() -> Dict[str, Any]:
    """Get optimization statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/data/optimization", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Optimization stats error: {e}")
        return None

def clear_conversation():
    """Clear conversation history"""
    try:
        response = requests.delete(f"{API_BASE_URL}/conversation", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Clear conversation error: {e}")
        return None

def test_live_api():
    """Test the live API endpoints"""
    print("🌐 Testing Live API Endpoints")
    print("=" * 50)
    
    # Test health check
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test root endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API info: {data['message']} v{data['version']}")
        else:
            print("❌ Root endpoint failed")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")

if __name__ == "__main__":
    # Test live API first
    test_live_api()
    
    # Test enhanced RAG functionality
    test_enhanced_rag() 
#!/usr/bin/env python3

import sys
import os
import json
sys.path.append('/home/thari/office/web-scraper')

def test_rag_with_existing_data():
    print("Testing RAG system with existing scraped data...")
    
    # Check if we have existing scraped data
    data_file = "data/raw/scraped_https_celltronics_lk_.json"
    
    if not os.path.exists(data_file):
        print(f"Data file {data_file} not found")
        return
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        print(f"Found {len(data)} scraped pages")
        
        # Show some sample data
        if data:
            print(f"First page URL: {data[0].get('url', 'N/A')}")
            print(f"First page title: {data[0].get('title', 'N/A')}")
            
            # Check if there are products
            if 'products' in data[0]:
                print(f"Number of products on first page: {len(data[0]['products'])}")
            
            # Check if there are links
            if 'links' in data[0]:
                print(f"Number of links on first page: {len(data[0]['links'])}")
        
        # Test RAG system
        try:
            from src.rag.vector_store import VectorStore
            from src.rag.llm_interface import OpenAIInterface, RAGSystem
            
            print("Initializing RAG system...")
            vector_store = VectorStore()
            llm_interface = OpenAIInterface()
            rag_system = RAGSystem(vector_store, llm_interface)
            
            print("Adding documents to RAG system...")
            rag_system.add_documents(data)
            
            print("Testing query...")
            response = rag_system.query("What products does Celltronics sell?", n_results=3)
            print(f"RAG Response: {response}")
            
        except Exception as e:
            print(f"Error with RAG system: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error reading data file: {e}")

if __name__ == "__main__":
    test_rag_with_existing_data() 
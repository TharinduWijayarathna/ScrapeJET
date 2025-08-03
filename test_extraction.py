#!/usr/bin/env python3
"""
Test script to debug product extraction
"""

import json
import re
from pathlib import Path

def test_extraction():
    # Load the raw data
    with open('data/raw/scraped_www_celltronics_lk_1754238595.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get the content from the first page
    content = data['pages'][0]['content']
    
    # Test the context extraction method
    print("Testing context extraction...")
    
    # Find all price occurrences with their context
    price_pattern = r'Rs\.\s*([\d,]+\.?\d*)'
    price_matches = list(re.finditer(price_pattern, content))
    
    print(f"Found {len(price_matches)} prices")
    
    # Test the first few prices
    for i, match in enumerate(price_matches[:5]):
        price = match.group(1)
        start_pos = max(0, match.start() - 300)
        end_pos = min(len(content), match.end() + 100)
        
        context = content[start_pos:end_pos]
        before_price = context[:match.start() - start_pos].strip()
        
        print(f"\nPrice {i+1}: Rs. {price}")
        print(f"Context: {context}")
        print(f"Before price: {before_price}")
        
        # Test product name extraction
        product_patterns = [
            r'([A-Za-z]+\s+[A-Za-z]+\s+[A-Za-z]+\s+\d+\s+[A-Za-z]+)',  # Samsung Galaxy S25 Plus
            r'([A-Za-z]+\s+[A-Za-z]+\s+\d+\s+[A-Za-z]+)',  # Apple iPhone 16 Pro
            r'([A-Za-z]+\s+[A-Za-z]+\s+[A-Za-z]+\s+\d+)',  # Samsung Galaxy S25 Plus
            r'([A-Za-z]+\s+[A-Za-z]+\s+\d+)',  # Apple iPhone 16
            r'([A-Za-z]+\s+[A-Za-z]+\s+[A-Za-z]+)',  # JBL Flip 6
            r'([A-Za-z]+\s+[A-Za-z]+)',  # Simple two-word names
        ]
        
        found_name = None
        for pattern in product_patterns:
            matches = re.findall(pattern, before_price)
            if matches:
                found_name = matches[-1].strip()
                print(f"Found product name: '{found_name}' with pattern '{pattern}'")
                break
        
        if not found_name:
            print("No product name found")

if __name__ == "__main__":
    test_extraction() 
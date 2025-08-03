#!/usr/bin/env python3
"""
Data Processor for Web Scraper - Cleans and structures raw scraped data
"""

import json
import re
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger


class DataProcessor:
    """Processes and structures raw scraped data"""
    
    def __init__(self):
        self.product_patterns = [
            # Pattern for products with specifications like "Samsung Galaxy S25 Plus 12GB RAM 256GB Rs. 294,000.00"
            r'([A-Za-z\s]+(?:\s+\d+[A-Za-z]*)?(?:\s+[A-Za-z]+)*)\s+\d+[A-Za-z]*\s+RAM\s+\d+[A-Za-z]*\s+Rs\.\s*([\d,]+\.?\d*)',
            # Pattern for products with just name and price like "JBL Flip 6 Original Bluetooth Speaker Rs. 48,900.00"
            r'([A-Za-z\s]+(?:\s+\d+[A-Za-z]*)?(?:\s+[A-Za-z]+)*)\s+Rs\.\s*([\d,]+\.?\d*)',
            # Pattern for products with simple specs like "Apple iPhone 16 128GB Rs. 369,900.00"
            r'([A-Za-z\s]+(?:\s+\d+[A-Za-z]*)?(?:\s+[A-Za-z]+)*)\s+\d+[A-Za-z]*\s+Rs\.\s*([\d,]+\.?\d*)',
            # More flexible pattern for any product name followed by price
            r'([A-Za-z\s]+(?:\s+\d+[A-Za-z]*)?(?:\s+[A-Za-z]+)*)\s+Rs\.\s*([\d,]+\.?\d*)',
        ]
        
        self.price_patterns = [
            r'Rs\.\s*([\d,]+\.?\d*)',
            r'Original price was:\s*Rs\.\s*([\d,]+\.?\d*)\.\s*Rs\.\s*([\d,]+\.?\d*)',
            r'Current price is:\s*Rs\.\s*([\d,]+\.?\d*)',
        ]
        
        self.discount_patterns = [
            r'-(\d+)%',
            r'(\d+)%\s+off',
        ]
        
        self.section_patterns = [
            r'LATEST MOBILE PHONES',
            r'UNLEASH JBL POWER',
            r'PAY WEEK DEALS',
            r'SMART WATCHES',
            r'HEADPHONES',
            r'POWERBANKS',
            r'EARBUDS',
        ]
        
        # Common product separators
        self.product_separators = [
            'Add to compare',
            'Quick view', 
            'Add to wishlist',
            'Select options',
            'Add to cart',
            'This product has multiple variants',
            'New',
            'Best Seller'
        ]
    
    def process_raw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw scraped data into structured format"""
        processed_data = {
            'base_url': raw_data.get('base_url', ''),
            'scrape_stats': raw_data.get('scrape_stats', {}),
            'processed_pages': [],
            'products': [],
            'categories': {},
            'processing_timestamp': time.time()
        }
        
        for page in raw_data.get('pages', []):
            processed_page = self._process_page(page)
            if processed_page:
                processed_data['processed_pages'].append(processed_page)
                
                # Extract products from page
                page_products = self._extract_products_from_content(page.get('content', ''))
                processed_data['products'].extend(page_products)
                
                # Extract categories
                page_categories = self._extract_categories_from_content(page.get('content', ''))
                for category, products in page_categories.items():
                    if category not in processed_data['categories']:
                        processed_data['categories'][category] = []
                    processed_data['categories'][category].extend(products)
        
        return processed_data
    
    def _process_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual page data"""
        return {
            'url': page.get('url', ''),
            'title': page.get('title', ''),
            'content_summary': self._generate_content_summary(page.get('content', '')),
            'products_count': len(self._extract_products_from_content(page.get('content', ''))),
            'categories_count': len(self._extract_categories_from_content(page.get('content', ''))),
            'metadata': page.get('metadata', {}),
            'timestamp': page.get('timestamp', 0)
        }
    
    def _extract_products_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract structured product information from content"""
        products = []
        
        # Split content into sections
        sections = self._split_into_sections(content)
        
        for section_name, section_content in sections.items():
            # Extract products from each section
            section_products = self._extract_products_from_section(section_content, section_name)
            products.extend(section_products)
        
        return products
    
    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """Split content into logical sections"""
        sections = {}
        
        # Find all section positions
        section_positions = []
        for pattern in self.section_patterns:
            if pattern.lower() in content.lower():
                pos = content.lower().find(pattern.lower())
                section_positions.append((pos, pattern))
        
        # Sort by position
        section_positions.sort()
        
        if not section_positions:
            # No sections found, put everything in General
            sections["General"] = content
            return sections
        
        # Extract sections
        for i, (pos, pattern) in enumerate(section_positions):
            if i == 0:
                # First section - content from start to this section
                if pos > 0:
                    sections["General"] = content[:pos].strip()
            
            # Get content for this section
            if i < len(section_positions) - 1:
                # Content from this section to next section
                next_pos = section_positions[i + 1][0]
                section_content = content[pos:next_pos].strip()
            else:
                # Last section - content from this section to end
                section_content = content[pos:].strip()
            
            sections[pattern] = section_content
        
        return sections
    
    def _extract_products_from_section(self, section_content: str, section_name: str) -> List[Dict[str, Any]]:
        """Extract products from a specific section"""
        products = []
        
        # First, try to find all price patterns in the content
        price_matches = re.findall(r'Rs\.\s*([\d,]+\.?\d*)', section_content)
        
        if not price_matches:
            return products
        
        # Split content by product separators
        separator_pattern = '|'.join(map(re.escape, self.product_separators))
        product_blocks = re.split(f'(?:{separator_pattern})', section_content)
        
        for block in product_blocks:
            if not block.strip():
                continue
            
            # Try to extract product from this block
            product = self._parse_product_block(block.strip(), section_name)
            if product and product['name']:
                products.append(product)
        
        # If we didn't find products by splitting, try a different approach
        if not products:
            products = self._extract_products_by_price_context(section_content, section_name)
        
        return products
    
    def _parse_product_block(self, block: str, category: str) -> Optional[Dict[str, Any]]:
        """Parse a product block into structured data"""
        product = {
            'name': '',
            'specifications': '',
            'original_price': '',
            'current_price': '',
            'discount_percentage': '',
            'category': category,
            'features': [],
            'availability': 'In Stock'
        }
        
        # Extract product name and specifications
        for pattern in self.product_patterns:
            matches = re.findall(pattern, block, re.IGNORECASE)
            if matches:
                if len(matches[0]) >= 2:
                    product['name'] = matches[0][0].strip()
                    product['current_price'] = matches[0][1].strip()
                break
        
        # Extract pricing information
        price_info = self._extract_pricing_info(block)
        if price_info:
            product.update(price_info)
        
        # Extract discount information
        discount_info = self._extract_discount_info(block)
        if discount_info:
            product['discount_percentage'] = discount_info
        
        # Extract features
        features = self._extract_features(block)
        if features:
            product['features'] = features
        
        # Only return if we have at least a name
        if product['name']:
            return product
        
        return None
    
    def _extract_pricing_info(self, block: str) -> Dict[str, str]:
        """Extract pricing information from product block"""
        pricing = {}
        
        # Look for original and current prices
        price_matches = re.findall(r'Original price was:\s*Rs\.\s*([\d,]+\.?\d*)\.\s*Rs\.\s*([\d,]+\.?\d*)', block)
        if price_matches:
            pricing['original_price'] = price_matches[0][0]
            pricing['current_price'] = price_matches[0][1]
        else:
            # Look for single price
            single_price = re.search(r'Rs\.\s*([\d,]+\.?\d*)', block)
            if single_price:
                pricing['current_price'] = single_price.group(1)
        
        return pricing
    
    def _extract_discount_info(self, block: str) -> str:
        """Extract discount percentage from product block"""
        for pattern in self.discount_patterns:
            match = re.search(pattern, block)
            if match:
                return match.group(1)
        return ""
    
    def _extract_features(self, block: str) -> List[str]:
        """Extract product features from block"""
        features = []
        
        # Common feature keywords
        feature_keywords = [
            'New', 'Best Seller', 'Popular', 'Featured', 'Limited Time',
            'Free Shipping', 'Warranty', 'Gift', 'Bundle', 'Deal'
        ]
        
        for keyword in feature_keywords:
            if keyword.lower() in block.lower():
                features.append(keyword)
        
        return features
    
    def _extract_products_by_price_context(self, content: str, category: str) -> List[Dict[str, Any]]:
        """Extract products by looking at text around price patterns"""
        products = []
        
        # Find all price occurrences with their context
        price_pattern = r'Rs\.\s*([\d,]+\.?\d*)'
        price_matches = list(re.finditer(price_pattern, content))
        
        for match in price_matches:
            price = match.group(1)
            start_pos = max(0, match.start() - 300)  # Look 300 chars before price
            end_pos = min(len(content), match.end() + 100)  # Look 100 chars after price
            
            context = content[start_pos:end_pos]
            
            # Try to extract product name from context
            product_name = self._extract_product_name_from_context(context, match.start() - start_pos)
            
            if product_name and len(product_name) > 5:  # Ensure we have a meaningful name
                product = {
                    'name': product_name,
                    'specifications': '',
                    'current_price': price,
                    'original_price': '',
                    'discount_percentage': '',
                    'category': category,
                    'features': [],
                    'availability': 'In Stock'
                }
                
                # Extract additional information
                discount_info = self._extract_discount_info(context)
                if discount_info:
                    product['discount_percentage'] = discount_info
                
                # Check for original price
                original_price_match = re.search(r'Original price was:\s*Rs\.\s*([\d,]+\.?\d*)', context)
                if original_price_match:
                    product['original_price'] = original_price_match.group(1)
                
                # Extract features
                features = self._extract_features(context)
                if features:
                    product['features'] = features
                
                # Only add if we don't already have this product
                if not any(p['name'] == product_name and p['current_price'] == price for p in products):
                    products.append(product)
        
        return products
    
    def _extract_product_name_from_context(self, context: str, price_position: int) -> str:
        """Extract product name from context around price"""
        # Look for text before the price that could be a product name
        before_price = context[:price_position].strip()
        
        # Clean up the context by removing common boilerplate
        before_price = re.sub(r'This product has multiple variants\. The options may be chosen on the product page', '', before_price)
        before_price = re.sub(r'Add to compare|Quick view|Add to wishlist|Select options', '', before_price)
        before_price = re.sub(r'\s+', ' ', before_price).strip()
        
        # Look for specifications pattern like "12GB RAM 256GB"
        spec_match = re.search(r'(\d+[A-Za-z]*\s+RAM\s+\d+[A-Za-z]*)', before_price)
        if spec_match:
            # Get text before the specification
            before_spec = before_price[:spec_match.start()].strip()
            if before_spec:
                # Take the last few words as the product name
                words = before_spec.split()
                if len(words) >= 2:
                    # Take last 2-4 words as product name
                    name = ' '.join(words[-3:]) if len(words) >= 3 else ' '.join(words)
                    if len(name) > 3:
                        return name
        
        # If no specifications found, try to extract just product name
        words = before_price.split()
        if len(words) >= 2:
            # Take last 2-3 words as product name
            name = ' '.join(words[-2:]) if len(words) >= 2 else ' '.join(words)
            if len(name) > 3:
                return name
        
        return ""
    
    def _extract_categories_from_content(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract products organized by categories"""
        categories = {}
        
        sections = self._split_into_sections(content)
        
        for section_name, section_content in sections.items():
            products = self._extract_products_from_section(section_content, section_name)
            if products:
                categories[section_name] = products
        
        return categories
    
    def _generate_content_summary(self, content: str) -> str:
        """Generate a summary of the content"""
        if not content:
            return ""
        
        # Count products
        product_count = len(re.findall(r'Rs\.\s*[\d,]+\.?\d*', content))
        
        # Count categories
        category_count = len([p for p in self.section_patterns if p.lower() in content.lower()])
        
        # Get price range
        prices = re.findall(r'Rs\.\s*([\d,]+\.?\d*)', content)
        if prices:
            # Convert to numbers for comparison
            price_numbers = [float(p.replace(',', '')) for p in prices if p.replace(',', '').replace('.', '').isdigit()]
            if price_numbers:
                min_price = min(price_numbers)
                max_price = max(price_numbers)
                price_range = f"Rs. {min_price:,.0f} - Rs. {max_price:,.0f}"
            else:
                price_range = "Price range not available"
        else:
            price_range = "No pricing information"
        
        return f"Found {product_count} products across {category_count} categories. Price range: {price_range}"
    
    def save_processed_data(self, processed_data: Dict[str, Any], output_path: str) -> str:
        """Save processed data to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processed data saved to {output_file}")
        return str(output_file)
    
    def create_readable_summary(self, processed_data: Dict[str, Any]) -> str:
        """Create a human-readable summary of the processed data"""
        summary = []
        summary.append("=" * 80)
        summary.append("PROCESSED WEB SCRAPING DATA SUMMARY")
        summary.append("=" * 80)
        summary.append("")
        
        # Basic info
        summary.append(f"Base URL: {processed_data.get('base_url', 'N/A')}")
        summary.append(f"Total Pages Processed: {len(processed_data.get('processed_pages', []))}")
        summary.append(f"Total Products Found: {len(processed_data.get('products', []))}")
        summary.append(f"Categories Found: {len(processed_data.get('categories', {}))}")
        summary.append("")
        
        # Categories summary
        summary.append("CATEGORIES:")
        summary.append("-" * 40)
        for category, products in processed_data.get('categories', {}).items():
            summary.append(f"{category}: {len(products)} products")
        summary.append("")
        
        # Sample products
        summary.append("SAMPLE PRODUCTS:")
        summary.append("-" * 40)
        products = processed_data.get('products', [])
        for i, product in enumerate(products[:10]):  # Show first 10 products
            summary.append(f"{i+1}. {product.get('name', 'N/A')}")
            if product.get('current_price'):
                summary.append(f"   Price: Rs. {product.get('current_price')}")
            if product.get('discount_percentage'):
                summary.append(f"   Discount: {product.get('discount_percentage')}%")
            summary.append("")
        
        if len(products) > 10:
            summary.append(f"... and {len(products) - 10} more products")
        
        summary.append("=" * 80)
        
        return '\n'.join(summary)


def process_raw_file(input_file: str, output_file: str = None) -> str:
    """Process a raw scraped file and create structured output"""
    processor = DataProcessor()
    
    # Read raw data
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Process the data
    processed_data = processor.process_raw_data(raw_data)
    
    # Generate output filename if not provided
    if not output_file:
        input_path = Path(input_file)
        output_file = input_path.parent / f"processed_{input_path.name}"
    
    # Save processed data
    processor.save_processed_data(processed_data, output_file)
    
    # Create and save readable summary
    summary = processor.create_readable_summary(processed_data)
    summary_file = str(Path(output_file).with_suffix('.summary.txt'))
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    logger.info(f"Processing complete!")
    logger.info(f"Processed data: {output_file}")
    logger.info(f"Summary: {summary_file}")
    
    return output_file


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_processor.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    process_raw_file(input_file, output_file) 
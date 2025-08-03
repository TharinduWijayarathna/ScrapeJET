import os
import json
import time
import queue
import hashlib
import threading
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
from loguru import logger

from .base_scraper import BaseScraper

class UniversalScraper(BaseScraper):
    """Universal scraper that can handle any website with multithreading support and automatic optimization"""
    
    def __init__(self, base_url: str, output_dir: str = "data/raw", max_pages: int = 100, max_workers: int = 10):
        super().__init__(base_url, output_dir)
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.pagination_patterns = [
            r'page=(\d+)', r'p=(\d+)', r'page/(\d+)', r'(\d+)/?$'
        ]
        self._lock = threading.Lock()
        self._visited = set()
        self._all_data = []
        self._url_queue = queue.Queue()
        self._failed_urls = set()
        self._retry_count = {}
        self.max_retries = 3
        self.retry_delay = 2
        
        # Optimization tracking
        self._content_hashes = set()
        self._product_hashes = set()
        self._contact_hashes = set()
        self._optimization_stats = {
            'total_pages_scraped': 0,
            'duplicate_pages_skipped': 0,
            'duplicate_content_removed': 0,
            'duplicate_products_removed': 0,
            'duplicate_contacts_removed': 0,
            'content_cleaned': 0,
            'optimization_ratio': 0.0
        }
    
    def detect_pagination(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Detect pagination links with enhanced patterns"""
        pagination_links = []
        
        # Look for pagination links
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(current_url, href)
            
            # Check if this looks like a pagination link
            for pattern in self.pagination_patterns:
                if self._is_valid_pagination_url(absolute_url, self.base_url):
                    pagination_links.append(absolute_url)
                    break
        
        return list(set(pagination_links))  # Remove duplicates
    
    def _is_valid_pagination_url(self, url: str, base_url: str) -> bool:
        """Check if URL is a valid pagination URL"""
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(base_url)
            
            # Must be same domain
            if parsed_url.netloc != parsed_base.netloc:
                return False
            
            # Check for pagination patterns in path or query
            path = parsed_url.path.lower()
            query = parsed_url.query.lower()
            
            pagination_indicators = ['page', 'p=', 'pagination', 'offset', 'start']
            
            for indicator in pagination_indicators:
                if indicator in path or indicator in query:
                    return True
            
            # Check for numeric patterns in URL
            import re
            if re.search(r'/\d+/?$', path):
                return True
                
            return False
        except:
            return False
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information with enhanced patterns"""
        contact_info = {
            'emails': [],
            'phones': [],
            'addresses': []
        }
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        import re
        text = soup.get_text()
        emails = re.findall(email_pattern, text)
        contact_info['emails'] = list(set(emails))
        
        # Extract phone numbers
        phone_pattern = r'(\+?[\d\s\-\(\)]{7,})'
        phones = re.findall(phone_pattern, text)
        contact_info['phones'] = list(set(phones))
        
        # Extract addresses (basic pattern)
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)'
        addresses = re.findall(address_pattern, text)
        contact_info['addresses'] = list(set(addresses))
        
        return contact_info
    
    def extract_products(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract product information with enhanced detection"""
        products = []
        
        # Look for common product selectors
        product_selectors = [
            '.product', '.item', '.card', '.product-item',
            '[class*="product"]', '[class*="item"]', '[class*="card"]'
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            for element in elements:
                product = self._extract_product_from_element(element)
                if product:
                    products.append(product)
        
        # Also look for structured data
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    product = self._extract_product_from_structured_data(data)
                    if product:
                        products.append(product)
            except:
                continue
        
        return products
    
    def _extract_product_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract product information from a DOM element"""
        product = {}
        
        # Extract name
        name_selectors = ['h1', 'h2', 'h3', '.title', '.name', '[class*="title"]', '[class*="name"]']
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                product['name'] = name_elem.get_text().strip()
                break
        
        # Extract price
        price_selectors = ['.price', '.cost', '[class*="price"]', '[class*="cost"]']
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                product['price'] = price_elem.get_text().strip()
                break
        
        # Extract description
        desc_selectors = ['.description', '.desc', '[class*="description"]', '[class*="desc"]']
        for selector in desc_selectors:
            desc_elem = element.select_one(selector)
            if desc_elem:
                product['description'] = desc_elem.get_text().strip()
                break
        
        # Extract image
        img_elem = element.find('img')
        if img_elem and img_elem.get('src'):
            product['image'] = img_elem['src']
        
        # Extract link
        link_elem = element.find('a')
        if link_elem and link_elem.get('href'):
            product['link'] = link_elem['href']
        
        return product if product else None
    
    def _extract_product_from_structured_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract product information from structured data"""
        product = {}
        
        if 'name' in data:
            product['name'] = data['name']
        if 'price' in data:
            product['price'] = data['price']
        if 'description' in data:
            product['description'] = data['description']
        if 'image' in data:
            product['image'] = data['image']
        if 'url' in data:
            product['link'] = data['url']
        
        return product if product else None
    
    def extract_general_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract general content with enhanced cleaning"""
        content = {}
        
        # Extract title
        title_elem = soup.find('title')
        if title_elem:
            content['title'] = title_elem.get_text().strip()
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content['description'] = meta_desc['content'].strip()
        
        # Extract main content
        main_content = self._extract_main_content(soup)
        if main_content:
            content['content'] = main_content
        
        # Extract links
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(url, href)
            if urlparse(absolute_url).netloc == urlparse(self.base_url).netloc:
                links.append(absolute_url)
        content['links'] = list(set(links))
        
        # Extract images
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            absolute_url = urljoin(url, src)
            images.append(absolute_url)
        content['images'] = list(set(images))
        
        return content
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content with intelligent cleaning"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content area
        main_selectors = [
            'main', '[role="main"]', '.main', '.content', '.post', '.article',
            '#main', '#content', '#post', '#article'
        ]
        
        main_content = None
        for selector in main_selectors:
            main_elem = soup.select_one(selector)
            if main_elem:
                main_content = main_elem.get_text()
                break
        
        if not main_content:
            # Fallback to body content
            main_content = soup.get_text()
        
        # Clean the content
        return self._clean_content(main_content)
    
    def _clean_content(self, text: str) -> str:
        """Clean and normalize content"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common boilerplate
        boilerplate_patterns = [
            r'cookie policy',
            r'privacy policy',
            r'terms of service',
            r'© \d{4}.*?\.',
            r'all rights reserved',
            r'powered by.*?\.',
        ]
        
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def parse_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse a single page with automatic optimization"""
        page_data = {
            'url': url,
            'timestamp': time.time()
        }
        
        # Extract general content
        general_content = self.extract_general_content(soup, url)
        page_data.update(general_content)
        
        # Extract products
        products = self.extract_products(soup)
        if products:
            # Optimize products (remove duplicates)
            unique_products = self._deduplicate_products(products)
            page_data['products'] = unique_products
        
        # Extract contact information
        contact_info = self.extract_contact_info(soup)
        if any(contact_info.values()):
            # Optimize contact info (remove duplicates)
            unique_contacts = self._deduplicate_contacts(contact_info)
            page_data['contact_info'] = unique_contacts
        
        return page_data
    
    def _deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products based on name and price"""
        unique_products = []
        seen_hashes = set()
        
        for product in products:
            # Create hash based on name and price
            name = product.get('name', '').lower().strip()
            price = product.get('price', '').lower().strip()
            product_hash = hashlib.md5(f"{name}:{price}".encode()).hexdigest()
            
            if product_hash not in seen_hashes:
                seen_hashes.add(product_hash)
                unique_products.append(product)
            else:
                with self._lock:
                    self._optimization_stats['duplicate_products_removed'] += 1
        
        return unique_products
    
    def _deduplicate_contacts(self, contact_info: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Remove duplicate contact information"""
        unique_contacts = {}
        seen_hashes = set()
        
        for contact_type, contacts in contact_info.items():
            unique_contacts[contact_type] = []
            for contact in contacts:
                contact_hash = hashlib.md5(contact.lower().encode()).hexdigest()
                if contact_hash not in seen_hashes:
                    seen_hashes.add(contact_hash)
                    unique_contacts[contact_type].append(contact)
                else:
                    with self._lock:
                        self._optimization_stats['duplicate_contacts_removed'] += 1
        
        return unique_contacts
    
    def _scrape_single_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single page with retry logic and optimization"""
        if url in self._visited:
            with self._lock:
                self._optimization_stats['duplicate_pages_skipped'] += 1
            return None
        
        with self._lock:
            self._visited.add(url)
        
        logger.info(f"Scraping page: {url}")
        
        # Get page content with retry logic
        content = None
        for attempt in range(self.max_retries):
            try:
                content = self.get_page_content(url)
                if content:
                    break
                time.sleep(self.retry_delay * (2 ** attempt))
            except Exception as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
        
        if not content:
            with self._lock:
                self._failed_urls.add(url)
            return None
        
        # Parse the page
        soup = BeautifulSoup(content, 'html.parser')
        page_data = self.parse_page(soup, url)
        
        # Check for content duplication
        content_hash = self._generate_content_hash(page_data)
        if content_hash in self._content_hashes:
            with self._lock:
                self._optimization_stats['duplicate_content_removed'] += 1
            return None
        
        with self._lock:
            self._content_hashes.add(content_hash)
            self._optimization_stats['total_pages_scraped'] += 1
            self._optimization_stats['content_cleaned'] += 1
        
        return page_data
    
    def _generate_content_hash(self, page_data: Dict[str, Any]) -> str:
        """Generate hash for content deduplication"""
        # Create a string representation of the key content
        content_parts = []
        
        if 'title' in page_data:
            content_parts.append(page_data['title'])
        if 'content' in page_data:
            content_parts.append(page_data['content'][:500])  # First 500 chars
        if 'products' in page_data:
            for product in page_data['products'][:3]:  # First 3 products
                content_parts.append(str(product))
        
        content_string = '|'.join(content_parts)
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def _get_urls_to_visit(self, url: str) -> List[str]:
        """Get URLs to visit from a single page"""
        content = self.get_page_content(url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        new_links = self.extract_links(soup, url)
        pagination_links = self.detect_pagination(soup, url)
        
        return new_links + pagination_links
    
    def scrape_site(self) -> List[Dict[str, Any]]:
        """Main scraping method with improved queue management, retry logic, and automatic optimization"""
        logger.info(f"Starting multithreaded scraping with {self.max_workers} workers")
        
        # Initialize with base URL
        self._url_queue.put(self.base_url)
        self._visited.clear()
        self._all_data.clear()
        self._failed_urls.clear()
        self._retry_count.clear()
        
        # Reset optimization stats
        self._optimization_stats = {
            'total_pages_scraped': 0,
            'duplicate_pages_skipped': 0,
            'duplicate_content_removed': 0,
            'duplicate_products_removed': 0,
            'duplicate_contacts_removed': 0,
            'content_cleaned': 0,
            'optimization_ratio': 0.0
        }
        
        page_count = 0
        active_workers = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit initial tasks
            futures = []
            for _ in range(min(self.max_workers, self.max_pages)):
                if not self._url_queue.empty():
                    url = self._url_queue.get_nowait()
                    future = executor.submit(self._scrape_single_page, url)
                    futures.append((future, url))
                    active_workers += 1
            
            # Process tasks with queue management
            while futures and page_count < self.max_pages:
                # Wait for any task to complete
                done, not_done = concurrent.futures.wait(
                    [f[0] for f in futures], 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for future in done:
                    # Find the URL for this future
                    url = None
                    for f, u in futures:
                        if f == future:
                            url = u
                            futures.remove((f, u))
                            active_workers -= 1
                            break
                    
                    if url:
                        try:
                            page_data = future.result()
                            if page_data:
                                with self._lock:
                                    self._all_data.append(page_data)
                                    page_count += 1
                                logger.info(f"Successfully scraped {url}")
                            else:
                                logger.warning(f"Failed to scrape {url}")
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                
                # Add new URLs to queue and submit new tasks
                while not self._url_queue.empty() and active_workers < self.max_workers and page_count < self.max_pages:
                    try:
                        url = self._url_queue.get_nowait()
                        future = executor.submit(self._scrape_single_page, url)
                        futures.append((future, url))
                        active_workers += 1
                    except queue.Empty:
                        break
                
                # Log progress
                queue_size = self._url_queue.qsize()
                logger.info(f"Processed {page_count} pages, {queue_size} URLs in queue, {len(self._failed_urls)} failed URLs")
                
                # If no active workers and queue is empty, we're done
                if active_workers == 0 and self._url_queue.empty():
                    break
        
        # Calculate optimization ratio
        total_processed = self._optimization_stats['total_pages_scraped'] + self._optimization_stats['duplicate_content_removed']
        if total_processed > 0:
            self._optimization_stats['optimization_ratio'] = (
                self._optimization_stats['duplicate_content_removed'] / total_processed * 100
            )
        
        logger.info(f"Multithreaded scraping completed. Processed {len(self._all_data)} pages, {len(self._failed_urls)} failed URLs.")
        logger.info(f"Optimization Stats: {self._optimization_stats}")
        
        # Log final statistics
        success_rate = len(self._all_data) / (len(self._all_data) + len(self._failed_urls)) * 100 if (len(self._all_data) + len(self._failed_urls)) > 0 else 0
        logger.info(f"Scraping Statistics: Success Rate: {success_rate:.1f}%, Total URLs: {len(self._visited)}, Failed URLs: {len(self._failed_urls)}")
        
        return self._all_data
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return self._optimization_stats.copy()
    
    def scrape_and_save(self, output_format: str = "both") -> Dict[str, str]:
        """Scrape site and save data with optimization"""
        logger.info(f"Starting to scrape {self.base_url}")
        
        # Run the scraper
        data = self.scrape_site()
        
        # Generate filename from base URL
        domain = urlparse(self.base_url).netloc.replace('.', '_')
        filename = f"scraped_{domain}"
        
        saved_files = {}
        
        if output_format in ["json", "both"]:
            self.save_to_json(data, filename)
            saved_files['json'] = str(self.output_dir / f"{filename}.json")
        
        if output_format in ["markdown", "both"]:
            self.save_to_markdown(data, filename)
            saved_files['markdown'] = str(self.output_dir / f"{filename}.md")
        
        # Save optimization stats
        stats_file = self.output_dir / f"{filename}_optimization_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(self._optimization_stats, f, indent=2)
        saved_files['optimization_stats'] = str(stats_file)
        
        logger.info(f"Scraping completed. Processed {len(data)} pages.")
        logger.info(f"Optimization completed: {self._optimization_stats['optimization_ratio']:.1f}% content deduplication")
        
        return saved_files 
import asyncio
import re
import threading
import concurrent.futures
import queue
import time
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from loguru import logger
from .base_scraper import BaseScraper


class UniversalScraper(BaseScraper):
    """Universal scraper that can handle any website with multithreading support"""
    
    def __init__(self, base_url: str, output_dir: str = "data/raw", max_pages: int = 100, max_workers: int = 10):
        super().__init__(base_url, output_dir)
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.pagination_patterns = [
            r'page=(\d+)',
            r'p=(\d+)',
            r'page/(\d+)',
            r'(\d+)/?$'
        ]
        self._lock = threading.Lock()
        self._visited = set()
        self._all_data = []
        self._url_queue = queue.Queue()
        self._failed_urls = set()
        self._retry_count = {}
        self.max_retries = 3
        self.retry_delay = 2
        
    def detect_pagination(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Detect pagination links"""
        pagination_urls = []
        
        # Look for common pagination patterns
        pagination_selectors = [
            'a[href*="page"]',
            'a[href*="p="]',
            '.pagination a',
            '.pager a',
            'nav a',
            '.next',
            '.prev',
            '[class*="page"] a',
            '[class*="pagination"] a'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(current_url, href)
                    if self._is_valid_pagination_url(absolute_url, current_url):
                        pagination_urls.append(absolute_url)
        
        return list(set(pagination_urls))
    
    def _is_valid_pagination_url(self, url: str, base_url: str) -> bool:
        """Check if URL is a valid pagination URL"""
        if not url.startswith(self.base_url):
            return False
        
        # Check for pagination patterns
        for pattern in self.pagination_patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information from page"""
        contact_info = {}
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact_info['emails'] = list(set(emails))
        
        # Phone patterns
        phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, soup.get_text())
        if phones:
            contact_info['phones'] = [''.join(phone) for phone in phones]
        
        # Address patterns
        address_selectors = [
            '[class*="address"]',
            '[class*="contact"]',
            '[id*="address"]',
            '[id*="contact"]'
        ]
        
        for selector in address_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 10:  # Likely an address
                    contact_info['address'] = text
                    break
        
        return contact_info
    
    def extract_products(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract product information from page"""
        products = []
        
        # Common product selectors
        product_selectors = [
            '.product',
            '.item',
            '[class*="product"]',
            '[class*="item"]',
            'article',
            '.card',
            '.product-card'
        ]
        
        for selector in product_selectors:
            product_elements = soup.select(selector)
            
            for element in product_elements:
                product = {}
                
                # Extract product name
                name_selectors = ['h1', 'h2', 'h3', '.title', '.name', '[class*="title"]', '[class*="name"]']
                for name_sel in name_selectors:
                    name_elem = element.select_one(name_sel)
                    if name_elem:
                        product['name'] = name_elem.get_text(strip=True)
                        break
                
                # Extract price
                price_selectors = ['.price', '[class*="price"]', '.cost', '.amount']
                for price_sel in price_selectors:
                    price_elem = element.select_one(price_sel)
                    if price_elem:
                        product['price'] = price_elem.get_text(strip=True)
                        break
                
                # Extract description
                desc_selectors = ['.description', '[class*="description"]', '.desc', 'p']
                for desc_sel in desc_selectors:
                    desc_elem = element.select_one(desc_sel)
                    if desc_elem:
                        product['description'] = desc_elem.get_text(strip=True)
                        break
                
                # Extract image
                img_elem = element.select_one('img')
                if img_elem and img_elem.get('src'):
                    product['image'] = urljoin(self.base_url, img_elem['src'])
                
                # Extract link
                link_elem = element.select_one('a')
                if link_elem and link_elem.get('href'):
                    product['link'] = urljoin(self.base_url, link_elem['href'])
                
                if product:
                    products.append(product)
        
        return products
    
    def extract_general_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract general content from page"""
        content = {
            'url': url,
            'title': '',
            'description': '',
            'content': '',
            'links': [],
            'images': [],
            'contact_info': {}
        }
        
        # Extract title
        title_elem = soup.find('title')
        if title_elem:
            content['title'] = title_elem.get_text(strip=True)
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content['description'] = meta_desc['content']
        
        # Extract main content
        main_selectors = ['main', '.main', '#main', '.content', '#content', 'article']
        for selector in main_selectors:
            main_elem = soup.select_one(selector)
            if main_elem:
                content['content'] = main_elem.get_text(strip=True)
                break
        
        if not content['content']:
            # Fallback to body content
            body = soup.find('body')
            if body:
                content['content'] = body.get_text(strip=True)
        
        # Extract links
        content['links'] = self.extract_links(soup, url)
        
        # Extract images
        for img in soup.find_all('img'):
            if img.get('src'):
                content['images'].append(urljoin(url, img['src']))
        
        # Extract contact information
        content['contact_info'] = self.extract_contact_info(soup)
        
        return content
    
    def parse_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse a single page and extract data"""
        page_data = self.extract_general_content(soup, url)
        
        # Try to extract products if this looks like a product page
        products = self.extract_products(soup)
        if products:
            page_data['products'] = products
        
        return page_data
    
    def _scrape_single_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single page with retry logic and thread safety"""
        with self._lock:
            if url in self._visited:
                return None
            self._visited.add(url)
        
        logger.info(f"Scraping page: {url}")
        
        # Retry logic for failed requests
        for attempt in range(self.max_retries):
            try:
                # Try to get content with requests first
                content = self.get_page_content(url)
                
                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    page_data = self.parse_page(soup, url)
                    
                    with self._lock:
                        self._all_data.append(page_data)
                    
                    # Get new URLs from this page
                    new_urls = self._get_urls_to_visit(url)
                    for new_url in new_urls:
                        with self._lock:
                            if new_url not in self._visited and new_url not in self._failed_urls:
                                self._url_queue.put(new_url)
                    
                    return page_data
                
                # If content is None, try with Selenium as fallback
                if attempt == 0:  # Only try Selenium on first attempt
                    logger.info(f"Trying Selenium for {url}")
                    content = self.get_page_with_selenium(url, wait_time=15)
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        page_data = self.parse_page(soup, url)
                        
                        with self._lock:
                            self._all_data.append(page_data)
                        
                        # Get new URLs from this page
                        new_urls = self._get_urls_to_visit(url)
                        for new_url in new_urls:
                            with self._lock:
                                if new_url not in self._visited and new_url not in self._failed_urls:
                                    self._url_queue.put(new_url)
                        
                        return page_data
                
                # If we get here, the request failed
                if attempt < self.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {url}, retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error(f"Failed to scrape {url} after {self.max_retries} attempts")
                    with self._lock:
                        self._failed_urls.add(url)
                    return None
                    
            except Exception as e:
                logger.error(f"Error scraping {url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 1.5
                else:
                    with self._lock:
                        self._failed_urls.add(url)
                    return None
        
        return None
    
    def _get_urls_to_visit(self, url: str) -> List[str]:
        """Get URLs to visit from a single page"""
        content = self.get_page_content(url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        new_links = self.extract_links(soup, url)
        pagination_links = self.detect_pagination(soup, url)
        
        return new_links + pagination_links
    
    async def scrape_site(self) -> List[Dict[str, Any]]:
        """Main scraping method with improved queue management and retry logic"""
        logger.info(f"Starting multithreaded scraping with {self.max_workers} workers")
        
        # Initialize with base URL
        self._url_queue.put(self.base_url)
        self._visited.clear()
        self._all_data.clear()
        self._failed_urls.clear()
        self._retry_count.clear()
        
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
        
        logger.info(f"Multithreaded scraping completed. Processed {len(self._all_data)} pages, {len(self._failed_urls)} failed URLs.")
        
        # Log final statistics
        success_rate = len(self._all_data) / (len(self._all_data) + len(self._failed_urls)) * 100 if (len(self._all_data) + len(self._failed_urls)) > 0 else 0
        logger.info(f"Scraping Statistics: Success Rate: {success_rate:.1f}%, Total URLs: {len(self._visited)}, Failed URLs: {len(self._failed_urls)}")
        
        return self._all_data
    
    def scrape_and_save(self, output_format: str = "both") -> Dict[str, str]:
        """Scrape site and save data"""
        logger.info(f"Starting to scrape {self.base_url}")
        
        # Run the scraper
        data = asyncio.run(self.scrape_site())
        
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
        
        logger.info(f"Scraping completed. Processed {len(data)} pages.")
        return saved_files 
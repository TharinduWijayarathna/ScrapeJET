import asyncio
import re
import threading
import concurrent.futures
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
        """Scrape a single page (thread-safe)"""
        with self._lock:
            if url in self._visited:
                return None
            self._visited.add(url)
        
        logger.info(f"Scraping page: {url}")
        
        # Try different methods to get page content
        content = None
        
        # First try with requests
        content = self.get_page_content(url)
        
        # If that fails, try with Selenium
        if not content:
            content = self.get_page_with_selenium(url)
        
        # If that fails, try with Playwright (async, but we'll handle this differently)
        if not content:
            # For now, skip Playwright in threaded mode to avoid complexity
            logger.warning(f"Failed to get content from {url}")
            return None
        
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            page_data = self.parse_page(soup, url)
            
            with self._lock:
                self._all_data.append(page_data)
            
            return page_data
        else:
            logger.warning(f"Failed to get content from {url}")
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
        """Main scraping method with multithreading support"""
        logger.info(f"Starting multithreaded scraping with {self.max_workers} workers")
        
        # Initialize with base URL
        urls_to_visit = [self.base_url]
        self._visited.clear()
        self._all_data.clear()
        
        page_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while urls_to_visit and page_count < self.max_pages:
                # Get current batch of URLs to process
                current_batch = urls_to_visit[:self.max_workers]
                urls_to_visit = urls_to_visit[self.max_workers:]
                
                # Submit scraping tasks
                future_to_url = {
                    executor.submit(self._scrape_single_page, url): url 
                    for url in current_batch
                }
                
                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        page_data = future.result()
                        if page_data:
                            page_count += 1
                            
                            # Get new URLs from this page
                            new_urls = self._get_urls_to_visit(url)
                            for new_url in new_urls:
                                with self._lock:
                                    if new_url not in self._visited and new_url not in urls_to_visit:
                                        urls_to_visit.append(new_url)
                    
                    except Exception as e:
                        logger.error(f"Error scraping {url}: {e}")
                
                # Log progress
                logger.info(f"Processed {page_count} pages, {len(urls_to_visit)} URLs remaining")
        
        logger.info(f"Multithreaded scraping completed. Processed {len(self._all_data)} pages.")
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
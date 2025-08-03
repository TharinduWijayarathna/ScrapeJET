#!/usr/bin/env python3
"""
Super Universal Web Scraper - Advanced scraping with Selenium, Playwright, and Queue Management
"""

import os
import json
import time
import hashlib
import threading
import queue
import asyncio
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests
from loguru import logger

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Playwright imports
from playwright.async_api import async_playwright, Page, Browser

from .base_scraper import BaseScraper


class UniversalScraper(BaseScraper):
    """Super universal scraper with advanced capabilities"""
    
    def __init__(self, base_url: str, output_dir: str = "data/raw", expected_pages: int = None):
        super().__init__(base_url, output_dir)
        
        # Configuration from environment variables
        self.max_pages = int(os.getenv("MAX_PAGES", "100"))
        self.max_workers = int(os.getenv("MAX_WORKERS", "5"))
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.retry_count = int(os.getenv("RETRY_COUNT", "3"))
        self.delay = float(os.getenv("REQUEST_DELAY", "1.0"))
        
        # Override max_pages if expected_pages is provided
        if expected_pages is not None:
            self.max_pages = expected_pages
            logger.info(f"Setting max_pages to {expected_pages} based on expected_pages parameter")
        
        # Advanced scraping settings
        self.use_selenium = os.getenv("USE_SELENIUM", "true").lower() == "true"
        self.use_playwright = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"
        self.wait_for_js = int(os.getenv("WAIT_FOR_JS", "5"))
        self.scroll_pages = os.getenv("SCROLL_PAGES", "true").lower() == "true"
        self.screenshot_pages = os.getenv("SCREENSHOT_PAGES", "false").lower() == "true"
        
        # Queue management
        self._url_queue = queue.Queue()
        self._lock = threading.Lock()
        self._visited = set()
        self._data = []
        self._failed_urls = set()
        self._processing = set()
        
        # Browser instances (thread-safe)
        self._selenium_drivers = {}
        self._playwright_browsers = {}
        
        # Stats
        self.stats = {
            'total_pages': 0,
            'successful_pages': 0,
            'failed_pages': 0,
            'duplicate_pages': 0,
            'selenium_pages': 0,
            'playwright_pages': 0,
            'requests_pages': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _get_selenium_driver(self, worker_id: int) -> Optional[webdriver.Chrome]:
        """Get or create Selenium driver for worker"""
        if worker_id not in self._selenium_drivers:
            try:
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(self.timeout)
                self._selenium_drivers[worker_id] = driver
                logger.debug(f"Created Selenium driver for worker {worker_id}")
            except Exception as e:
                logger.error(f"Failed to create Selenium driver for worker {worker_id}: {e}")
                return None
        
        return self._selenium_drivers[worker_id]
    
    async def _get_playwright_browser(self, worker_id: int) -> Optional[Browser]:
        """Get or create Playwright browser for worker"""
        if worker_id not in self._playwright_browsers:
            try:
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security'
                    ]
                )
                self._playwright_browsers[worker_id] = browser
                logger.debug(f"Created Playwright browser for worker {worker_id}")
            except Exception as e:
                logger.error(f"Failed to create Playwright browser for worker {worker_id}: {e}")
                return None
        
        return self._playwright_browsers[worker_id]
    
    def get_page_content_advanced(self, url: str, worker_id: int = 0) -> Optional[str]:
        """Get page content using multiple methods with fallback"""
        
        # Method 1: Try requests first (fastest)
        content = self.get_page_content_requests(url)
        if content:
            self.stats['requests_pages'] += 1
            return content
        
        # Method 2: Try Selenium if enabled
        if self.use_selenium:
            content = self.get_page_content_selenium(url, worker_id)
            if content:
                self.stats['selenium_pages'] += 1
                return content
        
        # Method 3: Try Playwright if enabled
        if self.use_playwright:
            content = asyncio.run(self.get_page_content_playwright(url, worker_id))
            if content:
                self.stats['playwright_pages'] += 1
                return content
        
        return None
    
    def get_page_content_requests(self, url: str) -> Optional[str]:
        """Get page content using requests (fastest method)"""
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} with requests (attempt {attempt + 1})")
                if attempt < self.retry_count - 1:
                    time.sleep(self.delay)
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error fetching {url} with requests (attempt {attempt + 1})")
                if attempt < self.retry_count - 1:
                    time.sleep(self.delay)
                continue
            except Exception as e:
                logger.error(f"Error fetching {url} with requests: {e}")
                break
        
        return None
    
    def get_page_content_selenium(self, url: str, worker_id: int) -> Optional[str]:
        """Get page content using Selenium"""
        driver = self._get_selenium_driver(worker_id)
        if not driver:
            return None
        
        try:
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, self.wait_for_js).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to load lazy content
            if self.scroll_pages:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            
            # Take screenshot if enabled
            if self.screenshot_pages:
                screenshot_path = self.output_dir / f"screenshot_{hashlib.md5(url.encode()).hexdigest()[:8]}.png"
                driver.save_screenshot(str(screenshot_path))
            
            return driver.page_source
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url} with Selenium")
            return None
        except WebDriverException as e:
            logger.error(f"Selenium error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Selenium error for {url}: {e}")
            return None
    
    async def get_page_content_playwright(self, url: str, worker_id: int) -> Optional[str]:
        """Get page content using Playwright"""
        browser = await self._get_playwright_browser(worker_id)
        if not browser:
            return None
        
        page = None
        try:
            page = await browser.new_page()
            
            # Set user agent
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
            
            # Wait for JavaScript to load
            await page.wait_for_timeout(self.wait_for_js * 1000)
            
            # Scroll to load lazy content
            if self.scroll_pages:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(1000)
            
            # Take screenshot if enabled
            if self.screenshot_pages:
                screenshot_path = self.output_dir / f"screenshot_{hashlib.md5(url.encode()).hexdigest()[:8]}.png"
                await page.screenshot(path=str(screenshot_path))
            
            return await page.content()
            
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
        finally:
            if page:
                await page.close()
    
    def extract_links_advanced(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid links with advanced filtering"""
        links = []
        
        # Extract all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(current_url, href)
            
            # Only include links from the same domain
            if urlparse(absolute_url).netloc == urlparse(self.base_url).netloc:
                # Filter out common non-content URLs
                if not self._is_non_content_url(absolute_url):
                    links.append(absolute_url)
        
        # Also extract links from JavaScript (basic pattern matching)
        script_content = soup.find_all('script')
        for script in script_content:
            if script.string:
                js_links = self._extract_links_from_js(script.string, current_url)
                links.extend(js_links)
        
        return list(set(links))  # Remove duplicates
    
    def _is_non_content_url(self, url: str) -> bool:
        """Check if URL is likely non-content"""
        non_content_patterns = [
            '/admin', '/login', '/logout', '/register', '/signup',
            '/api/', '/ajax/', '/json/', '/xml/', '/rss',
            '/sitemap', '/robots.txt', '/favicon.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.zip', '.rar', '.tar', '.gz',
            'mailto:', 'tel:', 'javascript:'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in non_content_patterns)
    
    def _extract_links_from_js(self, js_content: str, base_url: str) -> List[str]:
        """Extract URLs from JavaScript content"""
        import re
        
        # Common patterns for URLs in JavaScript
        url_patterns = [
            r'["\']([^"\']*\.html?[^"\']*)["\']',
            r'["\']([^"\']*\.php[^"\']*)["\']',
            r'["\']([^"\']*\.aspx[^"\']*)["\']',
            r'["\']([^"\']*\.jsp[^"\']*)["\']',
            r'["\']([^"\']*\.asp[^"\']*)["\']',
            r'["\']([^"\']*\.cgi[^"\']*)["\']',
            r'["\']([^"\']*\.pl[^"\']*)["\']',
            r'["\']([^"\']*\.py[^"\']*)["\']',
            r'["\']([^"\']*\.rb[^"\']*)["\']',
            r'["\']([^"\']*\.cs[^"\']*)["\']',
            r'["\']([^"\']*\.java[^"\']*)["\']',
            r'["\']([^"\']*\.go[^"\']*)["\']',
            r'["\']([^"\']*\.rs[^"\']*)["\']',
            r'["\']([^"\']*\.swift[^"\']*)["\']',
            r'["\']([^"\']*\.kt[^"\']*)["\']',
            r'["\']([^"\']*\.scala[^"\']*)["\']',
            r'["\']([^"\']*\.clj[^"\']*)["\']',
            r'["\']([^"\']*\.hs[^"\']*)["\']',
            r'["\']([^"\']*\.ml[^"\']*)["\']',
            r'["\']([^"\']*\.fs[^"\']*)["\']',
            r'["\']([^"\']*\.v[^"\']*)["\']',
            r'["\']([^"\']*\.vhd[^"\']*)["\']',
            r'["\']([^"\']*\.sv[^"\']*)["\']',
            r'["\']([^"\']*\.vbs[^"\']*)["\']',
            r'["\']([^"\']*\.ps1[^"\']*)["\']',
            r'["\']([^"\']*\.sh[^"\']*)["\']',
            r'["\']([^"\']*\.bat[^"\']*)["\']',
            r'["\']([^"\']*\.cmd[^"\']*)["\']',
            r'["\']([^"\']*\.exe[^"\']*)["\']',
            r'["\']([^"\']*\.dll[^"\']*)["\']',
            r'["\']([^"\']*\.so[^"\']*)["\']',
            r'["\']([^"\']*\.dylib[^"\']*)["\']',
            r'["\']([^"\']*\.a[^"\']*)["\']',
            r'["\']([^"\']*\.lib[^"\']*)["\']',
            r'["\']([^"\']*\.o[^"\']*)["\']',
            r'["\']([^"\']*\.obj[^"\']*)["\']',
            r'["\']([^"\']*\.class[^"\']*)["\']',
            r'["\']([^"\']*\.jar[^"\']*)["\']',
            r'["\']([^"\']*\.war[^"\']*)["\']',
            r'["\']([^"\']*\.ear[^"\']*)["\']',
            r'["\']([^"\']*\.apk[^"\']*)["\']',
            r'["\']([^"\']*\.ipa[^"\']*)["\']',
            r'["\']([^"\']*\.deb[^"\']*)["\']',
            r'["\']([^"\']*\.rpm[^"\']*)["\']',
            r'["\']([^"\']*\.msi[^"\']*)["\']',
            r'["\']([^"\']*\.pkg[^"\']*)["\']',
            r'["\']([^"\']*\.dmg[^"\']*)["\']',
            r'["\']([^"\']*\.iso[^"\']*)["\']',
            r'["\']([^"\']*\.img[^"\']*)["\']',
            r'["\']([^"\']*\.vmdk[^"\']*)["\']',
            r'["\']([^"\']*\.vdi[^"\']*)["\']',
            r'["\']([^"\']*\.vhd[^"\']*)["\']',
            r'["\']([^"\']*\.vhdx[^"\']*)["\']',
            r'["\']([^"\']*\.ova[^"\']*)["\']',
            r'["\']([^"\']*\.ovf[^"\']*)["\']',
            r'["\"]/([^"\"]*)["\"]',  # General path pattern
        ]
        
        links = []
        for pattern in url_patterns:
            matches = re.findall(pattern, js_content)
            for match in matches:
                if match.startswith('/'):
                    # Relative URL
                    absolute_url = urljoin(base_url, match)
                    if urlparse(absolute_url).netloc == urlparse(self.base_url).netloc:
                        links.append(absolute_url)
                elif match.startswith('http'):
                    # Absolute URL
                    if urlparse(match).netloc == urlparse(self.base_url).netloc:
                        links.append(match)
        
        return list(set(links))
    
    def extract_page_data_advanced(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract comprehensive data from a page"""
        data = {
            'url': url,
            'title': '',
            'content': '',
            'links': [],
            'metadata': {},
            'images': [],
            'forms': [],
            'scripts': [],
            'styles': [],
            'timestamp': time.time()
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            data['title'] = title_tag.get_text().strip()
        
        # Extract main content
        main_content = self._extract_main_content_advanced(soup)
        data['content'] = main_content
        
        # Extract links
        data['links'] = self.extract_links_advanced(soup, url)
        
        # Extract metadata
        data['metadata'] = self._extract_metadata_advanced(soup)
        
        # Extract images
        data['images'] = self._extract_images(soup, url)
        
        # Extract forms
        data['forms'] = self._extract_forms(soup, url)
        
        # Extract scripts and styles
        data['scripts'] = self._extract_scripts(soup, url)
        data['styles'] = self._extract_styles(soup, url)
        
        return data
    
    def _extract_main_content_advanced(self, soup: BeautifulSoup) -> str:
        """Extract main content with advanced cleaning"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            element.decompose()
        
        # Try to find main content areas with priority
        main_selectors = [
            'main', 'article', '.content', '.main-content', '.post-content', '.entry-content',
            '#content', '#main', '.post', '.article', '[role="main"]', '.container',
            '.wrapper', '.page-content', '.site-content', '.primary-content'
        ]
        
        content = ""
        for selector in main_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator=' ', strip=True)
                break
        
        # If no main content found, use body
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
        
        # Advanced content cleaning
        content = self._clean_content_advanced(content)
        return content[:15000]  # Increased limit for comprehensive content
    
    def _clean_content_advanced(self, text: str) -> str:
        """Advanced content cleaning"""
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
            r'loading\.\.\.',
            r'please wait\.\.\.',
            r'javascript required',
            r'this site uses cookies',
            r'accept cookies',
            r'decline cookies',
            r'subscribe to newsletter',
            r'newsletter signup',
            r'follow us on',
            r'like us on facebook',
            r'follow us on twitter',
            r'follow us on instagram',
            r'follow us on linkedin',
            r'follow us on youtube',
            r'follow us on tiktok',
            r'follow us on snapchat',
            r'follow us on pinterest',
            r'follow us on reddit',
            r'follow us on discord',
            r'follow us on telegram',
            r'follow us on whatsapp',
            r'follow us on wechat',
            r'follow us on weibo',
            r'follow us on vk',
            r'follow us on ok',
            r'follow us on odnoklassniki',
            r'follow us on viber',
            r'follow us on line',
            r'follow us on kik',
            r'follow us on skype',
            r'follow us on zoom',
            r'follow us on teams',
            r'follow us on slack',
            r'follow us on discord',
            r'follow us on telegram',
            r'follow us on whatsapp',
            r'follow us on wechat',
            r'follow us on weibo',
            r'follow us on vk',
            r'follow us on ok',
            r'follow us on odnoklassniki',
            r'follow us on viber',
            r'follow us on line',
            r'follow us on kik',
            r'follow us on skype',
            r'follow us on zoom',
            r'follow us on teams',
            r'follow us on slack',
        ]
        
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _extract_metadata_advanced(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract comprehensive metadata"""
        metadata = {}
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                metadata[name] = content
        
        # Open Graph tags
        for meta in soup.find_all('meta', property=True):
            if meta['property'].startswith('og:'):
                metadata[meta['property']] = meta.get('content', '')
        
        # Twitter Card tags
        for meta in soup.find_all('meta', attrs={'name': True}):
            if meta['name'].startswith('twitter:'):
                metadata[meta['name']] = meta.get('content', '')
        
        # Schema.org structured data
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    metadata['schema_org'] = data
            except:
                continue
        
        return metadata
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image information"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            absolute_url = urljoin(base_url, src)
            
            image_info = {
                'src': absolute_url,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            }
            images.append(image_info)
        
        return images
    
    def _extract_forms(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract form information"""
        forms = []
        for form in soup.find_all('form'):
            form_info = {
                'action': urljoin(base_url, form.get('action', '')),
                'method': form.get('method', 'get'),
                'enctype': form.get('enctype', ''),
                'inputs': []
            }
            
            for input_elem in form.find_all('input'):
                input_info = {
                    'type': input_elem.get('type', 'text'),
                    'name': input_elem.get('name', ''),
                    'value': input_elem.get('value', ''),
                    'placeholder': input_elem.get('placeholder', '')
                }
                form_info['inputs'].append(input_info)
            
            forms.append(form_info)
        
        return forms
    
    def _extract_scripts(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract script URLs"""
        scripts = []
        for script in soup.find_all('script', src=True):
            src = script['src']
            absolute_url = urljoin(base_url, src)
            scripts.append(absolute_url)
        return scripts
    
    def _extract_styles(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract stylesheet URLs"""
        styles = []
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                styles.append(absolute_url)
        return styles
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def scrape_page_worker(self, worker_id: int) -> None:
        """Worker function for scraping pages from queue"""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get URL from queue with timeout
                url = self._url_queue.get(timeout=10)
                
                # Check if this is a stop signal
                if url is None:
                    logger.info(f"Worker {worker_id} received stop signal")
                    break
                
                # Check if already visited
                with self._lock:
                    if url in self._visited or url in self._processing:
                        self._url_queue.task_done()
                        continue
                    self._visited.add(url)
                    self._processing.add(url)
                
                logger.info(f"Worker {worker_id} scraping: {url}")
                
                # Get page content using advanced methods
                content = self.get_page_content_advanced(url, worker_id)
                
                if not content:
                    with self._lock:
                        self._failed_urls.add(url)
                        self.stats['failed_pages'] += 1
                        self._processing.remove(url)
                    self._url_queue.task_done()
                    continue
                
                # Parse content
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract data
                page_data = self.extract_page_data_advanced(soup, url)
                
                # Check for duplicates
                content_hash = self._generate_content_hash(page_data['content'])
                if content_hash in [self._generate_content_hash(item['content']) for item in self._data]:
                    with self._lock:
                        self.stats['duplicate_pages'] += 1
                        self._processing.remove(url)
                    self._url_queue.task_done()
                    continue
                
                # Add content hash to data
                page_data['content_hash'] = content_hash
                
                with self._lock:
                    self._data.append(page_data)
                    self.stats['successful_pages'] += 1
                    self._processing.remove(url)
                
                # Add new URLs to queue
                new_urls = page_data.get('links', [])
                for new_url in new_urls:
                    if new_url not in self._visited and new_url not in self._processing:
                        self._url_queue.put(new_url)
                
                # Mark task as done
                self._url_queue.task_done()
                
                # Small delay to be respectful
                time.sleep(self.delay)
                
            except queue.Empty:
                logger.info(f"Worker {worker_id} queue empty, stopping")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                try:
                    self._url_queue.task_done()
                except:
                    pass
        
        logger.info(f"Worker {worker_id} finished")
    
    def scrape_site(self) -> List[Dict[str, Any]]:
        """Main scraping method with advanced queue management"""
        logger.info(f"Starting super scraper for {self.base_url}")
        logger.info(f"Configuration: max_pages={self.max_pages}, max_workers={self.max_workers}")
        logger.info(f"Advanced features: Selenium={self.use_selenium}, Playwright={self.use_playwright}")
        
        self.stats['start_time'] = time.time()
        
        # Reset state
        self._visited.clear()
        self._processing.clear()
        self._failed_urls.clear()
        self._data.clear()
        
        # Initialize queue with base URL
        self._url_queue.put(self.base_url)
        
        # Create and start workers
        workers = []
        for worker_id in range(self.max_workers):
            worker = threading.Thread(target=self.scrape_page_worker, args=(worker_id,))
            worker.daemon = True
            worker.start()
            workers.append(worker)
            logger.info(f"Started worker {worker_id}")
        
        # Monitor progress with better logic
        last_report_time = time.time()
        while True:
            current_time = time.time()
            queue_size = self._url_queue.qsize()
            data_size = len(self._data)
            
            # Report progress every 10 seconds
            if current_time - last_report_time >= 10:
                logger.info(f"Progress: {data_size} pages scraped, {queue_size} URLs in queue, {len(self._processing)} processing")
                last_report_time = current_time
            
            # Check if we should stop
            if data_size >= self.max_pages:
                logger.info(f"Reached max pages limit ({self.max_pages})")
                break
            
            # Check if queue is empty and no workers are processing
            if queue_size == 0 and len(self._processing) == 0:
                logger.info("Queue empty and no workers processing, stopping")
                break
            
            time.sleep(2)
        
        # Stop all workers
        logger.info("Stopping all workers...")
        for _ in range(self.max_workers):
            self._url_queue.put(None)  # Signal to stop
        
        # Wait for workers to finish
        for i, worker in enumerate(workers):
            worker.join(timeout=30)
            logger.info(f"Worker {i} joined")
        
        # Cleanup browser instances
        self._cleanup_browsers()
        
        self.stats['end_time'] = time.time()
        self.stats['total_pages'] = len(self._data)
        
        logger.info(f"Super scraping completed. Processed {len(self._data)} pages.")
        logger.info(f"Stats: {self.stats}")
        
        return self._data
    
    def _cleanup_browsers(self):
        """Cleanup browser instances"""
        # Cleanup Selenium drivers
        for worker_id, driver in self._selenium_drivers.items():
            try:
                driver.quit()
            except:
                pass
        self._selenium_drivers.clear()
        
        # Cleanup Playwright browsers
        for worker_id, browser in self._playwright_browsers.items():
            try:
                asyncio.run(browser.close())
            except:
                pass
        self._playwright_browsers.clear()
    
    def parse_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse a single page and extract data"""
        return self.extract_page_data_advanced(soup, url)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics"""
        return self.stats.copy()
    
    def optimize_data_for_rag(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize and process scraped data for RAG usage"""
        logger.info("Optimizing data for RAG...")
        
        optimized_data = []
        
        for page in data:
            # Create optimized page data
            optimized_page = {
                'url': page.get('url', ''),
                'title': page.get('title', ''),
                'content': page.get('content', ''),
                'metadata': page.get('metadata', {}),
                'site_domain': urlparse(page.get('url', '')).netloc,
                'page_type': self._identify_page_type(page),
                'content_summary': self._generate_content_summary(page.get('content', '')),
                'key_topics': self._extract_key_topics(page.get('content', '')),
                'timestamp': page.get('timestamp', time.time()),
                'content_hash': page.get('content_hash', ''),
                'word_count': len(page.get('content', '').split()),
                'images_count': len(page.get('images', [])),
                'forms_count': len(page.get('forms', [])),
                'links_count': len(page.get('links', []))
            }
            
            # Add structured data if available
            if 'metadata' in page and 'schema_org' in page['metadata']:
                optimized_page['structured_data'] = page['metadata']['schema_org']
            
            optimized_data.append(optimized_page)
        
        logger.info(f"Optimized {len(optimized_data)} pages for RAG")
        return optimized_data
    
    def _identify_page_type(self, page: Dict[str, Any]) -> str:
        """Identify the type of page based on content and URL"""
        url = page.get('url', '').lower()
        content = page.get('content', '').lower()
        title = page.get('title', '').lower()
        
        # Product page indicators
        if any(word in url for word in ['product', 'item', 'goods', 'buy', 'shop']):
            return 'product'
        if any(word in content for word in ['price', 'add to cart', 'buy now', 'product']):
            return 'product'
        
        # Category page indicators
        if any(word in url for word in ['category', 'catalog', 'collection']):
            return 'category'
        
        # Contact page indicators
        if any(word in url for word in ['contact', 'about', 'company']):
            return 'contact'
        
        # Blog/Article indicators
        if any(word in url for word in ['blog', 'article', 'news', 'post']):
            return 'article'
        
        # Home page
        if url.endswith('/') or url.split('/')[-1] == '':
            return 'home'
        
        return 'general'
    
    def _generate_content_summary(self, content: str) -> str:
        """Generate a brief summary of the content"""
        if not content:
            return ""
        
        # Take first 200 characters as summary
        summary = content[:200].strip()
        if len(content) > 200:
            summary += "..."
        
        return summary
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from content"""
        if not content:
            return []
        
        # Simple keyword extraction (can be enhanced with NLP)
        words = content.lower().split()
        word_freq = {}
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 5 most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:5]]
    
    def scrape_and_save(self, output_format: str = "json") -> Dict[str, str]:
        """Scrape site and save data"""
        data = self.scrape_site()
        
        # Optimize data for RAG
        optimized_data = self.optimize_data_for_rag(data)
        
        # Generate filename
        domain = urlparse(self.base_url).netloc.replace('.', '_')
        filename = f"scraped_{domain}_{int(time.time())}"
        
        saved_files = {}
        
        if output_format in ["json", "both"]:
            self.save_to_json(optimized_data, filename)
            saved_files['json'] = str(self.output_dir / f"{filename}.json")
        
        if output_format in ["markdown", "both"]:
            self.save_to_markdown(optimized_data, filename)
            saved_files['markdown'] = str(self.output_dir / f"{filename}.md")
        
        return saved_files
    
    def save_data(self, filename: str = None) -> str:
        """Save scraped data to file"""
        data = self.scrape_site()
        
        # Optimize data for RAG
        optimized_data = self.optimize_data_for_rag(data)
        
        # Generate filename
        if not filename:
            domain = urlparse(self.base_url).netloc.replace('.', '_')
            filename = f"scraped_{domain}_{int(time.time())}"
        
        filepath = self.output_dir / f"{filename}.json"
        
        # Prepare data for saving
        save_data = {
            'base_url': self.base_url,
            'scrape_stats': self.stats,
            'pages': optimized_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filepath}")
        return str(filepath)
    
    def __del__(self):
        """Cleanup on destruction"""
        self._cleanup_browsers() 
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import aiofiles
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from loguru import logger


class BaseScraper(ABC):
    """Base class for all web scrapers"""
    
    def __init__(self, base_url: str, output_dir: str = "data/raw"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()
        self.data = []
        
    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content using requests"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_page_with_selenium(self, url: str, wait_time: int = 10) -> Optional[str]:
        """Get page content using Selenium for JavaScript-heavy sites"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to load lazy content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            return driver.page_source
        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    async def get_page_with_playwright(self, url: str) -> Optional[str]:
        """Get page content using Playwright for complex sites"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle')
                
                # Scroll to load lazy content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                logger.error(f"Error fetching {url} with Playwright: {e}")
                await browser.close()
                return None
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from a page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Only include links from the same domain
            if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                links.append(absolute_url)
        
        return list(set(links))
    
    def save_to_json(self, data: List[Dict], filename: str):
        """Save data to JSON file"""
        filepath = self.output_dir / f"{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {filepath}")
    
    def save_to_markdown(self, data: List[Dict], filename: str):
        """Save data to Markdown file"""
        filepath = self.output_dir / f"{filename}.md"
        
        markdown_content = []
        for item in data:
            if isinstance(item, dict):
                # Convert dict to markdown
                item_content = []
                for key, value in item.items():
                    if isinstance(value, str):
                        item_content.append(f"**{key}:** {value}")
                    elif isinstance(value, list):
                        item_content.append(f"**{key}:**")
                        for sub_item in value:
                            item_content.append(f"- {sub_item}")
                    else:
                        item_content.append(f"**{key}:** {value}")
                markdown_content.append("\n".join(item_content))
            else:
                markdown_content.append(str(item))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n\n---\n\n".join(markdown_content))
        
        logger.info(f"Data saved to {filepath}")
    
    @abstractmethod
    def parse_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse a single page and extract data"""
        pass
    
    @abstractmethod
    def scrape_site(self) -> List[Dict[str, Any]]:
        """Main scraping method"""
        pass 
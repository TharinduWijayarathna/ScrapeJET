#!/usr/bin/env python3
"""
Celery Tasks for ScrapeJET
Production-grade background tasks for web scraping and RAG processing
"""

import os
import sys
import json
import time
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse, urljoin
from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure
from loguru import logger

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.celery_app import celery_app
from src.scraper.universal_scraper import UniversalScraper
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, BedrockInterface, RAGSystem

# Global variables for caching
_vector_store = None
_rag_system = None

def get_vector_store():
    """Get or create vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

def get_rag_system():
    """Get or create RAG system instance"""
    global _rag_system
    if _rag_system is None:
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                vector_store = get_vector_store()
                llm_interface = OpenAIInterface(model="gpt-3.5-turbo")
                _rag_system = RAGSystem(vector_store, llm_interface)
                logger.info("RAG system initialized in worker")
            else:
                logger.warning("OpenAI API key not found, RAG system not available")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
    return _rag_system


class CallbackTask(Task):
    """Custom task class with callback support"""
    
    def __call__(self, *args, **kwargs):
        """Execute task with callback support"""
        self.progress_callback = kwargs.pop('progress_callback', None)
        return super().__call__(*args, **kwargs)
    
    def update_progress(self, progress_data: Dict[str, Any]):
        """Update task progress"""
        if hasattr(self, 'progress_callback') and self.progress_callback:
            try:
                self.progress_callback(progress_data)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta=progress_data
        )


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.scrape_website_task")
def scrape_website_task(self, url: str, expected_pages: int = 100, output_format: str = "json", 
                       site_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrape a complete website with progress tracking
    """
    logger.info(f"Starting website scraping task for {url}")
    
    start_time = time.time()
    
    try:
        # Progress callback function
        def update_progress(progress_data):
            self.update_progress({
                **progress_data,
                'task_id': self.request.id,
                'url': url,
                'start_time': start_time
            })
        
        # Initialize scraper with progress callback
        scraper = UniversalScraper(
            base_url=url, 
            expected_pages=expected_pages, 
            progress_callback=update_progress
        )
        
        # Update initial progress
        update_progress({
            'progress': 0.0,
            'pages_scraped': 0,
            'total_pages': expected_pages,
            'current_page': 'Initializing scraper...',
            'message': 'Starting scrape job...'
        })
        
        # Scrape the site
        data = scraper.scrape_site()
        
        # Save data
        saved_files = scraper.scrape_and_save(output_format)
        
        # Get stats
        stats = scraper.get_optimization_stats()
        
        # Optimize data for RAG
        optimized_data = scraper.optimize_data_for_rag(data)
        
        # Add to RAG system if available
        rag_system = get_rag_system()
        if rag_system and optimized_data:
            try:
                update_progress({
                    'progress': 95.0,
                    'pages_scraped': len(data),
                    'total_pages': expected_pages,
                    'current_page': 'Adding to RAG system...',
                    'message': 'Processing data for RAG...'
                })
                
                # Extract site name if not provided
                if not site_name:
                    site_name = urlparse(url).netloc
                
                rag_system.add_documents(optimized_data, site_name=site_name)
                logger.info(f"Added {len(optimized_data)} documents to RAG system for site {site_name}")
            except Exception as e:
                logger.error(f"Error adding documents to RAG: {e}")
        
        # Final progress update
        update_progress({
            'progress': 100.0,
            'pages_scraped': len(data),
            'total_pages': expected_pages,
            'current_page': 'Completed',
            'message': f'Successfully scraped {len(data)} pages'
        })
        
        end_time = time.time()
        
        result = {
            'status': 'completed',
            'url': url,
            'pages_scraped': len(data),
            'total_pages': expected_pages,
            'files': saved_files,
            'stats': stats,
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,
            'data': optimized_data[:10],  # Return first 10 pages for preview
            'message': f'Successfully scraped {len(data)} pages from {url}'
        }
        
        logger.info(f"Website scraping task completed for {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error in website scraping task for {url}: {e}")
        
        # Update failed progress
        self.update_progress({
            'progress': 0.0,
            'pages_scraped': 0,
            'total_pages': expected_pages,
            'current_page': 'Failed',
            'message': f'Scraping failed: {str(e)}',
            'task_id': self.request.id,
            'url': url,
            'start_time': start_time
        })
        
        raise self.retry(countdown=60, max_retries=3, exc=e)


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.scrape_business_task")
def scrape_business_task(self, url: str, pages_to_scrape: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Scrape specific business-related pages (about, contact, terms, etc.)
    """
    logger.info(f"Starting business scraping task for {url}")
    
    start_time = time.time()
    
    try:
        # Default business pages to scrape
        if not pages_to_scrape:
            pages_to_scrape = [
                '/',  # Homepage
                '/about',
                '/about-us', 
                '/contact',
                '/contact-us',
                '/terms',
                '/terms-of-service',
                '/privacy',
                '/privacy-policy',
                '/company',
                '/our-company',
                '/mission',
                '/vision',
                '/team',
                '/leadership',
                '/careers',
                '/jobs'
            ]
        
        # Progress callback function
        def update_progress(progress_data):
            self.update_progress({
                **progress_data,
                'task_id': self.request.id,
                'url': url,
                'start_time': start_time,
                'task_type': 'business_scrape'
            })
        
        # Update initial progress
        update_progress({
            'progress': 0.0,
            'pages_scraped': 0,
            'total_pages': len(pages_to_scrape),
            'current_page': 'Initializing business scraper...',
            'message': 'Starting business page scraping...'
        })
        
        # Initialize scraper
        scraper = UniversalScraper(
            base_url=url,
            expected_pages=len(pages_to_scrape),
            progress_callback=update_progress
        )
        
        # Build full URLs for business pages
        business_urls = []
        for page in pages_to_scrape:
            if page.startswith('http'):
                business_urls.append(page)
            else:
                business_urls.append(urljoin(url, page))
        
        # Scrape each business page
        scraped_data = []
        failed_urls = []
        
        for i, business_url in enumerate(business_urls):
            try:
                update_progress({
                    'progress': (i / len(business_urls)) * 90,  # Reserve 10% for final processing
                    'pages_scraped': i,
                    'total_pages': len(business_urls),
                    'current_page': business_url,
                    'message': f'Scraping business page {i+1} of {len(business_urls)}'
                })
                
                # Get page content
                content = scraper.get_page_content_advanced(business_url, worker_id=0)
                
                if content:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    page_data = scraper.extract_page_data_advanced(soup, business_url)
                    
                    # Add business page classification
                    page_data['page_type'] = _classify_business_page(business_url, page_data)
                    page_data['business_relevance'] = _calculate_business_relevance(page_data)
                    
                    scraped_data.append(page_data)
                    logger.info(f"Successfully scraped business page: {business_url}")
                else:
                    failed_urls.append(business_url)
                    logger.warning(f"Failed to scrape business page: {business_url}")
                
            except Exception as e:
                logger.error(f"Error scraping business page {business_url}: {e}")
                failed_urls.append(business_url)
        
        # Optimize data for RAG
        optimized_data = scraper.optimize_data_for_rag(scraped_data)
        
        # Add business-specific metadata
        for page in optimized_data:
            page['scrape_type'] = 'business'
            page['business_context'] = True
        
        # Add to RAG system with business context
        rag_system = get_rag_system()
        if rag_system and optimized_data:
            try:
                update_progress({
                    'progress': 95.0,
                    'pages_scraped': len(scraped_data),
                    'total_pages': len(business_urls),
                    'current_page': 'Adding to RAG system...',
                    'message': 'Processing business data for RAG...'
                })
                
                site_name = urlparse(url).netloc
                rag_system.add_documents(optimized_data, site_name=f"{site_name}_business")
                logger.info(f"Added {len(optimized_data)} business documents to RAG system")
            except Exception as e:
                logger.error(f"Error adding business documents to RAG: {e}")
        
        # Final progress update
        update_progress({
            'progress': 100.0,
            'pages_scraped': len(scraped_data),
            'total_pages': len(business_urls),
            'current_page': 'Completed',
            'message': f'Successfully scraped {len(scraped_data)} business pages'
        })
        
        end_time = time.time()
        
        # Generate business insights
        business_insights = _generate_business_insights(optimized_data)
        
        result = {
            'status': 'completed',
            'url': url,
            'pages_scraped': len(scraped_data),
            'total_pages': len(business_urls),
            'successful_pages': len(scraped_data),
            'failed_pages': len(failed_urls),
            'failed_urls': failed_urls,
            'business_insights': business_insights,
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,
            'data': optimized_data,
            'message': f'Successfully scraped {len(scraped_data)} business pages from {url}'
        }
        
        logger.info(f"Business scraping task completed for {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error in business scraping task for {url}: {e}")
        raise self.retry(countdown=60, max_retries=3, exc=e)


@celery_app.task(bind=True, name="src.tasks.process_rag_task")
def process_rag_task(self, documents: List[Dict[str, Any]], site_name: str) -> Dict[str, Any]:
    """
    Process documents and add them to RAG system
    """
    logger.info(f"Starting RAG processing task for {len(documents)} documents")
    
    try:
        rag_system = get_rag_system()
        if not rag_system:
            raise Exception("RAG system not available")
        
        # Add documents to RAG
        rag_system.add_documents(documents, site_name=site_name)
        
        # Get site stats
        stats = rag_system.get_site_stats(site_name)
        
        result = {
            'status': 'completed',
            'site_name': site_name,
            'documents_processed': len(documents),
            'site_stats': stats,
            'message': f'Successfully processed {len(documents)} documents for {site_name}'
        }
        
        logger.info(f"RAG processing task completed for {site_name}")
        return result
        
    except Exception as e:
        logger.error(f"Error in RAG processing task: {e}")
        raise self.retry(countdown=30, max_retries=3, exc=e)


@celery_app.task(bind=True, name="src.tasks.query_business_insights")
def query_business_insights(self, site_name: str, questions: List[str]) -> Dict[str, Any]:
    """
    Query business insights using RAG system
    """
    logger.info(f"Querying business insights for {site_name}")
    
    try:
        rag_system = get_rag_system()
        if not rag_system:
            raise Exception("RAG system not available")
        
        insights = {}
        
        for question in questions:
            try:
                answer = rag_system.query_site_specific(question, f"{site_name}_business", n_results=5)
                context = rag_system.get_relevant_context(question, 5, f"{site_name}_business")
                
                insights[question] = {
                    'answer': answer,
                    'context': context,
                    'confidence': _calculate_answer_confidence(answer, context)
                }
            except Exception as e:
                logger.error(f"Error querying '{question}': {e}")
                insights[question] = {
                    'answer': f"Error generating answer: {str(e)}",
                    'context': [],
                    'confidence': 0.0
                }
        
        result = {
            'status': 'completed',
            'site_name': site_name,
            'insights': insights,
            'total_questions': len(questions),
            'answered_questions': len([q for q in insights.values() if not q['answer'].startswith('Error')])
        }
        
        logger.info(f"Business insights query completed for {site_name}")
        return result
        
    except Exception as e:
        logger.error(f"Error in business insights query: {e}")
        raise self.retry(countdown=30, max_retries=3, exc=e)


def _classify_business_page(url: str, page_data: Dict[str, Any]) -> str:
    """Classify the type of business page"""
    url_lower = url.lower()
    content_lower = page_data.get('content', '').lower()
    title_lower = page_data.get('title', '').lower()
    
    # Homepage
    if url.endswith('/') or 'home' in url_lower:
        return 'homepage'
    
    # About pages
    if any(word in url_lower for word in ['about', 'company', 'mission', 'vision']):
        return 'about'
    
    # Contact pages
    if any(word in url_lower for word in ['contact', 'reach', 'location']):
        return 'contact'
    
    # Terms and policies
    if any(word in url_lower for word in ['terms', 'privacy', 'policy', 'legal']):
        return 'legal'
    
    # Team and careers
    if any(word in url_lower for word in ['team', 'careers', 'jobs', 'leadership']):
        return 'team'
    
    # Services or products
    if any(word in url_lower for word in ['service', 'product', 'offering']):
        return 'services'
    
    return 'general'


def _calculate_business_relevance(page_data: Dict[str, Any]) -> float:
    """Calculate how relevant a page is for business insights"""
    content = page_data.get('content', '').lower()
    title = page_data.get('title', '').lower()
    
    business_keywords = [
        'company', 'business', 'about', 'mission', 'vision', 'values',
        'team', 'leadership', 'management', 'founder', 'ceo', 'executive',
        'contact', 'address', 'phone', 'email', 'location', 'office',
        'service', 'product', 'offering', 'solution', 'expertise',
        'history', 'established', 'founded', 'experience', 'years',
        'industry', 'market', 'client', 'customer', 'partner'
    ]
    
    score = 0.0
    total_words = len(content.split())
    
    if total_words == 0:
        return 0.0
    
    for keyword in business_keywords:
        count = content.count(keyword) + title.count(keyword) * 2  # Title words weight more
        score += count
    
    # Normalize by content length
    relevance = min(score / total_words * 100, 1.0)
    return relevance


def _generate_business_insights(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate business insights from scraped data"""
    insights = {
        'page_types': {},
        'total_pages': len(data),
        'avg_relevance': 0.0,
        'key_sections': [],
        'contact_info': {},
        'business_focus': []
    }
    
    total_relevance = 0.0
    
    for page in data:
        page_type = page.get('page_type', 'general')
        insights['page_types'][page_type] = insights['page_types'].get(page_type, 0) + 1
        
        relevance = page.get('business_relevance', 0.0)
        total_relevance += relevance
        
        # Extract contact information
        if page_type == 'contact':
            content = page.get('content', '')
            contact_info = _extract_contact_info_from_content(content)
            insights['contact_info'].update(contact_info)
    
    if len(data) > 0:
        insights['avg_relevance'] = total_relevance / len(data)
    
    return insights


def _extract_contact_info_from_content(content: str) -> Dict[str, str]:
    """Extract contact information from content"""
    import re
    
    contact_info = {}
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, content)
    if emails:
        contact_info['email'] = emails[0]
    
    # Phone pattern
    phone_pattern = r'[\+]?[1-9]?[0-9]{7,15}'
    phones = re.findall(phone_pattern, content)
    if phones:
        contact_info['phone'] = phones[0]
    
    # Address pattern (basic)
    address_keywords = ['address', 'location', 'office', 'headquarters']
    for keyword in address_keywords:
        if keyword in content.lower():
            # Try to extract text around the keyword
            start = content.lower().find(keyword)
            if start != -1:
                # Get surrounding text
                address_text = content[start:start+200]
                contact_info['address'] = address_text.strip()
                break
    
    return contact_info


def _calculate_answer_confidence(answer: str, context: List[Dict[str, Any]]) -> float:
    """Calculate confidence score for RAG answer"""
    if not answer or answer.startswith('Error'):
        return 0.0
    
    if not context:
        return 0.2
    
    # Simple confidence calculation based on context relevance
    confidence = min(len(context) / 5.0, 1.0)  # Max confidence with 5+ context items
    
    # Boost confidence if answer is detailed
    if len(answer) > 100:
        confidence += 0.1
    
    # Reduce confidence if answer mentions no information available
    if 'not available' in answer.lower() or 'no information' in answer.lower():
        confidence *= 0.5
    
    return min(confidence, 1.0)


# Task monitoring signals
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Task started handler"""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect  
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Task completed handler"""
    logger.info(f"Task {task.name} [{task_id}] completed with state: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Task failed handler"""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")

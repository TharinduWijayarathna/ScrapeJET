import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from loguru import logger
from urllib.parse import urlparse

# Disable telemetry for sentence-transformers and huggingface
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/sentence_transformers"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


class VectorStore:
    """Vector store for storing and searching scraped documents with site-wise organization"""
    
    def __init__(self, persist_directory: str = "data/vectorstore"):
        """Initialize vector store"""
        try:
            os.makedirs(persist_directory, exist_ok=True)
            os.chmod(persist_directory, 0o755)
        except PermissionError:
            logger.warning(f"Permission denied for {persist_directory}, using fallback directory")
            persist_directory = "/tmp/vectorstore"
            os.makedirs(persist_directory, exist_ok=True)
        
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Track content hashes to prevent duplicates per site
        self._content_hashes: Dict[str, Set[str]] = {}
        
        # Track available sites
        self._available_sites = self._discover_sites()
        
        logger.info(f"Vector store initialized at {persist_directory}")
        logger.info(f"Available sites: {list(self._available_sites.keys())}")
    
    def _discover_sites(self) -> Dict[str, str]:
        """Discover existing site collections"""
        sites = {}
        try:
            collections = self.client.list_collections()
            for collection in collections:
                if collection.name.startswith("site_"):
                    site_name = collection.name.replace("site_", "")
                    sites[site_name] = collection.name
        except Exception as e:
            logger.warning(f"Error discovering sites: {e}")
        return sites
    
    def _get_site_name(self, url: str) -> str:
        """Extract site name from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            # Fallback: use URL as site name
            return url.replace("://", "_").replace("/", "_").replace(".", "_")
    
    def _get_or_create_site_collection(self, site_name: str):
        """Get or create collection for a specific site"""
        collection_name = f"site_{site_name}"
        
        if collection_name not in self._available_sites:
            try:
                collection = self.client.get_collection(collection_name)
                self._available_sites[site_name] = collection_name
            except:
                collection = self.client.create_collection(collection_name)
                self._available_sites[site_name] = collection_name
                self._content_hashes[site_name] = set()
        else:
            collection = self.client.get_collection(collection_name)
        
        return collection
    
    def add_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 1000, site_name: Optional[str] = None):
        """Add documents to the vector store with site-wise organization"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        # Group documents by site if site_name not provided
        if site_name is None:
            site_groups = {}
            for doc in documents:
                doc_site = self._get_site_name(doc.get('url', ''))
                if doc_site not in site_groups:
                    site_groups[doc_site] = []
                site_groups[doc_site].append(doc)
            
            # Add documents for each site
            for site, site_docs in site_groups.items():
                self._add_documents_for_site(site_docs, site, chunk_size)
        else:
            self._add_documents_for_site(documents, site_name, chunk_size)
    
    def _add_documents_for_site(self, documents: List[Dict[str, Any]], site_name: str, chunk_size: int):
        """Add documents for a specific site"""
        # Get or create collection for this site
        collection = self._get_or_create_site_collection(site_name)
        
        # Initialize content hashes for this site if not exists
        if site_name not in self._content_hashes:
            self._content_hashes[site_name] = set()
        
        # Process documents into chunks with deduplication
        chunks = self._chunk_documents_optimized(documents, chunk_size, site_name)
        
        if not chunks:
            logger.warning(f"No unique chunks to add for site {site_name}")
            return
        
        # Prepare data for ChromaDB
        ids = []
        texts = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{site_name}_chunk_{i}"
            ids.append(chunk_id)
            texts.append(chunk['text'])
            metadatas.append(chunk['metadata'])
        
        # Add to collection
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(chunks)} unique chunks to vector store for site {site_name}")
    
    def _chunk_documents(self, documents: List[Dict[str, Any]], chunk_size: int) -> List[Dict[str, Any]]:
        """Split documents into chunks"""
        chunks = []
        
        for doc in documents:
            # Extract text content
            text_parts = []
            
            if 'title' in doc and doc['title']:
                text_parts.append(f"Title: {doc['title']}")
            
            if 'description' in doc and doc['description']:
                text_parts.append(f"Description: {doc['description']}")
            
            if 'content' in doc and doc['content']:
                text_parts.append(doc['content'])
            
            # Add product information if available
            if 'products' in doc and doc['products']:
                for product in doc['products']:
                    product_text = []
                    if 'name' in product:
                        product_text.append(f"Product: {product['name']}")
                    if 'price' in product:
                        product_text.append(f"Price: {product['price']}")
                    if 'description' in product:
                        product_text.append(f"Description: {product['description']}")
                    text_parts.append(" | ".join(product_text))
            
            # Add contact information if available
            if 'contact_info' in doc and doc['contact_info']:
                contact_text = []
                for key, value in doc['contact_info'].items():
                    if isinstance(value, list):
                        contact_text.append(f"{key}: {', '.join(value)}")
                    else:
                        contact_text.append(f"{key}: {value}")
                text_parts.append("Contact: " + " | ".join(contact_text))
            
            # Combine all text
            full_text = " ".join(text_parts)
            
            # Split into chunks
            words = full_text.split()
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if chunk_text.strip():
                    chunks.append({
                        'text': chunk_text,
                        'metadata': {
                            'url': doc.get('url', ''),
                            'title': doc.get('title', ''),
                            'chunk_index': i // chunk_size,
                            'total_chunks': (len(words) + chunk_size - 1) // chunk_size
                        }
                    })
        
        return chunks
    
    def _chunk_documents_optimized(self, documents: List[Dict[str, Any]], chunk_size: int, site_name: str) -> List[Dict[str, Any]]:
        """Split documents into chunks with deduplication and optimization"""
        chunks = []
        seen_hashes = self._content_hashes.get(site_name, set())
        
        for doc in documents:
            # Extract and optimize text content
            text_parts = self._extract_optimized_text(doc)
            
            # Combine all text
            full_text = " ".join(text_parts)
            
            # Skip empty or very short content
            if len(full_text.strip()) < 10:
                continue
            
            # Split into chunks
            words = full_text.split()
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if chunk_text.strip():
                    # Create hash for deduplication
                    chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()
                    
                    # Skip if we've seen this content before
                    if chunk_hash in seen_hashes:
                        continue
                    
                    seen_hashes.add(chunk_hash)
                    
                    chunks.append({
                        'text': chunk_text,
                        'metadata': {
                            'url': doc.get('url', ''),
                            'title': doc.get('title', ''),
                            'chunk_index': i // chunk_size,
                            'total_chunks': (len(words) + chunk_size - 1) // chunk_size,
                            'content_hash': chunk_hash,
                            'site_name': site_name
                        }
                    })
        
        # Update content hashes for this site
        self._content_hashes[site_name] = seen_hashes
        
        return chunks
    
    def _extract_optimized_text(self, doc: Dict[str, Any]) -> List[str]:
        """Extract text content with deduplication and optimization"""
        text_parts = []
        
        # Add title (only if different from content)
        if 'title' in doc and doc['title']:
            text_parts.append(f"Title: {doc['title']}")
        
        # Add description (only if different from title and content)
        if 'description' in doc and doc['description']:
            desc = doc['description']
            if desc != doc.get('title', '') and len(desc) > 20:  # Avoid very short descriptions
                text_parts.append(f"Description: {desc}")
        
        # Add main content (cleaned)
        if 'content' in doc and doc['content']:
            content = self._clean_content(doc['content'])
            if content and content != doc.get('title', ''):
                text_parts.append(content)
        
        # Add product information (deduplicated)
        if 'products' in doc and doc['products']:
            unique_products = self._deduplicate_products(doc['products'])
            for product in unique_products:
                product_text = []
                if 'name' in product:
                    product_text.append(f"Product: {product['name']}")
                if 'price' in product:
                    product_text.append(f"Price: {product['price']}")
                if 'description' in product and product['description'] != product.get('name', ''):
                    product_text.append(f"Description: {product['description']}")
                
                if product_text:
                    text_parts.append(" | ".join(product_text))
        
        # Add contact information (only once per unique contact)
        if 'contact_info' in doc and doc['contact_info']:
            contact_text = self._extract_unique_contacts(doc['contact_info'])
            if contact_text:
                text_parts.append("Contact: " + " | ".join(contact_text))
        
        return text_parts
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = ' '.join(content.split())
        
        # Remove common boilerplate
        boilerplate_phrases = [
            'cookie policy', 'privacy policy', 'terms of service',
            'all rights reserved', 'copyright', 'powered by',
            'loading...', 'please wait', 'javascript required'
        ]
        
        for phrase in boilerplate_phrases:
            content = content.replace(phrase, '')
        
        return content.strip()
    
    def _deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products based on name and price"""
        seen_products = set()
        unique_products = []
        
        for product in products:
            name = product.get('name', '').strip()
            price = product.get('price', '').strip()
            
            if name and price:
                product_key = f"{name}|{price}"
                if product_key not in seen_products:
                    seen_products.add(product_key)
                    unique_products.append(product)
        
        return unique_products
    
    def _extract_unique_contacts(self, contact_info: Dict[str, Any]) -> List[str]:
        """Extract unique contact information"""
        unique_contacts = []
        seen_contacts = set()
        
        for key, value in contact_info.items():
            if isinstance(value, list):
                for item in value:
                    contact_text = f"{key}: {item}"
                    if contact_text not in seen_contacts:
                        seen_contacts.add(contact_text)
                        unique_contacts.append(contact_text)
            elif value:
                contact_text = f"{key}: {value}"
                if contact_text not in seen_contacts:
                    seen_contacts.add(contact_text)
                    unique_contacts.append(contact_text)
        
        return unique_contacts
    
    def search(self, query: str, n_results: int = 5, site_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar documents, optionally within a specific site"""
        if site_name:
            # Search within specific site
            if site_name not in self._available_sites:
                logger.warning(f"Site {site_name} not found")
                return []
            
            collection = self.client.get_collection(self._available_sites[site_name])
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
        else:
            # Search across all sites
            all_results = []
            for site_name, collection_name in self._available_sites.items():
                try:
                    collection = self.client.get_collection(collection_name)
                    site_results = collection.query(
                        query_texts=[query],
                        n_results=n_results
                    )
                    
                    # Add site information to results
                    for i in range(len(site_results['documents'][0])):
                        all_results.append({
                            'text': site_results['documents'][0][i],
                            'metadata': {**site_results['metadatas'][0][i], 'site_name': site_name},
                            'distance': site_results['distances'][0][i] if 'distances' in site_results else None
                        })
                except Exception as e:
                    logger.warning(f"Error searching site {site_name}: {e}")
            
            # Sort by distance and return top results
            all_results.sort(key=lambda x: x.get('distance', float('inf')))
            return all_results[:n_results]
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def search_site_specific(self, query: str, site_name: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for documents within a specific site"""
        return self.search(query, n_results, site_name)
    
    def get_sites(self) -> List[str]:
        """Get list of available sites"""
        return list(self._available_sites.keys())
    
    def get_site_stats(self, site_name: str) -> Dict[str, Any]:
        """Get statistics for a specific site"""
        if site_name not in self._available_sites:
            return {'error': f'Site {site_name} not found'}
        
        try:
            collection = self.client.get_collection(self._available_sites[site_name])
            results = collection.get()
            
            total_chunks = len(results['documents'])
            unique_hashes = set()
            
            for metadata in results['metadatas']:
                if 'content_hash' in metadata:
                    unique_hashes.add(metadata['content_hash'])
            
            return {
                'site_name': site_name,
                'total_chunks': total_chunks,
                'unique_chunks': len(unique_hashes),
                'duplicate_chunks': total_chunks - len(unique_hashes),
                'deduplication_ratio': round((total_chunks - len(unique_hashes)) / max(total_chunks, 1) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error getting stats for site {site_name}: {e}")
            return {'error': str(e)}
    
    def get_all_sites_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all sites"""
        stats = {}
        for site_name in self._available_sites:
            stats[site_name] = self.get_site_stats(site_name)
        return stats
    
    def get_all_documents(self, site_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all documents from the vector store, optionally for a specific site"""
        if site_name:
            if site_name not in self._available_sites:
                return []
            
            collection = self.client.get_collection(self._available_sites[site_name])
            results = collection.get()
        else:
            # Get from all sites
            all_results = []
            for site_name, collection_name in self._available_sites.items():
                try:
                    collection = self.client.get_collection(collection_name)
                    site_results = collection.get()
                    
                    for i in range(len(site_results['documents'])):
                        all_results.append({
                            'text': site_results['documents'][i],
                            'metadata': {**site_results['metadatas'][i], 'site_name': site_name},
                            'id': site_results['ids'][i]
                        })
                except Exception as e:
                    logger.warning(f"Error getting documents from site {site_name}: {e}")
            
            return all_results
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'])):
            formatted_results.append({
                'text': results['documents'][i],
                'metadata': results['metadatas'][i],
                'id': results['ids'][i]
            })
        
        return formatted_results
    
    def clear_site(self, site_name: str):
        """Clear all documents for a specific site"""
        if site_name in self._available_sites:
            collection_name = self._available_sites[site_name]
            self.client.delete_collection(collection_name)
            del self._available_sites[site_name]
            if site_name in self._content_hashes:
                del self._content_hashes[site_name]
            logger.info(f"Cleared vector store for site {site_name}")
        else:
            logger.warning(f"Site {site_name} not found")
    
    def clear(self):
        """Clear all documents from all sites"""
        for site_name in list(self._available_sites.keys()):
            self.clear_site(site_name)
        logger.info("All vector stores cleared")

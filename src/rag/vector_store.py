import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from loguru import logger

# Disable telemetry for sentence-transformers and huggingface
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/sentence_transformers"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


class VectorStore:
    """Vector store for storing and searching scraped documents"""
    
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
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection("scraped_data")
        except:
            self.collection = self.client.create_collection("scraped_data")
        
        # Track content hashes to prevent duplicates
        self._content_hashes: Set[str] = set()
        
        logger.info(f"Vector store initialized at {persist_directory}")
    
    def add_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 1000):
        """Add documents to the vector store with deduplication"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        # Process documents into chunks with deduplication
        chunks = self._chunk_documents_optimized(documents, chunk_size)
        
        if not chunks:
            logger.warning("No unique chunks to add after deduplication")
            return
        
        # Prepare data for ChromaDB
        ids = []
        texts = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            ids.append(chunk_id)
            texts.append(chunk['text'])
            metadatas.append(chunk['metadata'])
        
        # Add to collection
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(chunks)} unique chunks to vector store")
    
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
    
    def _chunk_documents_optimized(self, documents: List[Dict[str, Any]], chunk_size: int) -> List[Dict[str, Any]]:
        """Split documents into chunks with deduplication and optimization"""
        chunks = []
        seen_hashes = set()
        
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
                            'content_hash': chunk_hash
                        }
                    })
        
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
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get statistics about data optimization"""
        try:
            all_docs = self.get_all_documents()
            
            # Count unique content hashes
            unique_hashes = set()
            total_chunks = 0
            
            for doc in all_docs:
                metadata = doc.get('metadata', {})
                if 'content_hash' in metadata:
                    unique_hashes.add(metadata['content_hash'])
                total_chunks += 1
            
            # Calculate deduplication ratio
            dedup_ratio = 0
            if total_chunks > 0:
                dedup_ratio = (total_chunks - len(unique_hashes)) / total_chunks * 100
            
            return {
                'total_chunks': total_chunks,
                'unique_chunks': len(unique_hashes),
                'duplicate_chunks': total_chunks - len(unique_hashes),
                'deduplication_ratio': round(dedup_ratio, 2),
                'storage_efficiency': round(len(unique_hashes) / max(total_chunks, 1) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error getting optimization stats: {e}")
            return {
                'total_chunks': 0,
                'unique_chunks': 0,
                'duplicate_chunks': 0,
                'deduplication_ratio': 0,
                'storage_efficiency': 0
            }
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from the vector store"""
        results = self.collection.get()
        
        formatted_results = []
        for i in range(len(results['documents'])):
            formatted_results.append({
                'text': results['documents'][i],
                'metadata': results['metadatas'][i],
                'id': results['ids'][i]
            })
        
        return formatted_results
    
    def clear(self):
        """Clear all documents from the vector store"""
        self.client.delete_collection("scraped_data")
        self.collection = self.client.create_collection(
            name="scraped_data",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Vector store cleared")

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from loguru import logger

# Disable telemetry for sentence-transformers and huggingface
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/sentence_transformers"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


class VectorStore:
    """Vector store for RAG functionality"""
    
    def __init__(self, persist_directory: str = "data/vectorstore"):
        self.persist_directory = Path(persist_directory)
        # Ensure the directory exists and is writable
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            # Set proper permissions for the directory
            os.chmod(self.persist_directory, 0o755)
        except PermissionError as e:
            logger.warning(f"Permission issue with {self.persist_directory}: {e}")
            # Try to use a fallback directory
            fallback_dir = Path("/tmp/vectorstore")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.persist_directory = fallback_dir
            logger.info(f"Using fallback directory: {self.persist_directory}")
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize sentence transformer
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="scraped_data",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Vector store initialized at {self.persist_directory}")
    
    def add_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 1000):
        """Add documents to the vector store"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        # Process documents into chunks
        chunks = self._chunk_documents(documents, chunk_size)
        
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
        
        logger.info(f"Added {len(chunks)} chunks to vector store")
    
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

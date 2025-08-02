import os
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import boto3
from openai import OpenAI
from loguru import logger
import json


class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""
    
    @abstractmethod
    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate a response based on query and context"""
        pass


class OpenAIInterface(LLMInterface):
    """OpenAI GPT interface"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"OpenAI interface initialized with model: {model}")
    
    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate response using OpenAI"""
        # Prepare context
        context_text = self._prepare_context(context)
        
        # Create prompt
        prompt = f"""Based on the following scraped website data, please answer the user's question.

Context from scraped website:
{context_text}

User Question: {query}

Please provide a comprehensive answer based on the scraped data. If the information is not available in the context, please state that clearly."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes scraped website data and provides insights based on the available information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return f"Error generating response: {str(e)}"
    
    def _prepare_context(self, context: List[Dict[str, Any]]) -> str:
        """Prepare context for the LLM"""
        context_parts = []
        
        for item in context:
            text = item.get('text', '')
            metadata = item.get('metadata', {})
            
            # Add metadata information
            if metadata.get('title'):
                text = f"Title: {metadata['title']}\n{text}"
            
            if metadata.get('url'):
                text = f"URL: {metadata['url']}\n{text}"
            
            context_parts.append(text)
        
        return "\n\n---\n\n".join(context_parts)


class BedrockInterface(LLMInterface):
    """AWS Bedrock interface"""
    
    def __init__(self, model_id: str = "anthropic.claude-v2", region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region)
        
        logger.info(f"Bedrock interface initialized with model: {model_id}")
    
    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate response using AWS Bedrock"""
        # Prepare context
        context_text = self._prepare_context(context)
        
        # Create prompt
        prompt = f"""Based on the following scraped website data, please answer the user's question.

Context from scraped website:
{context_text}

User Question: {query}

Please provide a comprehensive answer based on the scraped data. If the information is not available in the context, please state that clearly."""

        try:
            if "claude" in self.model_id.lower():
                return self._call_claude(prompt)
            elif "titan" in self.model_id.lower():
                return self._call_titan(prompt)
            else:
                return self._call_claude(prompt)  # Default to Claude
        except Exception as e:
            logger.error(f"Error generating Bedrock response: {e}")
            return f"Error generating response: {str(e)}"
    
    def _call_claude(self, prompt: str) -> str:
        """Call Claude model"""
        body = {
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 1000,
            "temperature": 0.7,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman:"]
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('completion', '')
    
    def _call_titan(self, prompt: str) -> str:
        """Call Titan model"""
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1000,
                "temperature": 0.7,
                "topP": 1
            }
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('results', [{}])[0].get('outputText', '')
    
    def _prepare_context(self, context: List[Dict[str, Any]]) -> str:
        """Prepare context for the LLM"""
        context_parts = []
        
        for item in context:
            text = item.get('text', '')
            metadata = item.get('metadata', {})
            
            # Add metadata information
            if metadata.get('title'):
                text = f"Title: {metadata['title']}\n{text}"
            
            if metadata.get('url'):
                text = f"URL: {metadata['url']}\n{text}"
            
            context_parts.append(text)
        
        return "\n\n---\n\n".join(context_parts)


class RAGSystem:
    """Complete RAG system combining vector store and LLM with site-wise organization"""
    
    def __init__(self, vector_store, llm_interface):
        self.vector_store = vector_store
        self.llm_interface = llm_interface
        
        logger.info("RAG system initialized")
    
    def add_documents(self, documents: List[Dict[str, Any]], site_name: Optional[str] = None):
        """Add documents to the vector store with optional site specification"""
        self.vector_store.add_documents(documents, site_name=site_name)
    
    def query(self, question: str, n_results: int = 5, site_name: Optional[str] = None) -> str:
        """Query the RAG system, optionally within a specific site"""
        # Search for relevant documents
        search_results = self.vector_store.search(question, n_results, site_name)
        
        if not search_results:
            if site_name:
                return f"No relevant information found in the scraped data for site '{site_name}'."
            else:
                return "No relevant information found in the scraped data."
        
        # Generate response using LLM
        response = self.llm_interface.generate_response(question, search_results)
        
        return response
    
    def query_site_specific(self, question: str, site_name: str, n_results: int = 5) -> str:
        """Query the RAG system for a specific site"""
        return self.query(question, n_results, site_name)
    
    def get_relevant_context(self, question: str, n_results: int = 5, site_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relevant context without generating a response"""
        return self.vector_store.search(question, n_results, site_name)
    
    def get_sites(self) -> List[str]:
        """Get list of available sites"""
        return self.vector_store.get_sites()
    
    def get_site_stats(self, site_name: str) -> Dict[str, Any]:
        """Get statistics for a specific site"""
        return self.vector_store.get_site_stats(site_name)
    
    def get_all_sites_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all sites"""
        return self.vector_store.get_all_sites_stats()
    
    def clear_site(self, site_name: str):
        """Clear all documents for a specific site"""
        self.vector_store.clear_site(site_name)
    
    def clear_all(self):
        """Clear all documents from all sites"""
        self.vector_store.clear() 
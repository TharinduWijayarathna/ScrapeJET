import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import openai
import boto3
import time
import hashlib

logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""
    
    @abstractmethod
    def generate_response(self, query: str, context: List[Dict[str, Any]], conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        pass

class OpenAIInterface(LLMInterface):
    """OpenAI interface with improved prompt engineering"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.model = model
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"OpenAI interface initialized with model: {model}")
    
    def generate_response(self, query: str, context: List[Dict[str, Any]], conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using OpenAI with improved prompt engineering"""
        # Prepare context with better filtering
        context_text = self._prepare_context_advanced(context, query)
        
        # Build conversation history
        messages = self._build_conversation_messages(query, context_text, conversation_history)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more consistent responses
                top_p=0.9,
                frequency_penalty=0.1,  # Reduce repetition
                presence_penalty=0.1    # Encourage diverse responses
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return f"Error generating response: {str(e)}"
    
    def _build_conversation_messages(self, query: str, context_text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """Build conversation messages with context and history"""
        messages = [
            {
                "role": "system", 
                "content": """You are a precise web scraping analyst. Your CRITICAL rules:

1. **ONLY use the provided context data** - NEVER invent or generate information not present in the context
2. **Be extremely specific** - reference exact text, URLs, and data points from the context
3. **If information is not in the context, explicitly state "This information is not available in the scraped data"**
4. **Quote directly from the context** when possible to show the exact data
5. **Avoid generic responses** - focus on the specific content that was actually scraped
6. **Structure responses clearly** with bullet points and specific references

IMPORTANT: The context contains the actual scraped website data. You must base your response ONLY on this data. Do not make assumptions or generate fictional information."""
            }
        ]
        
        # Add conversation history if available
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                messages.append(msg)
        
        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"""Based ONLY on the following scraped website data, answer this question: "{query}"

**ACTUAL SCRAPED DATA (use only this information):**
{context_text}

**CRITICAL INSTRUCTIONS:**
- Answer using ONLY the information provided in the scraped data above
- If the information is not in the data, say "This information is not available in the scraped data"
- Be specific and reference exact text from the data
- Do not invent or assume any information not present in the data"""
        })
        
        return messages
    
    def _prepare_context_advanced(self, context: List[Dict[str, Any]], query: str) -> str:
        """Prepare context with advanced filtering and relevance scoring"""
        if not context:
            return "No relevant data available."
        
        # For debugging, let's not filter by relevance initially
        # Just format all context items
        context_parts = []
        for item in context:
            text = item.get('text', '')
            metadata = item.get('metadata', {})
            
            # Create structured context entry
            context_entry = []
            
            if metadata.get('title'):
                context_entry.append(f"📄 Title: {metadata['title']}")
            
            if metadata.get('url'):
                context_entry.append(f"🔗 URL: {metadata['url']}")
            
            context_entry.append(f"Content: {text}")
            
            context_parts.append("\n".join(context_entry))
        
        return "\n\n---\n\n".join(context_parts)
    
    def _calculate_relevance_score(self, text: str, metadata: Dict[str, Any], query: str) -> float:
        """Calculate relevance score based on query and content"""
        score = 0.0
        
        # Check for exact keyword matches
        query_words = set(query.split())
        text_words = set(text.lower().split())
        
        # Exact word matches
        exact_matches = len(query_words.intersection(text_words))
        score += exact_matches * 0.3
        
        # Partial word matches
        for query_word in query_words:
            for text_word in text_words:
                if len(query_word) > 3 and (query_word in text_word or text_word in query_word):
                    score += 0.1
        
        # Metadata relevance
        if metadata.get('title'):
            title_lower = metadata['title'].lower()
            for query_word in query_words:
                if query_word in title_lower:
                    score += 0.2
        
        # Content type relevance
        if any(word in query for word in ['product', 'price', 'buy', 'shop']):
            if 'product' in text.lower() or 'price' in text.lower():
                score += 0.3
        
        if any(word in query for word in ['contact', 'email', 'phone', 'address']):
            if any(word in text.lower() for word in ['contact', 'email', 'phone', 'address']):
                score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0

class BedrockInterface(LLMInterface):
    """AWS Bedrock interface with improved prompt engineering"""
    
    def __init__(self, model_id: str = "anthropic.claude-v2", region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region)
        
        logger.info(f"Bedrock interface initialized with model: {model_id}")
    
    def generate_response(self, query: str, context: List[Dict[str, Any]], conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using AWS Bedrock with improved prompt engineering"""
        # Prepare context with advanced filtering
        context_text = self._prepare_context_advanced(context, query)
        
        # Build conversation history
        conversation_context = self._build_conversation_context(conversation_history)
        
        # Create enhanced prompt
        prompt = self._create_enhanced_prompt(query, context_text, conversation_context)
        
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
    
    def _create_enhanced_prompt(self, query: str, context_text: str, conversation_context: str) -> str:
        """Create an enhanced prompt for better responses"""
        return f"""You are a precise web scraping analyst. Your CRITICAL rules:

1. **ONLY use the provided context data** - NEVER invent or generate information not present in the context
2. **Be extremely specific** - reference exact text, URLs, and data points from the context
3. **If information is not in the context, explicitly state "This information is not available in the scraped data"**
4. **Quote directly from the context** when possible to show the exact data
5. **Avoid generic responses** - focus on the specific content that was actually scraped
6. **Structure responses clearly** with bullet points and specific references

IMPORTANT: The context contains the actual scraped website data. You must base your response ONLY on this data. Do not make assumptions or generate fictional information.

**Previous Conversation Context:**
{conversation_context}

**Current Query:** {query}

**ACTUAL SCRAPED DATA (use only this information):**
{context_text}

**CRITICAL INSTRUCTIONS:**
- Answer using ONLY the information provided in the scraped data above
- If the information is not in the data, say "This information is not available in the scraped data"
- Be specific and reference exact text from the data
- Do not invent or assume any information not present in the data
- Quote directly from the context when possible

Please provide your analysis based ONLY on the actual scraped data:"""
    
    def _build_conversation_context(self, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Build conversation context for Bedrock"""
        if not conversation_history:
            return "No previous conversation context."
        
        context_parts = []
        for msg in conversation_history[-4:]:  # Keep last 4 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            context_parts.append(f"{role.title()}: {content}")
        
        return "\n".join(context_parts)
    
    def _prepare_context_advanced(self, context: List[Dict[str, Any]], query: str) -> str:
        """Prepare context with advanced filtering (same as OpenAI)"""
        if not context:
            return "No relevant data available."
        
        # Score and filter context based on query relevance
        scored_context = []
        query_lower = query.lower()
        
        for item in context:
            text = item.get('text', '')
            metadata = item.get('metadata', {})
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(text, metadata, query_lower)
            
            if relevance_score > 0.1:  # Only include relevant items
                scored_context.append({
                    'text': text,
                    'metadata': metadata,
                    'score': relevance_score
                })
        
        # Sort by relevance and take top items
        scored_context.sort(key=lambda x: x['score'], reverse=True)
        top_context = scored_context[:min(8, len(scored_context))]
        
        # Format context
        context_parts = []
        for item in top_context:
            text = item['text']
            metadata = item['metadata']
            
            context_entry = []
            if metadata.get('title'):
                context_entry.append(f"Title: {metadata['title']}")
            if metadata.get('url'):
                context_entry.append(f"URL: {metadata['url']}")
            context_entry.append(f"Content: {text}")
            
            context_parts.append("\n".join(context_entry))
        
        return "\n\n---\n\n".join(context_parts)
    
    def _calculate_relevance_score(self, text: str, metadata: Dict[str, Any], query: str) -> float:
        """Calculate relevance score (same as OpenAI)"""
        score = 0.0
        
        query_words = set(query.split())
        text_words = set(text.lower().split())
        
        exact_matches = len(query_words.intersection(text_words))
        score += exact_matches * 0.3
        
        for query_word in query_words:
            for text_word in text_words:
                if len(query_word) > 3 and (query_word in text_word or text_word in query_word):
                    score += 0.1
        
        if metadata.get('title'):
            title_lower = metadata['title'].lower()
            for query_word in query_words:
                if query_word in title_lower:
                    score += 0.2
        
        if any(word in query for word in ['product', 'price', 'buy', 'shop']):
            if 'product' in text.lower() or 'price' in text.lower():
                score += 0.3
        
        if any(word in query for word in ['contact', 'email', 'phone', 'address']):
            if any(word in text.lower() for word in ['contact', 'email', 'phone', 'address']):
                score += 0.3
        
        return min(score, 1.0)
    
    def _call_claude(self, prompt: str) -> str:
        """Call Claude model with enhanced prompt"""
        body = {
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 1500,
            "temperature": 0.3,
            "top_p": 0.9,
            "stop_sequences": ["\n\nHuman:"]
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('completion', '')
    
    def _call_titan(self, prompt: str) -> str:
        """Call Titan model with enhanced prompt"""
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1500,
                "temperature": 0.3,
                "topP": 0.9
            }
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('results', [{}])[0].get('outputText', '')


class RAGSystem:
    """Enhanced RAG system with conversation tracking and improved precision"""
    
    def __init__(self, vector_store, llm_interface):
        self.vector_store = vector_store
        self.llm_interface = llm_interface
        self.conversation_history = []
        self.query_cache = {}  # Cache for similar queries
        self.response_diversity_tracker = {}  # Track response diversity
        
        logger.info("Enhanced RAG system initialized")
    
    def add_documents(self, documents: List[Dict[str, Any]], site_name: Optional[str] = None):
        """Add documents to the vector store with optional site specification"""
        self.vector_store.add_documents(documents, site_name=site_name)
    
    def query(self, question: str, n_results: int = 5, site_name: Optional[str] = None) -> str:
        """Query the RAG system with enhanced precision and conversation tracking"""
        # Check cache for similar queries
        cache_key = self._generate_cache_key(question, site_name)
        if cache_key in self.query_cache:
            cached_response = self.query_cache[cache_key]
            if self._should_use_cached_response(question, cached_response):
                return cached_response['response']
        
        # Search for relevant documents with enhanced filtering
        search_results = self.vector_store.search(question, n_results * 2, site_name)  # Get more results for filtering
        
        if not search_results:
            if site_name:
                response = f"No relevant information found in the scraped data for site '{site_name}'."
            else:
                response = "No relevant information found in the scraped data."
        else:
            # Filter and enhance search results
            enhanced_results = self._enhance_search_results(search_results, question)
            
            # Generate response using enhanced LLM interface
            response = self.llm_interface.generate_response(
                question, 
                enhanced_results, 
                self.conversation_history
            )
        
        # Update conversation history
        self._update_conversation_history(question, response)
        
        # Cache the response
        self.query_cache[cache_key] = {
            'response': response,
            'timestamp': time.time(),
            'question': question
        }
        
        return response
    
    def query_site_specific(self, question: str, site_name: str, n_results: int = 5) -> str:
        """Query the RAG system for a specific site with enhanced precision"""
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
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.query_cache = {}
        self.response_diversity_tracker = {}
        logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def _generate_cache_key(self, question: str, site_name: Optional[str] = None) -> str:
        """Generate cache key for query caching"""
        key_text = f"{question.lower().strip()}:{site_name or 'all'}"
        return hashlib.md5(key_text.encode()).hexdigest()
    
    def _should_use_cached_response(self, question: str, cached_data: Dict[str, Any]) -> bool:
        """Determine if cached response should be used"""
        current_time = time.time()
        cache_age = current_time - cached_data['timestamp']
        
        # Don't use cache older than 1 hour
        if cache_age > 3600:
            return False
        
        # Check if questions are very similar
        cached_question = cached_data['question']
        similarity = self._calculate_question_similarity(question, cached_question)
        
        return similarity > 0.8  # 80% similarity threshold
    
    def _calculate_question_similarity(self, question1: str, question2: str) -> float:
        """Calculate similarity between two questions"""
        words1 = set(question1.lower().split())
        words2 = set(question2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _enhance_search_results(self, results: List[Dict[str, Any]], question: str) -> List[Dict[str, Any]]:
        """Enhance search results with better filtering and ranking"""
        if not results:
            return []
        
        # Remove duplicates based on content similarity
        unique_results = []
        seen_content = set()
        
        for result in results:
            content_hash = self._generate_content_hash(result['text'])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Re-rank based on question relevance
        scored_results = []
        for result in unique_results:
            score = self._calculate_result_relevance(result, question)
            scored_results.append((score, result))
        
        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results[:5]]
    
    def _generate_content_hash(self, text: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()
    
    def _calculate_result_relevance(self, result: Dict[str, Any], question: str) -> float:
        """Calculate relevance score for a search result"""
        text = result.get('text', '').lower()
        question_lower = question.lower()
        
        score = 0.0
        
        # Exact word matches
        question_words = set(question_lower.split())
        text_words = set(text.split())
        exact_matches = len(question_words.intersection(text_words))
        score += exact_matches * 0.3
        
        # Phrase matches
        for word in question_words:
            if len(word) > 3 and word in text:
                score += 0.2
        
        # Metadata relevance
        metadata = result.get('metadata', {})
        if metadata.get('title'):
            title_lower = metadata['title'].lower()
            for word in question_words:
                if word in title_lower:
                    score += 0.2
        
        return min(score, 1.0)
    
    def _update_conversation_history(self, question: str, response: str):
        """Update conversation history"""
        self.conversation_history.append({
            'role': 'user',
            'content': question
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Keep only last 10 messages to prevent context overflow
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        # Track response diversity
        self._track_response_diversity(question, response)
    
    def _track_response_diversity(self, question: str, response: str):
        """Track response diversity to avoid repetition"""
        question_key = question.lower().strip()
        
        if question_key not in self.response_diversity_tracker:
            self.response_diversity_tracker[question_key] = []
        
        self.response_diversity_tracker[question_key].append(response)
        
        # Keep only last 3 responses for diversity tracking
        if len(self.response_diversity_tracker[question_key]) > 3:
            self.response_diversity_tracker[question_key] = self.response_diversity_tracker[question_key][-3:] 
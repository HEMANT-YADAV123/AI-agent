import google.generativeai as genai
import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class SimpleMemoryStore:
    def __init__(self, max_memories_per_user: int = 20):
        self.memories = {}
        self.max_memories = max_memories_per_user
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 1 hour
    
    def add_memory(self, username: str, message: str, response: str):
        """Add a new memory to the store with automatic cleanup"""
        current_time = time.time()
        
        # Periodic cleanup of old memories
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_memories()
            self._last_cleanup = current_time
        
        if username not in self.memories:
            self.memories[username] = []
        
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message[:500],  # limit message length to prevent memory stack is full error
            "assistant_response": response[:1000],  # limit response length
            "created_at": current_time
        }
        
        self.memories[username].append(memory_entry)
        
        # keep only recent memories per user for better recent answer.
        if len(self.memories[username]) > self.max_memories:
            self.memories[username] = self.memories[username][-self.max_memories:]
        
        logger.debug(f"Added memory for {username} (total: {len(self.memories[username])})")
    
    def _cleanup_old_memories(self):
        """Remove memories older than 24 hours"""
        cutoff_time = time.time() - 86400  # 24 hours ago
        
        for username in self.memories:
            original_count = len(self.memories[username])
            self.memories[username] = [
                mem for mem in self.memories[username] 
                if mem.get('created_at', 0) > cutoff_time
            ]
            
            if len(self.memories[username]) < original_count:
                logger.debug(f"Cleaned up {original_count - len(self.memories[username])} old memories for {username}")
    
    def get_relevant_memories(self, username: str, current_message: str, limit: int = 3):
        """Retrieve relevant memories for context"""
        if username not in self.memories or not self.memories[username]:
            return []
        
        # simple keyword matching for relevance
        message_words = set(current_message.lower().split())
        scored_memories = []
        
        for memory in self.memories[username][-10:]:  # Only check recent memories
            memory_words = set(memory['user_message'].lower().split())
            overlap = len(message_words.intersection(memory_words))
            scored_memories.append((overlap, memory))
        
        # sort by relevance score and recency
        scored_memories.sort(key=lambda x: (x[0], x[1].get('created_at', 0)), reverse=True)
        
        return [memory for score, memory in scored_memories[:limit]]
    
    def get_user_stats(self) -> Dict[str, int]:
        """Get statistics about stored memories"""
        return {username: len(memories) for username, memories in self.memories.items()}


class ChatAgent:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # retry logic
        self.model = None
        self.memory_store = SimpleMemoryStore()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # rate limiting: min 100ms between requests
        self._max_retries = 3
        
        self._initialize_model()
        
        # response caching for identical queries (simple)
        self._response_cache = {}
        self._cache_max_size = 100
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("ChatAgent initialized successfully")
    
    def _initialize_model(self):
        """Initialize the Gemini model with retry logic"""
        for attempt in range(self._max_retries):
            try:
                genai.configure(api_key=self.api_key)
                
                # use more efficient model configuration
                generation_config = genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=512,  # limit response length for faster generation
                    stop_sequences=None,
                )
                
                self.model = genai.GenerativeModel(
                    'gemini-2.0-flash',
                    generation_config=generation_config
                )
                
                logger.info(f"Model initialized successfully on attempt {attempt + 1}")
                return
                
            except Exception as e:
                logger.warning(f"Model initialization attempt {attempt + 1} failed: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                else:
                    raise
    
    def _get_cache_key(self, username: str, message: str) -> str:
        """Generate cache key for response caching"""
        return f"{username}:{hash(message.lower().strip())}"
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (response, timestamp) in self._response_cache.items()
            if current_time - timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._response_cache[key]
        
        # limit cache size
        if len(self._response_cache) > self._cache_max_size:
            # remove oldest entries
            sorted_items = sorted(
                self._response_cache.items(), 
                key=lambda x: x[1][1]  # sort by timestamp
            )
            
            for key, _ in sorted_items[:len(sorted_items) - self._cache_max_size]:
                del self._response_cache[key]
    
    def generate_response(self, username: str, message: str) -> str:
        """Generate a contextual response using memory with caching and rate limiting"""
        try:
            # clean message input
            message = message.strip()
            if not message:
                return "I didn't receive a message. Could you please try again?"
            
            # check cache first
            cache_key = self._get_cache_key(username, message)
            current_time = time.time()
            
            if cache_key in self._response_cache:
                cached_response, timestamp = self._response_cache[cache_key]
                if current_time - timestamp < self._cache_ttl:
                    logger.debug(f"Cache hit for {username}")
                    return cached_response
            
            # rate limiting
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._min_request_interval:
                time.sleep(self._min_request_interval - time_since_last)
            
            # get relevant memories efficiently
            memories = self.memory_store.get_relevant_memories(username, message, limit=2)  # Reduce to 2 for faster processing
            
            # build optimized context
            context_parts = [
                f"You are a helpful AI assistant talking to {username}.",
                "Keep responses concise, friendly, and under 200 words."
            ]
            
            if memories:
                context_parts.append("Recent conversation context:")
                for i, memory in enumerate(memories, 1):
                    context_parts.append(
                        f"{i}. User: '{memory['user_message'][:100]}...' "
                        f"You: '{memory['assistant_response'][:100]}...'"
                    )
            
            context_parts.extend([
                f"Current message: {message}",
                "Respond naturally, referencing past context when relevant."
            ])
            
            context = "\n".join(context_parts)
            
            logger.debug(f"Generating response for {username}: {message[:50]}...")
            
            # Generate response with retry logic
            response_text = self._generate_with_retry(context)
            
            # Update request time
            self._last_request_time = time.time()
            
            # Cache the response
            self._response_cache[cache_key] = (response_text, current_time)
            self._clean_cache()
            
            # Store this interaction in memory (async to not block)
            self.memory_store.add_memory(username, message, response_text)
            
            logger.info(f"Response generated successfully for {username}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response for {username}: {str(e)}")
            error_msg = "Sorry, I encountered an error. Please try again in a moment!"
            
            # Still store the interaction even if there was an error
            try:
                self.memory_store.add_memory(username, message, error_msg)
            except Exception as mem_error:
                logger.error(f"Failed to store memory: {mem_error}")
            
            return error_msg
    
    def _generate_with_retry(self, context: str) -> str:
        """Generate response with retry logic and fallbacks"""
        for attempt in range(self._max_retries):
            try:
                response = self.model.generate_content(context)
                
                if response and response.text:
                    return response.text.strip()
                else:
                    raise Exception("Empty response from model")
                    
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self._max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    time.sleep(wait_time)
                    
                    # Try to reinitialize model on persistent failures
                    if "API" in str(e) or "quota" in str(e).lower():
                        try:
                            self._initialize_model()
                        except:
                            pass  # Continue with existing model
                else:
                    # Final fallback
                    return "I'm having trouble generating a response right now. Please try again!"
        
        return "Sorry, I'm experiencing technical difficulties. Please try again later."
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory statistics for debugging"""
        stats = self.memory_store.get_user_stats()
        stats['cache_size'] = len(self._response_cache)
        return stats
    
    def clear_user_memory(self, username: str):
        """Clear memories for a specific user"""
        if username in self.memory_store.memories:
            del self.memory_store.memories[username]
            logger.info(f"Cleared memories for {username}")
    
    def health_check(self) -> Dict[str, any]:
        """Check agent health status"""
        try:
            # Test model with simple query
            test_response = self.model.generate_content("Say 'OK'")
            model_healthy = bool(test_response and test_response.text)
        except:
            model_healthy = False
        
        return {
            "model_healthy": model_healthy,
            "memory_users": len(self.memory_store.memories),
            "cache_size": len(self._response_cache),
            "api_configured": bool(self.api_key)
        }
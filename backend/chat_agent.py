# chat_agent.py
import google.generativeai as genai
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class SimpleMemoryStore:
    def __init__(self):
        self.memories = {}
    
    def add_memory(self, username: str, message: str, response: str):
        """Add a new memory to the store"""
        if username not in self.memories:
            self.memories[username] = []
        
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "assistant_response": response,
        }
        
        self.memories[username].append(memory_entry)
        
        # Keep only last 10 memories per user to avoid memory bloat
        if len(self.memories[username]) > 10:
            self.memories[username] = self.memories[username][-10:]
        
        logger.info(f"Added memory for {username}")
    
    def get_relevant_memories(self, username: str, current_message: str, limit: int = 3):
        """Retrieve relevant memories for context"""
        if username not in self.memories or not self.memories[username]:
            return []
        
        # Return most recent memories (simple approach)
        return self.memories[username][-limit:]


class ChatAgent:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.memory_store = SimpleMemoryStore()
            logger.info("ChatAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChatAgent: {e}")
            raise
    
    def generate_response(self, username: str, message: str):
        """Generate a contextual response using memory"""
        try:
            # Get relevant memories
            memories = self.memory_store.get_relevant_memories(username, message)
            
            # Build context
            context = f"You are a helpful AI assistant talking to {username}.\n"
            
            if memories:
                context += "Here's some relevant conversation history:\n"
                for memory in memories:
                    context += f"- User said: '{memory['user_message']}', You responded: '{memory['assistant_response']}'\n"
            
            context += f"\nCurrent message from {username}: {message}\n"
            context += "Please respond in a friendly and contextual manner, referencing past conversations when relevant. Keep responses concise and natural."
            
            logger.info(f"Generating response for {username}: {message[:50]}...")
            
            response = self.model.generate_content(context)
            response_text = response.text
            
            # Store this interaction in memory
            self.memory_store.add_memory(username, message, response_text)
            
            logger.info(f"Response generated successfully for {username}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response for {username}: {str(e)}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            
            # Still store the interaction even if there was an error
            try:
                self.memory_store.add_memory(username, message, error_msg)
            except Exception as mem_error:
                logger.error(f"Failed to store memory: {mem_error}")
            
            return error_msg
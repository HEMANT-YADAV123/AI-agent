import google.generativeai as genai
from memory_store import MemoryStore
import os
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:
    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        self.memory_store = MemoryStore()
    
    def generate_response(self, username: str, message: str):
        """Generate a contextual response using memory"""
        # Get relevant memories
        memories = self.memory_store.get_relevant_memories(username, message)
        
        # Build context
        context = f"You are a helpful AI assistant talking to {username}.\n"
        
        if memories:
            context += "Here's some relevant conversation history:\n"
            for memory in memories:
                context += f"- {memory['content']}\n"
        
        context += f"\nCurrent message from {username}: {message}\n"
        context += "Please respond in a friendly and contextual manner, referencing past conversations when relevant."
        
        try:
            response = self.model.generate_content(context)
            response_text = response.text
            
            # Store this interaction in memory
            self.memory_store.add_memory(username, message, response_text)
            
            return response_text
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
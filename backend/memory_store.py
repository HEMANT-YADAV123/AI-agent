import json
import os
from datetime import datetime

class SimpleMemoryStore:
    def __init__(self):
        self.memory_file = "user_memories.json"
        self.memories = self._load_memories()
    
    def _load_memories(self):
        """Load memories from JSON file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_memories(self):
        """Save memories to JSON file"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memories, f, indent=2, ensure_ascii=False)
    
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
        
        # Keep only last 50 memories per user to avoid memory bloat
        if len(self.memories[username]) > 50:
            self.memories[username] = self.memories[username][-50:]
        
        self.save_memories()
    
    def get_relevant_memories(self, username: str, current_message: str, limit: int = 3):
        """Retrieve relevant memories for context"""
        if username not in self.memories or not self.memories[username]:
            return []
        
        # Return most recent memories (simple approach)
        return self.memories[username][-limit:]
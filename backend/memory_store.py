import chromadb
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime
import os

class MemoryStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(
            name="user_memories",
            get_or_create=True
        )
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_memory(self, username: str, message: str, response: str):
        """Add a new memory to the store"""
        memory_text = f"User {username} said: {message}. Assistant responded: {response}"
        embedding = self.encoder.encode([memory_text])[0].tolist()
        
        self.collection.add(
            documents=[memory_text],
            embeddings=[embedding],
            metadatas=[{
                "username": username,
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "assistant_response": response
            }],
            ids=[f"{username}_{datetime.now().timestamp()}"]
        )
    
    def get_relevant_memories(self, username: str, current_message: str, limit: int = 3):
        """Retrieve relevant memories for context"""
        if self.collection.count() == 0:
            return []
            
        query_embedding = self.encoder.encode([current_message])[0].tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, self.collection.count()),
            where={"username": username}
        )
        
        if not results['documents'] or not results['documents'][0]:
            return []
            
        memories = []
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            memories.append({
                'content': doc,
                'timestamp': metadata['timestamp'],
                'user_message': metadata['user_message'],
                'assistant_response': metadata['assistant_response']
            })
        
        return memories
import asyncio
import os
from livekit import api
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.llm import ChatMessage
from livekit.protocol import participant_pb2 as proto
from livekit import rtc
from chat_agent import ChatAgent
from dotenv import load_dotenv

load_dotenv()

class ChatBot:
    def __init__(self):
        self.agent = ChatAgent()
        self.room = None
        
    async def run(self, job_ctx: JobContext):
        self.room = job_ctx.room
        
        print(f"AI Chat Agent joining room: {self.room.name}")
        
        # Send welcome message
        await self.room.local_participant.publish_data(
            "Welcome! I'm your AI assistant. I can remember our previous conversations!",
            reliable=True
        )
        
        # Listen for chat messages
        @self.room.on("data_received")
        def on_data_received(data, participant):
            asyncio.create_task(self.handle_message(data.decode('utf-8'), participant))
    
    async def handle_message(self, message: str, participant):
        """Handle incoming chat messages"""
        if participant.identity == "ai-agent":
            return  # Don't respond to own messages
            
        username = participant.identity or "User"
        print(f"Received message from {username}: {message}")
        
        # Generate response
        response = self.agent.generate_response(username, message)
        
        # Send response back to the room
        await self.room.local_participant.publish_data(
            f"🤖 {response}",
            reliable=True
        )
        print(f"Sent response: {response}")

async def entrypoint(job_ctx: JobContext):
    bot = ChatBot()
    await bot.run(job_ctx)
    
    # Keep the agent running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint),
    )
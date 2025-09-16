# main.py - Fixed version without state attribute
import asyncio
import os
import jwt
import time
from livekit.agents import JobContext, WorkerOptions, cli
from livekit import rtc
from dotenv import load_dotenv

load_dotenv()

def debug_data_packet_kind():
    """Debug function to see available DataPacketKind values"""
    print("Available DataPacketKind values:")
    for attr in dir(rtc.DataPacketKind):
        if not attr.startswith('_'):
            value = getattr(rtc.DataPacketKind, attr)
            print(f"  - {attr}: {value} (type: {type(value)})")

def debug_room_attributes(room):
    """Debug function to see available Room attributes"""
    print("Available Room attributes:")
    for attr in dir(room):
        if not attr.startswith('_'):
            try:
                value = getattr(room, attr)
                print(f"  - {attr}: {type(value).__name__}")
            except:
                print(f"  - {attr}: <error accessing>")

class ChatBot:
    def __init__(self):
        self.room = rtc.Room()
        self.agent = None
        self.local_participant = None
        
    async def initialize_agent(self):
        """Initialize the chat agent"""
        try:
            from chat_agent import ChatAgent
            self.agent = ChatAgent()
            print("Chat agent initialized successfully")
        except Exception as e:
            print(f"Failed to initialize chat agent: {e}")
            raise
        
    async def connect_to_room(self):
        """Manually connect to the specific ai-chat-room"""
        try:
            # Debug available DataPacketKind values
            debug_data_packet_kind()
            
            api_key = os.getenv('LIVEKIT_API_KEY')
            api_secret = os.getenv('LIVEKIT_API_SECRET')
            ws_url = os.getenv('LIVEKIT_URL')
            
            if not all([api_key, api_secret, ws_url]):
                raise Exception("Missing LiveKit credentials")
            
            # Generate token for AI agent
            now = int(time.time())
            token = jwt.encode({
                'iss': api_key,
                'sub': 'ai-agent',
                'nbf': now,
                'exp': now + 3600,
                'video': {
                    'room': 'ai-chat-room',
                    'roomJoin': True,
                    'canPublish': True,
                    'canSubscribe': True,
                    'canPublishData': True
                }
            }, api_secret, algorithm='HS256')
            
            print(f"Connecting to room: ai-chat-room")
            print(f"WebSocket URL: {ws_url}")
            print(f"Token generated: {bool(token)}")
            
            # Connect to the room
            await self.room.connect(ws_url, token)
            self.local_participant = self.room.local_participant
            
            print(f"✅ AI Agent connected to room: ai-chat-room")
            print(f"✅ Local participant: {self.local_participant.identity}")
            
            # Debug room attributes to see what's available
            debug_room_attributes(self.room)
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def setup_event_handlers(self):
        """Set up room event handlers with flexible signature handling"""
        
        @self.room.on("data_received")
        def on_data_received(*args):
            try:
                # Debug: print what arguments we're receiving
                print(f"📨 Data received with {len(args)} arguments: {[type(arg).__name__ for arg in args]}")
                
                # Handle different argument patterns
                participant = None
                message = None
                
                if len(args) == 3:
                    # New signature: (data, kind, participant)
                    data, kind, participant = args
                    message = data.decode('utf-8')
                elif len(args) == 2:
                    # Old signature: (data, participant)  
                    data, participant = args
                    message = data.decode('utf-8')
                elif len(args) == 1 and hasattr(args[0], 'data'):
                    # DataPacket object
                    data_packet = args[0]
                    message = data_packet.data.decode('utf-8')
                    participant = getattr(data_packet, 'participant', None)
                else:
                    print(f"❌ Unexpected data_received arguments: {args}")
                    return
                
                print(f"📨 Message received from {getattr(participant, 'identity', 'unknown')}: {message}")
                asyncio.create_task(self.handle_message(message, participant))
                
            except Exception as e:
                print(f"❌ Error in data_received handler: {e}")
                import traceback
                traceback.print_exc()
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            print(f"🟢 Participant connected: {participant.identity}")
            asyncio.create_task(self.send_welcome_to_participant(participant))
        
        @self.room.on("participant_disconnected") 
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            print(f"🔴 Participant disconnected: {participant.identity}")
        
        @self.room.on("disconnected")
        def on_disconnected():
            print("🔴 Room disconnected")
    
    async def send_welcome_to_participant(self, participant):
        """Send welcome message when a participant joins"""
        try:
            await asyncio.sleep(1)
            if self.local_participant:
                username = getattr(participant, 'identity', 'User')
                welcome_msg = f"🤖 Hello {username}! I'm your AI assistant. Type anything to start chatting!"
                
                # Try different data packet kinds - use integer 0 for reliable
                await self.local_participant.publish_data(
                    welcome_msg.encode('utf-8'),
                )
                
                print(f"✅ Welcome message sent to {username}")
        except Exception as e:
            print(f"❌ Failed to send welcome message: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_message(self, message: str, participant: rtc.RemoteParticipant):
        """Handle incoming chat messages"""
        try:
            if not message.strip():
                return
                
            participant_id = getattr(participant, 'identity', None)
            
            # Skip messages from AI agent itself
            if participant_id == "ai-agent":
                return
                
            username = participant_id or "User"
            print(f"📨 Processing message from {username}: {message}")
            
            if not self.local_participant:
                print("❌ Cannot respond - local participant not available")
                return
            
            # Generate response
            if self.agent:
                print(f"🤔 Generating response for {username}...")
                response = self.agent.generate_response(username, message)
                
                # Use integer 0 for reliable data transmission
                await self.local_participant.publish_data(
                    f"🤖 {response}".encode('utf-8'),
                )
                
                print(f"✅ Response sent to {username}")
                
        except Exception as e:
            print(f"❌ Error handling message: {e}")
            import traceback
            traceback.print_exc()

async def entrypoint(job_ctx: JobContext):
    """Main entrypoint for the LiveKit agent"""
    print("🚀 Starting LiveKit Chat Agent...")
    print("=" * 50)
    
    bot = ChatBot()
    
    try:
        # Initialize agent first
        await bot.initialize_agent()
        
        # Connect to the specific room
        await bot.connect_to_room()
        
        # Set up event handlers
        bot.setup_event_handlers()
        
        print("✅ Chat bot is running and ready in ai-chat-room!")
        print("💬 Waiting for messages...")
        print("=" * 50)
        
        # Keep the agent running
        while True:
            await asyncio.sleep(300)
            if bot.local_participant:
                print("💚 Agent status: Online and ready")
            else:
                print("🟡 Agent status: Running but local participant unavailable")
            
    except Exception as e:
        print(f"❌ Critical error in entrypoint: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("🤖 LiveKit AI Chat Agent")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'LIVEKIT_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please check your .env file")
        exit(1)
    
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint),
    )
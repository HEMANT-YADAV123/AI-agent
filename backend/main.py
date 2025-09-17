import asyncio
import os
import jwt
import time
from livekit.agents import JobContext, WorkerOptions, cli
from livekit import rtc
from dotenv import load_dotenv
import logging

# Set up proper logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def debug_data_packet_kind():
    """Debug function to see available DataPacketKind values"""
    logger.debug("Available DataPacketKind values:")
    for attr in dir(rtc.DataPacketKind):
        if not attr.startswith('_'):
            value = getattr(rtc.DataPacketKind, attr)
            logger.debug(f"  - {attr}: {value} (type: {type(value)})")

def debug_room_attributes(room):
    """Debug function to see available Room attributes"""
    logger.debug("Available Room attributes:")
    for attr in dir(room):
        if not attr.startswith('_'):
            try:
                value = getattr(room, attr)
                logger.debug(f"  - {attr}: {type(value).__name__}")
            except:
                logger.debug(f"  - {attr}: <error accessing>")

class ChatBot:
    def __init__(self):
        self.room = rtc.Room()
        self.agent = None
        self.local_participant = None
        self._shutdown_flag = False
        self._message_queue = asyncio.Queue(maxsize=100)  # Prevent memory buildup
        self._message_processor = None
        
    async def initialize_agent(self):
        """Initialize the chat agent"""
        try:
            from chat_agent import ChatAgent
            self.agent = ChatAgent()
            logger.info("Chat agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chat agent: {e}")
            raise
        
    async def connect_to_room(self):
        """Manually connect to the specific ai-chat-room"""
        try:
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
                'exp': now + 3600,  # 1 hour expiry
                'video': {
                    'room': 'ai-chat-room',
                    'roomJoin': True,
                    'canPublish': True,
                    'canSubscribe': True,
                    'canPublishData': True
                }
            }, api_secret, algorithm='HS256')
            
            logger.info(f"Connecting to room: ai-chat-room")
            logger.debug(f"WebSocket URL: {ws_url}")
            logger.debug(f"Token generated: {bool(token)}")
            
            # Connect to the room
            await self.room.connect(ws_url, token)
            self.local_participant = self.room.local_participant
            
            logger.info(f"✅ AI Agent connected to room: ai-chat-room")
            logger.info(f"✅ Local participant: {self.local_participant.identity}")
            
            debug_room_attributes(self.room)
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise
    
    def setup_event_handlers(self):
        """Set up room event handlers with flexible signature handling"""
        
        @self.room.on("data_received")
        def on_data_received(*args):
            try:
                # Handle different argument patterns efficiently
                participant = None
                message = None
                
                if len(args) == 3:
                    data, kind, participant = args
                    message = data.decode('utf-8')
                elif len(args) == 2:
                    data, participant = args
                    message = data.decode('utf-8')
                elif len(args) == 1 and hasattr(args[0], 'data'):
                    data_packet = args[0]
                    message = data_packet.data.decode('utf-8')
                    participant = getattr(data_packet, 'participant', None)
                else:
                    logger.warning(f"Unexpected data_received arguments: {len(args)} args")
                    return
                
                # Skip empty messages early
                if not message.strip():
                    return
                    
                participant_id = getattr(participant, 'identity', 'unknown')
                
                # Skip messages from AI agent itself
                if participant_id == "ai-agent":
                    return
                
                logger.info(f"📨 Message received from {participant_id}: {message[:100]}...")
                
                # Queue message for processing (non-blocking)
                try:
                    self._message_queue.put_nowait((message, participant))
                except asyncio.QueueFull:
                    logger.warning("Message queue full, dropping oldest message")
                    try:
                        self._message_queue.get_nowait()  # Remove oldest
                        self._message_queue.put_nowait((message, participant))
                    except asyncio.QueueEmpty:
                        pass
                
            except Exception as e:
                logger.error(f"❌ Error in data_received handler: {e}")
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"🟢 Participant connected: {participant.identity}")
            asyncio.create_task(self.send_welcome_to_participant(participant))
        
        @self.room.on("participant_disconnected") 
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"🔴 Participant disconnected: {participant.identity}")
        
        @self.room.on("disconnected")
        def on_disconnected():
            logger.warning("🔴 Room disconnected")
            self._shutdown_flag = True
    
    async def start_message_processor(self):
        """Start the async message processor"""
        self._message_processor = asyncio.create_task(self._process_message_queue())
        
    async def _process_message_queue(self):
        """Process messages from queue asynchronously"""
        while not self._shutdown_flag:
            try:
                # Wait for message with timeout
                message, participant = await asyncio.wait_for(
                    self._message_queue.get(), 
                    timeout=1.0
                )
                await self.handle_message(message, participant)
                self._message_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Check shutdown flag
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    async def send_welcome_to_participant(self, participant):
        """Send welcome message when a participant joins"""
        try:
            await asyncio.sleep(1)  # Brief delay
            if self.local_participant and not self._shutdown_flag:
                username = getattr(participant, 'identity', 'User')
                welcome_msg = f"🤖 Hello {username}! I'm your AI assistant. Type anything to start chatting!"
                
                await self.local_participant.publish_data(welcome_msg.encode('utf-8'))
                logger.info(f"✅ Welcome message sent to {username}")
                
        except Exception as e:
            logger.error(f"❌ Failed to send welcome message: {e}")
    
    async def handle_message(self, message: str, participant: rtc.RemoteParticipant):
        """Handle incoming chat messages"""
        try:
            if not message.strip() or self._shutdown_flag:
                return
                
            participant_id = getattr(participant, 'identity', None)
            username = participant_id or "User"
            
            logger.info(f"📨 Processing message from {username}: {message[:50]}...")
            
            if not self.local_participant:
                logger.warning("❌ Cannot respond - local participant not available")
                return
            
            # Generate response with timeout
            if self.agent:
                logger.debug(f"🤔 Generating response for {username}...")
                
                # Add timeout to prevent hanging
                response_task = asyncio.create_task(
                    self._generate_response_with_fallback(username, message)
                )
                
                try:
                    response = await asyncio.wait_for(response_task, timeout=30.0)
                    
                    await self.local_participant.publish_data(
                        f"🤖 {response}".encode('utf-8')
                    )
                    
                    logger.info(f"✅ Response sent to {username}")
                    
                except asyncio.TimeoutError:
                    timeout_msg = "Sorry, I'm taking too long to respond. Please try again!"
                    await self.local_participant.publish_data(
                        f"🤖 {timeout_msg}".encode('utf-8')
                    )
                    logger.warning(f"Response timeout for {username}")
                
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    async def _generate_response_with_fallback(self, username: str, message: str):
        """Generate response with fallback handling"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                self.agent.generate_response,
                username,
                message
            )
            return response
        except Exception as e:
            logger.error(f"Response generation failed for {username}: {e}")
            return f"Sorry {username}, I encountered an error. Please try again!"
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down chat bot...")
        self._shutdown_flag = True
        
        if self._message_processor:
            self._message_processor.cancel()
            try:
                await self._message_processor
            except asyncio.CancelledError:
                pass
        
        # Process remaining messages quickly
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
                self._message_queue.task_done()
            except asyncio.QueueEmpty:
                break

async def entrypoint(job_ctx: JobContext):
    """Main entrypoint for the LiveKit agent"""
    logger.info("🚀 Starting LiveKit Chat Agent...")
    logger.info("=" * 50)
    
    bot = ChatBot()
    
    try:
        # Initialize agent first
        await bot.initialize_agent()
        
        # Connect to the specific room
        await bot.connect_to_room()
        
        # Set up event handlers
        bot.setup_event_handlers()
        
        # Start message processor
        await bot.start_message_processor()
        
        logger.info("✅ Chat bot is running and ready in ai-chat-room!")
        logger.info("💬 Waiting for messages...")
        logger.info("=" * 50)
        
        # Improved heartbeat with connection monitoring
        heartbeat_interval = 30  # 30 seconds instead of 5 minutes
        while not bot._shutdown_flag:
            await asyncio.sleep(heartbeat_interval)
            
            if bot.local_participant:
                logger.debug("💚 Agent status: Online and ready")
            else:
                logger.warning("🟡 Agent status: Running but local participant unavailable")
                # Could add reconnection logic here
            
    except Exception as e:
        logger.error(f"❌ Critical error in entrypoint: {e}")
        raise
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    logger.info("🤖 LiveKit AI Chat Agent")
    logger.info("=" * 50)
    
    # Check environment variables
    required_vars = ['LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'LIVEKIT_URL', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.error("Please check your .env file")
        exit(1)
    
    # Set log level based on environment
    if os.getenv('DEBUG', '').lower() == 'true':
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint),
    )
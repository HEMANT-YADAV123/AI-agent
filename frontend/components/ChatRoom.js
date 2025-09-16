import { useEffect, useState, useRef } from 'react';
import { Room, RoomEvent } from 'livekit-client';

export default function ChatRoom() {
  const [room, setRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [username, setUsername] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');
  const [participants, setParticipants] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Cleanup on component unmount
    return () => {
      if (room) {
        room.disconnect();
      }
    };
  }, [room]);

  const connectToRoom = async () => {
    if (!username.trim()) {
      setError('Please enter a username');
      return;
    }

    setIsConnecting(true);
    setError('');
    
    try {
      console.log('Getting token for username:', username);
      
      const response = await fetch('/api/get-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim() })
      });
      
      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Token request failed: ${response.status} ${errorData}`);
      }
      
      const { token, wsUrl, roomName } = await response.json();
      
      console.log('Connecting to LiveKit room:', wsUrl, 'Room:', roomName);
      
      // Create LiveKit room
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });
      
      // Set up event listeners
      room
        .on(RoomEvent.Connected, () => {
          console.log('Connected to room');
          setIsConnected(true);
          setIsConnecting(false);
          setError('');
          
          // Update participants list immediately after connection
          updateParticipantsList(room);
          
          setMessages(prev => [...prev, {
            id: Date.now(),
            sender: 'System',
            message: 'Connected to chat room!',
            timestamp: new Date(),
            isSystem: true
          }]);
        })
        .on(RoomEvent.Disconnected, () => {
          console.log('Disconnected from room');
          setIsConnected(false);
          setParticipants([]);
          setMessages(prev => [...prev, {
            id: Date.now(),
            sender: 'System',
            message: 'Disconnected from chat room',
            timestamp: new Date(),
            isSystem: true
          }]);
        })
        .on(RoomEvent.DataReceived, (payload, participant) => {
          try {
            const decoder = new TextDecoder();
            const message = decoder.decode(payload);
            
            console.log('Message received:', message, 'from:', participant?.identity);
            
            setMessages(prev => [...prev, {
              id: Date.now() + Math.random(),
              sender: participant?.identity || 'Unknown',
              message: message,
              timestamp: new Date(),
              isBot: participant?.identity === 'ai-agent'
            }]);
          } catch (error) {
            console.error('Error processing received data:', error);
          }
        })
        .on(RoomEvent.ParticipantConnected, (participant) => {
          console.log('Participant connected:', participant.identity);
          setParticipants(prev => {
            // Avoid duplicates
            if (!prev.includes(participant.identity)) {
              return [...prev, participant.identity];
            }
            return prev;
          });
          
          if (participant.identity === 'ai-agent') {
            setMessages(prev => [...prev, {
              id: Date.now(),
              sender: 'System',
              message: 'AI Assistant joined the chat',
              timestamp: new Date(),
              isSystem: true
            }]);
          }
        })
        .on(RoomEvent.ParticipantDisconnected, (participant) => {
          console.log('Participant disconnected:', participant.identity);
          setParticipants(prev => prev.filter(p => p !== participant.identity));
        });

      // Connect to the room
      await room.connect(wsUrl, token, {
        autoSubscribe: true,
      });
      setRoom(room);
      
    } catch (error) {
      console.error('Connection failed:', error);
      setError(`Connection failed: ${error.message}`);
      setIsConnecting(false);
    }
  };

  // Helper function to update participants list
// Helper function to update participants list
const updateParticipantsList = (room) => {
  if (room) {
    try {
      // Check if participants exists and has values method
      const remoteParticipants = room.participants ? 
        Array.from(room.participants.values()).map(p => p.identity) : [];
      
      // Add local participant (current user)
      const allParticipants = [...remoteParticipants];
      if (room.localParticipant) {
        allParticipants.push(room.localParticipant.identity);
      }
      
      console.log('All participants:', allParticipants);
      setParticipants(allParticipants);
    } catch (error) {
      console.error('Error updating participants list:', error);
    }
  }
};

  const sendMessage = async () => {
    if (!inputMessage.trim() || !room || !isConnected) return;

    const message = inputMessage.trim();
    setInputMessage('');

    // Add user message to local state
    setMessages(prev => [...prev, {
      id: Date.now(),
      sender: username,
      message: message,
      timestamp: new Date(),
      isUser: true
    }]);

    // Send message via LiveKit data channel
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(message);
      
      await room.localParticipant.publishData(data, undefined, {
        reliable: true
      });
      
      console.log('Message sent:', message);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(`Failed to send message: ${error.message}`);
      
      // Remove the message if sending failed
      setMessages(prev => prev.filter(msg => msg.id !== Date.now()));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const disconnect = () => {
    if (room) {
      room.disconnect();
      setRoom(null);
    }
    setIsConnected(false);
    setParticipants([]);
    setMessages([]);
    setError('');
  };

  // Debug: Log participants when they change
  useEffect(() => {
    console.log('Participants updated:', participants);
  }, [participants]);

  // ... rest of the component remains the same

  if (!isConnected && !isConnecting) {
    return (
      <div style={{ 
        maxWidth: '400px', 
        margin: '50px auto', 
        padding: '20px',
        border: '1px solid #ddd',
        borderRadius: '8px',
        backgroundColor: '#f9f9f9'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Join AI Chat Room</h2>
        
        {error && (
          <div style={{
            padding: '10px',
            marginBottom: '15px',
            backgroundColor: '#ffe6e6',
            border: '1px solid #ff9999',
            borderRadius: '4px',
            color: '#cc0000',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}
        
        <input
          type="text"
          placeholder="Enter your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{
            width: '100%',
            padding: '10px',
            marginBottom: '10px',
            border: '1px solid #ccc',
            borderRadius: '4px',
            fontSize: '16px',
            boxSizing: 'border-box'
          }}
          onKeyPress={(e) => e.key === 'Enter' && connectToRoom()}
        />
        <button
          onClick={connectToRoom}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          Join Chat
        </button>
      </div>
    );
  }

  if (isConnecting) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <h3>Connecting to chat room...</h3>
        <p>Username: {username}</p>
        {error && (
          <div style={{
            padding: '10px',
            marginTop: '15px',
            backgroundColor: '#ffe6e6',
            border: '1px solid #ff9999',
            borderRadius: '4px',
            color: '#cc0000'
          }}>
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ 
      maxWidth: '800px', 
      margin: '20px auto', 
      height: '80vh',
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #ddd',
      borderRadius: '8px',
      backgroundColor: '#fff'
    }}>
      {/* Header */}
      <div style={{
        padding: '15px',
        backgroundColor: '#007bff',
        color: 'white',
        borderRadius: '8px 8px 0 0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h3 style={{ margin: 0 }}>AI Chat Room - {username}</h3>
          <small>Participants: {participants.length}</small>
        </div>
        <button
          onClick={disconnect}
          style={{
            padding: '5px 10px',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Disconnect
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div style={{
          padding: '10px',
          backgroundColor: '#ffe6e6',
          border: '1px solid #ff9999',
          color: '#cc0000'
        }}>
          {error}
        </div>
      )}

      {/* Participants list */}
      {participants.length > 0 && (
        <div style={{
          padding: '5px 15px',
          backgroundColor: '#e9ecef',
          borderBottom: '1px solid #ddd',
          fontSize: '12px'
        }}>
          Online: {participants.join(', ')}
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1,
        padding: '10px',
        overflowY: 'auto',
        backgroundColor: '#f8f9fa'
      }}>
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            style={{
              marginBottom: '10px',
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: msg.isBot ? '#e3f2fd' : 
                             msg.isUser ? '#e8f5e8' : 
                             msg.isSystem ? '#fff3cd' : '#fff',
              border: `1px solid ${msg.isBot ? '#bbdefb' : 
                                  msg.isUser ? '#c8e6c9' : 
                                  msg.isSystem ? '#ffeaa7' : '#e0e0e0'}`,
              marginLeft: msg.isUser ? '20%' : '0',
              marginRight: msg.isUser ? '0' : '20%'
            }}
          >
            <div style={{
              fontSize: '12px',
              color: '#666',
              marginBottom: '4px',
              fontWeight: 'bold'
            }}>
              {msg.sender} • {msg.timestamp.toLocaleTimeString()}
            </div>
            <div>{msg.message}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '15px',
        borderTop: '1px solid #ddd',
        backgroundColor: '#fff'
      }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected}
            style={{
              flex: 1,
              padding: '10px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '16px'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !inputMessage.trim()}
            style={{
              padding: '10px 20px',
              backgroundColor: isConnected && inputMessage.trim() ? '#28a745' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              cursor: isConnected && inputMessage.trim() ? 'pointer' : 'not-allowed'
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
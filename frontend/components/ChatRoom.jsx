import { useEffect, useState, useRef } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import LoginForm from './LoginForm';
import ConnectionStatus from './ConnectionStatus';
import ChatHeader from './ChatHeader';
import ParticipantsList from './ParticipantsList';
import MessagesList from './MessagesList';
import MessageInput from './MessageInput';
import { AlertCircle } from 'lucide-react';

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
      
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });
      
      room
        .on(RoomEvent.Connected, () => {
          console.log('Connected to room');
          setIsConnected(true);
          setIsConnecting(false);
          setError('');
          
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

  const updateParticipantsList = (room) => {
    if (room) {
      try {
        const remoteParticipants = room.participants ? 
          Array.from(room.participants.values()).map(p => p.identity) : [];
        
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

    setMessages(prev => [...prev, {
      id: Date.now(),
      sender: username,
      message: message,
      timestamp: new Date(),
      isUser: true
    }]);

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

  useEffect(() => {
    console.log('Participants updated:', participants);
  }, [participants]);

  // Render different states
  if (!isConnected && !isConnecting) {
    return (
      <LoginForm
        username={username}
        setUsername={setUsername}
        onConnect={connectToRoom}
        error={error}
        isConnecting={isConnecting}
      />
    );
  }

  if (isConnecting) {
    return (
      <ConnectionStatus
        isConnecting={isConnecting}
        username={username}
        error={error}
      />
    );
  }

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
      <ChatHeader
        username={username}
        participants={participants}
        onDisconnect={disconnect}
      />
      
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <span className="text-red-700 text-sm">{error}</span>
        </div>
      )}

      <ParticipantsList participants={participants} />

      <MessagesList messages={messages} messagesEndRef={messagesEndRef} />

      <MessageInput
        inputMessage={inputMessage}
        setInputMessage={setInputMessage}
        onSend={sendMessage}
        onKeyPress={handleKeyPress}
        isConnected={isConnected}
      />
    </div>
  );
}
// frontend/pages/api/get-token.js
const jwt = require('jsonwebtoken');

export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { username } = req.body;
  
  if (!username) {
    return res.status(400).json({ error: 'Username is required' });
  }

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const wsUrl = process.env.LIVEKIT_URL;
  
  if (!apiKey || !apiSecret || !wsUrl) {
    return res.status(500).json({ 
      error: 'Missing LiveKit configuration',
      details: {
        apiKey: !apiKey ? 'Missing' : 'Present',
        apiSecret: !apiSecret ? 'Missing' : 'Present',
        wsUrl: !wsUrl ? 'Missing' : 'Present'
      }
    });
  }
  
  const now = Math.floor(Date.now() / 1000);
  const roomName = 'ai-chat-room';
  
  // Correct JWT payload for LiveKit
  const payload = {
    iss: apiKey,
    sub: username,
    nbf: now,
    exp: now + (6 * 60 * 60), // 6 hours
    video: {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true
    }
  };
  
  try {
    const token = jwt.sign(payload, apiSecret, {
      algorithm: 'HS256'
    });
    
    console.log('Generated token for user:', username);
    
    res.json({ 
      token, 
      wsUrl,
      roomName 
    });
    
  } catch (error) {
    console.error('Token generation error:', error);
    res.status(500).json({ 
      error: 'Failed to generate token',
      details: error.message
    });
  }
}
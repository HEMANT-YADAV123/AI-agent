import { Users, Bot, User } from 'lucide-react';


const ParticipantsList = ({ participants }) => {
  if (participants.length === 0) return null;
  
  return (
    <div className="bg-gray-50 border-b border-gray-200 px-6 py-3">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Users className="w-4 h-4" />
        <span className="font-medium">Online now:</span>
        <div className="flex flex-wrap gap-2">
          {participants.map((participant, index) => (
            <span
              key={participant}
              className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-full text-xs font-medium text-gray-700 border"
            >
              {participant === 'ai-agent' ? (
                <Bot className="w-3 h-3 text-blue-500" />
              ) : (
                <User className="w-3 h-3 text-gray-500" />
              )}
              {participant}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ParticipantsList;
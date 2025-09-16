import { Users } from 'lucide-react';
import Message from './Message';

const MessagesList = ({ messages, messagesEndRef }) => {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
      <div className="space-y-1">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500">No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((msg) => <Message key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default MessagesList;
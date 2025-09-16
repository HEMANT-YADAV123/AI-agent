import { Send } from 'lucide-react';


const MessageInput = ({ inputMessage, setInputMessage, onSend, onKeyPress, isConnected }) => {
  return (
    <div className="bg-white border-t border-gray-200 p-6">
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={onKeyPress}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected}
            className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-gray-50"
          />
        </div>
        <button
          onClick={onSend}
          disabled={!isConnected || !inputMessage.trim()}
          className="flex items-center justify-center w-12 h-12 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-full transition-all duration-200 hover:scale-105 disabled:scale-100"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default MessageInput;
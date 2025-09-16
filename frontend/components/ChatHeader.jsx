import { Users, LogOut } from 'lucide-react';


const ChatHeader = ({ username, participants, onDisconnect }) => {
  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <Users className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">AI Chat Room</h3>
            <p className="text-sm text-gray-500">Welcome, {username}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>{participants.length} online</span>
          </div>
          <button
            onClick={onDisconnect}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors duration-200"
          >
            <LogOut className="w-4 h-4" />
            Disconnect
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatHeader;
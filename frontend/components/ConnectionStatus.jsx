import { AlertCircle } from 'lucide-react';


const ConnectionStatus = ({ isConnecting, username, error }) => {
  if (!isConnecting) return null;
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
        <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Connecting to chat room...</h3>
        <p className="text-gray-600 mb-4">Username: <span className="font-medium">{username}</span></p>
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 max-w-sm mx-auto">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-red-700 text-sm">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionStatus;
import { Bot, User } from 'lucide-react';


const Message = ({ message }) => {
  const getMessageStyle = () => {
    if (message.isUser) {
      return {
        container: "ml-auto max-w-xs bg-blue-600 text-white",
        alignment: "flex-row-reverse"
      };
    } else if (message.isBot) {
      return {
        container: "mr-auto max-w-xs bg-white border border-gray-200",
        alignment: "flex-row"
      };
    } else if (message.isSystem) {
      return {
        container: "mx-auto max-w-sm bg-yellow-50 border border-yellow-200 text-yellow-800",
        alignment: "flex-row"
      };
    } else {
      return {
        container: "mr-auto max-w-xs bg-gray-100 border border-gray-200",
        alignment: "flex-row"
      };
    }
  };

  const style = getMessageStyle();

  return (
    <div className={`flex gap-3 mb-4 ${style.alignment}`}>
      <div className="flex-shrink-0">
        {message.isBot ? (
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <Bot className="w-4 h-4 text-blue-600" />
          </div>
        ) : message.isUser ? (
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
        ) : (
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-gray-600" />
          </div>
        )}
      </div>
      <div className={`rounded-2xl px-4 py-3 ${style.container}`}>
        <div className="text-xs opacity-75 mb-1 font-medium">
          {message.sender} • {message.timestamp.toLocaleTimeString()}
        </div>
        <div className="text-sm leading-relaxed">{message.message}</div>
      </div>
    </div>
  );
};

export default Message;
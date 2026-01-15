import React from 'react';
import { Bot, UserRound } from 'lucide-react';
import { Message as MessageType } from '../types/chat';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row animate-fade-in ${isUser ? 'message-row-user' : ''}`}>
      <div
        className={`message-bubble ${
          isUser ? 'message-bubble-user' : 'message-bubble-assistant'
        }`}
      >
        <div className="message-header">
          <span
            className={`message-avatar ${
              isUser ? 'message-avatar-user' : 'message-avatar-assistant'
            }`}
          >
            {isUser ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </span>
          <span className="message-author">{isUser ? 'You' : 'Assistant'}</span>
          <span className="message-time">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
        <p className="message-text">{message.content}</p>
      </div>
    </div>
  );
};

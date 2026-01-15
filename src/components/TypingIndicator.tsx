import React from 'react';
import { Bot } from 'lucide-react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="message-row animate-fade-in">
      <div className="message-bubble message-bubble-assistant">
        <div className="message-header">
          <span className="message-avatar message-avatar-assistant">
            <Bot className="h-4 w-4" />
          </span>
          <span className="message-author">Assistant</span>
          <span className="message-time">Typing</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span>Thinking</span>
          <div className="flex gap-1">
            <span
              className="h-2 w-2 rounded-full bg-slate-400/70 animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <span
              className="h-2 w-2 rounded-full bg-slate-400/70 animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <span
              className="h-2 w-2 rounded-full bg-slate-400/70 animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

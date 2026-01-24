import React from 'react';
import { Bot, UserRound, Volume2 } from 'lucide-react';
import { Message as MessageType } from '../types/chat';
import { isSpeechSynthesisSupported, speakText } from '../utils/voice';

interface MessageProps {
  message: MessageType;
}

type GuardrailPayload = {
  answer: string;
  evidence: string[];
  disclaimer: string;
};

const parseGuardrailPayload = (text: string): GuardrailPayload | null => {
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed) as Partial<GuardrailPayload>;
    if (
      !parsed ||
      typeof parsed.answer !== 'string' ||
      typeof parsed.disclaimer !== 'string'
    ) {
      return null;
    }

    const evidence = Array.isArray(parsed.evidence)
      ? parsed.evidence.filter((item) => typeof item === 'string')
      : [];

    return {
      answer: parsed.answer,
      evidence,
      disclaimer: parsed.disclaimer,
    };
  } catch (error) {
    return null;
  }
};

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const guardrailPayload = !isUser ? parseGuardrailPayload(message.content) : null;
  const displayText = guardrailPayload?.answer ?? message.content;
  const canSpeak =
    !isUser && isSpeechSynthesisSupported() && Boolean(displayText.trim());

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
          {canSpeak && (
            <button
              type="button"
              onClick={() => speakText(displayText)}
              className="speak-button"
              aria-label="Speak response"
            >
              <Volume2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <p className="message-text">{displayText}</p>
        {guardrailPayload && guardrailPayload.evidence.length > 0 && (
          <div className="message-section">
            <div className="message-section-title">Evidence</div>
            <ul className="message-evidence">
              {guardrailPayload.evidence.map((item, index) => (
                <li key={`${index}-${item.slice(0, 24)}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        {guardrailPayload && guardrailPayload.disclaimer && (
          <div className="message-section message-disclaimer">
            <div className="message-section-title">Disclaimer</div>
            <p className="message-disclaimer-text">{guardrailPayload.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
};

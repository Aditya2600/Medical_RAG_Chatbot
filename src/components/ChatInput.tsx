import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Mic, MicOff } from 'lucide-react';
import { getSpeechRecognition, isSpeechRecognitionSupported } from '../utils/voice';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isLoading, 
  disabled = false 
}) => {
  const [message, setMessage] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const baseMessageRef = useRef('');
  const finalTranscriptRef = useRef('');
  const ignoreOnEndRef = useRef(false);

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (isListening) {
      stopListening();
    }
    const trimmed = message.trim();
    if (trimmed && !isLoading && !disabled) {
      onSendMessage(trimmed);
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  useEffect(() => {
    setVoiceSupported(isSpeechRecognitionSupported());
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  const buildTranscript = useCallback((interim: string) => {
    const base = baseMessageRef.current.trimEnd();
    const parts = [base, finalTranscriptRef.current.trim(), interim.trim()].filter(Boolean);
    return parts.join(' ').trim();
  }, []);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    ignoreOnEndRef.current = true;
    recognitionRef.current.stop();
  }, []);

  const startListening = useCallback(() => {
    if (isLoading || disabled || isListening) return;
    const recognition = getSpeechRecognition();
    if (!recognition) {
      setVoiceError('Voice input is not supported in this browser.');
      return;
    }

    baseMessageRef.current = message;
    finalTranscriptRef.current = '';
    setVoiceError(null);

    if (typeof navigator !== 'undefined' && navigator.language) {
      recognition.lang = navigator.language;
    } else {
      recognition.lang = 'en-US';
    }
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0]?.transcript || '';
        if (result.isFinal) {
          finalTranscriptRef.current += `${transcript} `;
        } else {
          interimTranscript += `${transcript} `;
        }
      }

      const combined = buildTranscript(interimTranscript);
      setMessage(combined);
    };

    recognition.onerror = (event) => {
      const errorLabel = event.error ? `Voice error: ${event.error}` : 'Voice error';
      setVoiceError(errorLabel);
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;

      if (ignoreOnEndRef.current) {
        ignoreOnEndRef.current = false;
        return;
      }

      const finalMessage = buildTranscript('');
      if (!finalMessage) return;

      if (!baseMessageRef.current.trim()) {
        if (!isLoading && !disabled) {
          onSendMessage(finalMessage);
          setMessage('');
        }
      } else {
        setMessage(finalMessage);
      }
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  }, [buildTranscript, disabled, isListening, isLoading, message, onSendMessage]);

  useEffect(() => {
    if (isLoading && isListening) {
      stopListening();
    }
  }, [isLoading, isListening, stopListening]);

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const isDisabled = !message.trim() || isLoading || disabled || isListening;

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="input-shell">
        <textarea
          ref={textareaRef}
          className={`input-field ${
            isLoading || disabled || isListening ? 'cursor-not-allowed' : ''
          }`}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a clinical question..."
          disabled={isLoading || disabled || isListening}
          rows={1}
          aria-label="Chat message"
        />

        {voiceSupported && (
          <button
            type="button"
            onClick={toggleListening}
            disabled={isLoading || disabled}
            aria-pressed={isListening}
            aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
            className={`voice-button ${isListening ? 'voice-button-active' : ''}`}
          >
            {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>
        )}

        <button
          type="submit"
          disabled={isDisabled}
          aria-label="Send message"
          className="send-button"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </button>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>Enter to send - Shift+Enter for a new line</span>
        {voiceSupported && (
          <span className={`voice-status ${isListening ? 'voice-status-active' : ''}`}>
            {isListening ? 'Listening...' : 'Mic ready'}
          </span>
        )}
      </div>
      {voiceError && <div className="voice-error text-[11px]">{voiceError}</div>}
    </form>
  );
};

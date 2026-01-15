import { useState, useCallback, useEffect } from 'react';
import { Message, ChatState } from '../types/chat';
import { chatAPI } from '../utils/api';

export const useChat = () => {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  // Load initial messages on mount
  useEffect(() => {
    const loadMessages = async () => {
      try {
        setState(prev => ({ ...prev, isLoading: true, error: null }));
        const messages = await chatAPI.getMessages();
        setState(prev => ({ ...prev, messages, isLoading: false }));
      } catch (error) {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to load messages',
        }));
      }
    };

    loadMessages();
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const assistantId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const userMessage: Message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage, assistantMessage],
      isLoading: true,
      error: null,
    }));

    try {
      await chatAPI.sendMessageStream(content, (chunk) => {
        setState(prev => ({
          ...prev,
          messages: prev.messages.map(message =>
            message.id === assistantId
              ? { ...message, content: message.content + chunk }
              : message
          ),
        }));
      });
      setState(prev => ({
        ...prev,
        isLoading: false,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        messages: prev.messages.filter(message => message.id !== assistantId),
        isLoading: false,
        error: error instanceof Error ? error.message : 'An error occurred',
      }));
    }
  }, []);

  const clearMessages = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      await chatAPI.clearChat();
      setState(prev => ({
        ...prev,
        messages: [],
        isLoading: false,
        error: null,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to clear chat',
      }));
    }
  }, []);

  return {
    ...state,
    sendMessage,
    clearMessages,
  };
};

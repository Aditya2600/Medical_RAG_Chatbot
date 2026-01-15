import { Message } from '../types/chat';

const API_BASE_URL = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '');

const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

const createId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
};

export const chatAPI = {
  async sendMessage(question: string): Promise<Message[]> {
    const response = await fetch(buildUrl('/api/chat'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
      credentials: 'include',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || 'Failed to send message');
    }

    const data = await response.json();
    return this.transformMessages(data.messages || []);
  },

  async sendMessageStream(
    question: string,
    onDelta: (chunk: string) => void
  ): Promise<void> {
    const response = await fetch(buildUrl('/api/chat/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
      credentials: 'include',
    });

    if (!response.ok) {
      let errorMessage = 'Failed to send message';
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorMessage;
      } catch (error) {
        const text = await response.text().catch(() => '');
        if (text) {
          errorMessage = text;
        }
      }
      throw new Error(errorMessage);
    }

    if (!response.body) {
      const text = await response.text();
      if (text) {
        onDelta(text);
      }
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        if (chunk) {
          onDelta(chunk);
        }
      }
    }

    const remaining = decoder.decode();
    if (remaining) {
      onDelta(remaining);
    }
  },

  async getMessages(): Promise<Message[]> {
    const response = await fetch(buildUrl('/api/messages'), {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }

    const data = await response.json();
    return this.transformMessages(data.messages || []);
  },

  async clearChat(): Promise<void> {
    const response = await fetch(buildUrl('/api/clear'), {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to clear chat');
    }
  },

  // Transform Flask messages to our Message type
  transformMessages(flaskMessages: any[]): Message[] {
    return flaskMessages.map((msg) => {
      const parsedTimestamp = msg.timestamp ? new Date(msg.timestamp) : new Date();
      const timestamp = Number.isNaN(parsedTimestamp.getTime())
        ? new Date()
        : parsedTimestamp;

      return {
        id: msg.id || createId(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp,
      };
    });
  }
};

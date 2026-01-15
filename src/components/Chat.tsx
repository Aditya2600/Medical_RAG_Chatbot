import React, { useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Moon,
  Plus,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Sun,
} from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { TypingIndicator } from './TypingIndicator';

const promptSuggestions = [
  'Summarize the latest guidance for hypertension management.',
  'What are common side effects of metformin?',
  'Explain the differences between Type 1 and Type 2 diabetes.',
  'How should vitamin D deficiency be evaluated?',
  'List warning signs that require urgent care for chest pain.',
  'Outline initial management for acute asthma exacerbation.',
];

const getInitialTheme = () => {
  if (typeof window === 'undefined') return false;
  const stored = window.localStorage.getItem('theme');
  if (stored) return stored === 'dark';
  if (window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return false;
};

export const Chat: React.FC = () => {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastMessage = messages[messages.length - 1];
  const showTyping =
    isLoading &&
    messages.length > 0 &&
    lastMessage?.role === 'assistant' &&
    !lastMessage?.content;
  const [isDark, setIsDark] = useState(getInitialTheme);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.dataset.theme = isDark ? 'dark' : 'light';
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }
  }, [isDark]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSuggestion = (prompt: string) => {
    if (isLoading) return;
    sendMessage(prompt);
  };

  return (
    <div className="app-shell">
      <div className="flex min-h-screen">
        <aside className="sidebar-surface hidden w-72 flex-col px-6 py-8 lg:flex">
          <div className="flex items-center gap-3">
            <div className="sidebar-logo">
              <Stethoscope className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/70">
                Medical RAG
              </p>
              <h1 className="font-display text-lg text-white">
                Clinical Chat
              </h1>
            </div>
          </div>

          <button
            onClick={clearMessages}
            disabled={isLoading}
            className={`mt-6 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition ${
              isLoading
                ? 'cursor-not-allowed border-white/10 text-white/40'
                : 'border-emerald-300/40 text-emerald-100 hover:border-emerald-200 hover:bg-emerald-500/10'
            }`}
          >
            <Plus className="h-4 w-4" />
            New chat
          </button>

          <div className="mt-10 space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/60">
              Quick prompts
            </p>
            {promptSuggestions.slice(0, 3).map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleSuggestion(prompt)}
                disabled={isLoading}
                className={`sidebar-card w-full text-left text-sm transition ${
                  isLoading
                    ? 'cursor-not-allowed text-white/40'
                    : 'text-white/80 hover:text-white'
                }`}
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="mt-auto space-y-4">
            <div className="sidebar-card">
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-emerald-200/70">
                <span>Status</span>
                <span className="flex items-center gap-2 text-[11px] font-semibold text-emerald-100/80">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      isLoading ? 'bg-amber-300 animate-pulse' : 'bg-emerald-300'
                    }`}
                  />
                  {isLoading ? 'Thinking' : 'Ready'}
                </span>
              </div>
              <div className="mt-3 space-y-2 text-sm text-white/80">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-emerald-200" />
                  Grounded in your PDFs
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-200" />
                  Session memory enabled
                </div>
              </div>
            </div>
            <div className="sidebar-card text-xs text-white/70">
              This assistant supports research and reference, not medical advice.
            </div>
          </div>
        </aside>

        <main className="flex flex-1 flex-col">
          <header className="chat-header px-5 py-6 md:px-10">
            <div className="flex items-center gap-3 lg:hidden">
              <div className="sidebar-logo">
                <Stethoscope className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--text-muted)]">
                  Medical RAG
                </p>
                <h1 className="font-display text-lg text-slate-900">
                  Clinical Chat
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-semibold text-slate-500">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${
                    isLoading ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'
                  }`}
                />
                {isLoading ? 'Synthesizing answer' : 'Ready to chat'}
              </div>
              <div className="flex items-center gap-2">
                <span className="hidden text-[10px] uppercase tracking-[0.24em] lg:inline">
                  Dark mode
                </span>
                <button
                  type="button"
                  onClick={() => setIsDark((prev) => !prev)}
                  className="theme-toggle"
                  aria-pressed={isDark}
                  aria-label="Toggle dark mode"
                >
                  <span className="theme-toggle-thumb">
                    {isDark ? <Moon className="h-3 w-3" /> : <Sun className="h-3 w-3" />}
                  </span>
                </button>
              </div>
            </div>
          </header>

          <section className="chat-body flex-1 px-5 pb-6 md:px-10">
            <div className="chat-panel mx-auto flex h-full w-full max-w-3xl flex-col">
              <div className="chat-scroll flex-1 space-y-6 pr-2">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <div className="space-y-3">
                      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                        Welcome
                      </p>
                      <h2 className="font-display text-3xl text-slate-900">
                        Start a new clinical conversation.
                      </h2>
                      <p className="text-sm text-slate-600">
                        Ask about diagnoses, treatment guidelines, or medical
                        literature. The assistant retrieves evidence from your
                        PDF library before responding.
                      </p>
                    </div>
                    <div className="mt-6 grid gap-3 md:grid-cols-2">
                      {promptSuggestions.slice(0, 4).map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => handleSuggestion(prompt)}
                          disabled={isLoading}
                          className={`prompt-card ${
                            isLoading ? 'cursor-not-allowed opacity-60' : ''
                          }`}
                        >
                          <span className="flex items-center justify-between gap-3">
                            <span>{prompt}</span>
                            <Activity className="h-4 w-4 text-emerald-500" />
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((message) => (
                      <Message key={message.id} message={message} />
                    ))}
                  </>
                )}
                {showTyping && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </section>

          <section className="chat-footer px-5 pb-8 md:px-10">
            <div className="mx-auto w-full max-w-3xl space-y-3">
              {error && (
                <div className="error-card flex items-center gap-3 rounded-2xl px-4 py-3 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              )}
              <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
              <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">
                Grounded responses. Not a substitute for professional care.
              </p>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

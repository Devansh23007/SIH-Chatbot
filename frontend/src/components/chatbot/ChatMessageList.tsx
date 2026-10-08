import { useEffect, useRef } from 'react';
import type { ChatErrorCode, ChatMessage as Message } from '../../types/chatbot';
import { buildFollowUps, prefersReducedMotion } from '../../utils/chatbotUtils';
import { ChatErrorState } from './ChatErrorState';
import { ChatMessage } from './ChatMessage';
import { QuickSuggestions } from './QuickSuggestions';
import { TypingIndicator } from './TypingIndicator';

interface Props {
  messages: Message[];
  isTyping: boolean;
  error: ChatErrorCode | null;
  onRetry: (id: string) => void;
  onSelectSuggestion: (text: string) => void;
}

export function ChatMessageList({ messages, isTyping, error, onRetry, onSelectSuggestion }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'end' });
  }, [messages, isTyping, error]);

  const last = messages[messages.length - 1];
  // Follow-ups appear after each assistant reply: backend-provided if present, otherwise topic-based.
  let followUps: string[] = [];
  if (!isTyping && !error && last?.role === 'assistant') {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    followUps = last.suggestions?.length ? last.suggestions : buildFollowUps(lastUser?.content ?? '', last.blocks);
  }

  const failed = error && last?.status === 'failed' ? last : null;

  return (
    <div role="log" aria-live="polite" aria-relevant="additions" className="cb-list">
      {messages.map((m) => <ChatMessage key={m.id} message={m} />)}
      {isTyping && <TypingIndicator />}
      {followUps.length > 0 && <QuickSuggestions variant="chips" suggestions={followUps} onSelect={onSelectSuggestion} />}
      {(failed || (error === 'auth' && !failed)) && (
        <ChatErrorState code={error!} onRetry={failed ? () => onRetry(failed.id) : undefined} />
      )}
      <div ref={endRef} />
    </div>
  );
}

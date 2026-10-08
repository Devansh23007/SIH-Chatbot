import { useEffect, type CSSProperties } from 'react';
import { chatbotConfig } from '../../config/chatbotConfig';
import type { useChat } from '../../hooks/useChat';
import type { ResizableWindow } from '../../hooks/useResizableWindow';
import type { Theme } from '../../hooks/useTheme';
import type { UserProfile } from '../../types/user';
import { ChatErrorState } from './ChatErrorState';
import { ChatInput } from './ChatInput';
import { ChatMessageList } from './ChatMessageList';
import { ChatbotHeader } from './ChatbotHeader';
import { EmptyChatState } from './EmptyChatState';

interface Props {
  chat: ReturnType<typeof useChat>;
  profile: UserProfile | null;
  theme: Theme;
  closing: boolean;
  resize: ResizableWindow;
  onToggleTheme: () => void;
  onMinimize: () => void;
  onClose: () => void;
}

export function ChatbotWindow({ chat, profile, theme, closing, resize, onToggleTheme, onMinimize, onClose }: Props) {
  const { messages, isTyping, isLoading, error, sendMessage, retryMessage, clearChat } = chat;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onMinimize();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onMinimize]);

  const sizeVars = resize.size
    ? ({ '--cb-w': `${resize.size.w}px`, '--cb-h': `${resize.size.h}px` } as CSSProperties)
    : undefined;

  return (
    <section
      ref={resize.windowRef} style={sizeVars} className="cb-window" role="dialog"
      aria-label={chatbotConfig.assistantName} data-state={closing ? 'closing' : 'open'}
    >
      <button
        type="button" className="cb-resize" onPointerDown={resize.startResize} onKeyDown={resize.onHandleKeyDown}
        aria-label="Resize chat window. Drag, or use the arrow keys." title="Drag to resize"
      />
      <ChatbotHeader
        theme={theme} expanded={resize.expanded} onToggleTheme={onToggleTheme} onToggleExpand={resize.toggleExpand}
        onNewChat={clearChat} onMinimize={onMinimize} onClose={onClose}
      />
      <div className="cb-body">
        {isLoading ? (
          <p className="cb-loading" role="status">Loading conversation…</p>
        ) : messages.length === 0 ? (
          <>
            <EmptyChatState profile={profile} onSelect={sendMessage} />
            {error && <ChatErrorState code={error} onRetry={() => clearChat()} />}
          </>
        ) : (
          <ChatMessageList messages={messages} isTyping={isTyping} error={error} onRetry={retryMessage} onSelectSuggestion={sendMessage} />
        )}
      </div>
      <ChatInput onSend={sendMessage} disabled={isTyping || isLoading} />
    </section>
  );
}

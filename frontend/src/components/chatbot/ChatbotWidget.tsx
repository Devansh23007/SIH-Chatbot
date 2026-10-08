import { useEffect, useState } from 'react';
import './chatbot.css';
import { chatbotConfig } from '../../config/chatbotConfig';
import { useChat } from '../../hooks/useChat';
import { useChatbot } from '../../hooks/useChatbot';
import { useResizableWindow } from '../../hooks/useResizableWindow';
import { useTheme, type Theme } from '../../hooks/useTheme';
import type { UserProfile } from '../../types/user';
import { isTeaserDismissed, rememberTeaserDismissed } from '../../utils/chatbotUtils';
import { ChatbotButton } from './ChatbotButton';
import { ChatbotTeaser } from './ChatbotTeaser';
import { ChatbotWindow } from './ChatbotWindow';

export interface ChatbotWidgetProps {
  /** Optional: pass the user from NCCT's auth context. If omitted, userService fetches the profile. */
  user?: UserProfile | null;
  /** Optional: drive the theme from NCCT's theme provider. */
  theme?: Theme;
  onThemeChange?: (theme: Theme) => void;
}

/** Drop-in entry point: <ChatbotWidget /> on the NCCT home page. */
export function ChatbotWidget({ user, theme: themeProp, onThemeChange }: ChatbotWidgetProps) {
  const { isOpen, isClosing, open, close, profile } = useChatbot(user);
  const chat = useChat();
  const resize = useResizableWindow();
  const { theme, toggleTheme } = useTheme(themeProp, onThemeChange);
  const [wasOpened, setWasOpened] = useState(false);
  const [teaserDismissed, setTeaserDismissed] = useState(isTeaserDismissed);
  const { clearChat, sendMessage } = chat;

  useEffect(() => { if (isOpen) setWasOpened(true); }, [isOpen]);

  const dismissTeaser = () => { setTeaserDismissed(true); rememberTeaserDismissed(); };
  const openChat = () => { dismissTeaser(); open(); };
  // Teaser buttons: open the window and send the question to the backend like any typed message.
  const askFromTeaser = (question: string) => { openChat(); sendMessage(question); };
  // Minimize keeps the conversation; Close ends it so the next open starts fresh.
  const closeAndReset = () => { clearChat(); close(); };

  return (
    <div className="ncct-cb" data-theme={theme} style={{ zIndex: chatbotConfig.zIndex }}>
      {isOpen ? (
        <ChatbotWindow
          chat={chat} profile={profile} theme={theme} closing={isClosing} resize={resize}
          onToggleTheme={toggleTheme} onMinimize={close} onClose={closeAndReset}
        />
      ) : (
        <>
          {!teaserDismissed && <ChatbotTeaser onAsk={askFromTeaser} onDismiss={dismissTeaser} />}
          <ChatbotButton onClick={openChat} restoreFocus={wasOpened} />
        </>
      )}
    </div>
  );
}

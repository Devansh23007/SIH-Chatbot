import { useCallback, useEffect, useRef, useState } from 'react';
import type { UserProfile } from '../types/user';
import { prefersReducedMotion } from '../utils/chatbotUtils';

const CLOSE_ANIMATION_MS = 160;

/**
 * Widget open/close state. The career backend has no user-profile endpoint yet,
 * so the profile only comes from the host app (<ChatbotWidget user={...} />) or stays null.
 */
export function useChatbot(userFromHost?: UserProfile | null) {
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const profile = userFromHost ?? null;

  const open = useCallback(() => {
    window.clearTimeout(timer.current);
    setIsClosing(false);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    if (prefersReducedMotion()) return setIsOpen(false);
    setIsClosing(true);
    timer.current = window.setTimeout(() => { setIsOpen(false); setIsClosing(false); }, CLOSE_ANIMATION_MS);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return { isOpen, isClosing, open, close, profile };
}
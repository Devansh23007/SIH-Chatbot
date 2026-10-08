import { useCallback, useEffect, useRef, useState } from 'react';
import { chatService } from '../services/chatService';
import { ChatError, type ChatErrorCode, type ChatMessage, type ChatReply } from '../types/chatbot';
import { createId } from '../utils/chatbotUtils';

const toAssistantMessage = (r: ChatReply): ChatMessage => ({
  id: r.messageId ?? createId(),
  role: 'assistant',
  content: r.content ?? '',
  blocks: r.blocks,
  suggestions: r.suggestions,
  createdAt: r.createdAt ?? new Date().toISOString(),
  status: 'sent',
});

/** All chat state and logic. Components stay purely visual. */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false); // loading a stored conversation
  const [isTyping, setIsTyping] = useState(false); // waiting for the assistant
  const [error, setError] = useState<ChatErrorCode | null>(null);

  const conversationRef = useRef<string | null>(null);
  const typingRef = useRef(false);
  const requestRef = useRef(0); // invalidates in-flight replies after clear/new chat

  // Unsolicited messages pushed by a socket/streaming transport.
  useEffect(
    () => chatService.subscribe((reply) => {
      conversationRef.current = reply.conversationId;
      setConversationId(reply.conversationId);
      setMessages((prev) => [...prev, toAssistantMessage(reply)]);
    }),
    [],
  );

  const deliver = useCallback(async (messageId: string, text: string) => {
    const request = ++requestRef.current;
    typingRef.current = true;
    setIsTyping(true);
    setError(null);
    try {
      const reply = await chatService.sendMessage({ message: text, conversationId: conversationRef.current });
      if (request !== requestRef.current) return;
      if (!reply?.content?.trim() && !reply?.blocks?.length) throw new ChatError('empty');
      conversationRef.current = reply.conversationId;
      setConversationId(reply.conversationId);
      setMessages((prev) => [
        ...prev.map((m) => (m.id === messageId ? { ...m, status: 'sent' as const, errorCode: undefined } : m)),
        toAssistantMessage(reply),
      ]);
    } catch (e) {
      if (request !== requestRef.current) return;
      const code = e instanceof ChatError ? e.code : 'server';
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, status: 'failed', errorCode: code } : m)));
      setError(code);
    } finally {
      if (request === requestRef.current) {
        typingRef.current = false;
        setIsTyping(false);
      }
    }
  }, []);

  const sendMessage = useCallback((text: string) => {
    const content = text.trim();
    if (!content || typingRef.current) return;
    const message: ChatMessage = { id: createId(), role: 'user', content, createdAt: new Date().toISOString(), status: 'pending' };
    setMessages((prev) => [...prev, message]);
    void deliver(message.id, content);
  }, [deliver]);

  const retryMessage = useCallback((id: string) => {
    if (typingRef.current) return;
    const target = messages.find((m) => m.id === id && m.status === 'failed');
    if (!target) return;
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'pending', errorCode: undefined } : m)));
    void deliver(id, target.content);
  }, [messages, deliver]);

  const clearChat = useCallback(() => {
    requestRef.current++;
    conversationRef.current = null;
    typingRef.current = false;
    setMessages([]);
    setConversationId(null);
    setIsTyping(false);
    setError(null);
  }, []);

  /** INTEGRATION POINT (history): call with an id from chatService.listConversations(). */
  const loadConversation = useCallback(async (id: string) => {
    clearChat();
    setIsLoading(true);
    try {
      const detail = await chatService.loadConversation(id);
      conversationRef.current = detail.conversationId;
      setConversationId(detail.conversationId);
      setMessages(detail.messages);
    } catch (e) {
      setError(e instanceof ChatError ? e.code : 'server');
    } finally {
      setIsLoading(false);
    }
  }, [clearChat]);

  return { messages, conversationId, sendMessage, retryMessage, clearChat, loadConversation, isLoading, isTyping, error };
}

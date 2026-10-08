import { chatbotConfig } from '../config/chatbotConfig';
import { ChatError, type ChatReply, type ChatTransport, type SendMessageRequest } from '../types/chatbot';
import { httpJson } from './http';
import { buildMockReply } from './mock/mockData';

const url = (path: string) => `${chatbotConfig.apiBaseUrl}${path}`;
const noopUnsubscribe = () => () => undefined;

/** REST: one request, one full reply. */
export const restTransport: ChatTransport = {
  sendMessage: (req) => httpJson<ChatReply>(url(chatbotConfig.endpoints.message), { method: 'POST', body: req }),
  subscribeToMessage: noopUnsubscribe,
  disconnect: () => undefined,
};

/**
 * Socket.IO / WebSocket adapter. No dependency on socket.io-client: the backend developer
 * creates the socket and passes it in (anything with emit/on/off/disconnect works).
 *
 * INTEGRATION POINT (real-time), e.g. in chatService.ts:
 *   import { io } from 'socket.io-client';
 *   const transport = createSocketTransport(io(chatbotConfig.socketUrl, { withCredentials: true }));
 *
 * Event names are placeholders: 'chat:message' (client -> server, with ack reply),
 * 'chat:reply' (server -> client push). Align them with the backend contract.
 */
export interface SocketLike {
  emit(event: string, payload: unknown, ack?: (reply: ChatReply | { error: string }) => void): void;
  on(event: string, handler: (...args: any[]) => void): void;
  off(event: string, handler: (...args: any[]) => void): void;
  disconnect(): void;
  connected?: boolean;
}

export function createSocketTransport(socket: SocketLike): ChatTransport {
  return {
    sendMessage: (req: SendMessageRequest) =>
      new Promise<ChatReply>((resolve, reject) => {
        if (socket.connected === false) return reject(new ChatError('disconnected'));
        const timer = setTimeout(() => reject(new ChatError('timeout')), chatbotConfig.requestTimeoutMs);
        socket.emit('chat:message', req, (reply) => {
          clearTimeout(timer);
          if ('error' in reply) reject(new ChatError(reply.error === 'unauthorized' ? 'auth' : 'server'));
          else resolve(reply);
        });
      }),
    subscribeToMessage(handler) {
      socket.on('chat:reply', handler);
      return () => socket.off('chat:reply', handler);
    },
    disconnect: () => socket.disconnect(),
  };
}

/** Mock: simulates 500-1000ms latency and the error states. */
export const mockTransport: ChatTransport = {
  async sendMessage({ message, conversationId }) {
    await new Promise((r) => setTimeout(r, 500 + Math.random() * 500));
    if (message.includes('/fail')) throw new ChatError('network');
    if (message.includes('/auth')) throw new ChatError('auth');
    return buildMockReply(message, conversationId ?? `mock-conv-${Date.now()}`);
  },
  subscribeToMessage: noopUnsubscribe,
  disconnect: () => undefined,
};

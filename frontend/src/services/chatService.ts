import { chatbotConfig } from '../config/chatbotConfig';
import type {
  ChatReply, ChatTransport, ConversationDetail, ConversationSummary, SendMessageRequest,
} from '../types/chatbot';
import { careerTransport } from './careerTransport';
import { mockTransport } from './chatTransport';
import { httpJson } from './http';

/**
 * Transport: our FastAPI career backend.
 * Put VITE_USE_MOCK=true in .env to get the old fake replies back for UI work.
 */
function createTransport(): ChatTransport {
  if (import.meta.env.VITE_USE_MOCK === 'true') return mockTransport;
  return careerTransport;
}

let transport = createTransport();
const isMock = () => chatbotConfig.transport === 'mock';
const api = (p: string) => `${chatbotConfig.apiBaseUrl}${p}`;

export const chatService = {
  /** The backend identifies the user from the session; only message + conversationId are sent. */
  sendMessage: (req: SendMessageRequest): Promise<ChatReply> => transport.sendMessage(req),
  subscribe: (handler: (reply: ChatReply) => void) => transport.subscribeToMessage(handler),
  disconnect: () => transport.disconnect(),
  /** Test/host hook: swap the transport at runtime. */
  useTransport(next: ChatTransport) { transport = next; },

  async listConversations(): Promise<ConversationSummary[]> {
    if (isMock()) return [];
    return httpJson(api(chatbotConfig.endpoints.conversations));
  },
  async loadConversation(id: string): Promise<ConversationDetail> {
    if (isMock()) return { conversationId: id, messages: [] };
    return httpJson(api(chatbotConfig.endpoints.conversation(id)));
  },
};
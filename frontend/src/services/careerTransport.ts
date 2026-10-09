import { ChatError, type ChatReply, type ChatTransport, type SendMessageRequest } from '../types/chatbot';
import { createId, INITIAL_SUGGESTIONS } from '../utils/chatbotUtils';
import { httpJson } from './http';

/** Backend URL. Set VITE_API_URL in the frontend's .env (see .env.example). */
const API_BASE = ((import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000').replace(/\/$/, '');
const noopUnsubscribe = () => () => undefined;

/** Shape returned by the FastAPI endpoint POST /api/career-chat */
interface CareerApiReply {
  conversation_id: string | null;
  response: string;
  source: 'knowledge_base' | 'knowledge_base_closest' | 'general' | 'small_talk' | 'off_topic' | 'error';
  career: string | null;
  similarity: number | null;
  related_careers: { career: string; similarity: number }[];
}

/** Follow-up chips: depth on the matched career first, then one similar career. */
function buildSuggestions(data: CareerApiReply, asked: string): string[] {
  const text = asked.toLowerCase();
  const career = data.career;

  if ((data.source === 'knowledge_base' || data.source === 'knowledge_base_closest') && career) {
    const options = [
      { skip: /course|certif/, label: `Courses and certifications for ${career}` },
      { skip: /skill/, label: `Skills needed for ${career}` },
      { skip: /entry|fresher|job|role/, label: `Entry-level roles for ${career}` },
      { skip: /progress|growth|senior|future/, label: `Career growth in ${career}` },
    ];
    const own = options.filter((o) => !o.skip.test(text)).map((o) => o.label).slice(0, 3);
    const similar = data.related_careers
      .filter((r) => r.career !== career)
      .slice(0, 1)
      .map((r) => `Tell me about ${r.career}`);
    return [...own, ...similar];
  }

  // Career we don't have: offer the closest careers we DO have
  if (data.source === 'general' && data.related_careers.length) {
    return data.related_careers.slice(0, 3).map((r) => `Tell me about ${r.career}`);
  }

  // Greetings / off-topic: show the starter questions
  return INITIAL_SUGGESTIONS.slice(0, 3);
}

/** Talks to our FastAPI backend and converts its reply into the widget's ChatReply. */
export const careerTransport: ChatTransport = {
  async sendMessage(req: SendMessageRequest): Promise<ChatReply> {
    const data = await httpJson<CareerApiReply>(`${API_BASE}/api/career-chat`, {
      method: 'POST',
      // conversation_id lets the backend remember the recent messages of this chat.
      body: { message: req.message, conversation_id: req.conversationId ?? null },
      timeoutMs: 45_000, // AI replies can take a few seconds, longer if a provider retries
    });

    // Backend could not generate an answer: show the widget's own error + Retry button
    if (data.source === 'error') throw new ChatError('server');

    return {
      // The backend creates the id on the first message; keep using it for chat memory
      conversationId: data.conversation_id ?? req.conversationId ?? createId(),
      content: data.response,
      suggestions: buildSuggestions(data, req.message),
      createdAt: new Date().toISOString(),
    };
  },
  subscribeToMessage: noopUnsubscribe,
  disconnect: () => undefined,
};
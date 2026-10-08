/**
 * ===== BACKEND CONTRACT (frontend's expectations) =====
 * POST {VITE_CHAT_API_URL}/chat/message
 *   request : { message: string, conversationId?: string | null }   // user identified by session/cookie, not by payload
 *   response: ChatReply  // may include `suggestions: string[]` (follow-up chips); optional
 * GET  .../chat/conversations            -> ConversationSummary[]
 * GET  .../chat/conversations/:id        -> { conversationId, messages: ChatMessage[] }
 * HTTP 401/403 => authentication failure. Any other non-2xx => generic server error.
 * Endpoint paths are centralised in config/chatbotConfig.ts.
 */
export type ChatRole = 'user' | 'assistant';
export type MessageStatus = 'pending' | 'sent' | 'failed';
export type ChatErrorCode = 'network' | 'timeout' | 'auth' | 'empty' | 'server' | 'disconnected';

export interface CareerRecommendation {
  type: 'career_recommendation';
  title: string;
  description?: string;
  matchPercentage?: number;
  requiredSkills: string[];
  missingSkills: string[];
  url?: string;
}
export interface CourseRecommendation {
  type: 'course_recommendation';
  title: string;
  provider?: string;
  description?: string;
  level?: string;
  duration?: string;
  skills?: string[];
  url?: string;
}
export interface SkillGap {
  type: 'skill_gap';
  targetRole?: string;
  missingSkills: string[];
  partialSkills?: string[];
}
export interface LearningPath {
  type: 'learning_path';
  title: string;
  steps: { title: string; description?: string; duration?: string }[];
}
export interface JobRole {
  type: 'job_role';
  title: string;
  company?: string;
  location?: string;
  description?: string;
  skills?: string[];
  url?: string;
}
export type RecommendationBlock =
  | CareerRecommendation
  | CourseRecommendation
  | SkillGap
  | LearningPath
  | JobRole;

export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** Plain text with light markdown (**bold**, [links](https://..), "- " bullets, "1. " lists). */
  content: string;
  createdAt: string; // ISO
  status: MessageStatus;
  blocks?: RecommendationBlock[];
  /** Optional follow-up prompts from the backend; if absent the UI uses generic topic-based ones. */
  suggestions?: string[];
  errorCode?: ChatErrorCode;
}

export interface SendMessageRequest {
  message: string;
  conversationId?: string | null;
}
export interface ChatReply {
  conversationId: string;
  messageId?: string;
  content: string;
  blocks?: RecommendationBlock[];
  /** Optional: context-aware follow-up questions chosen by the backend/AI. */
  suggestions?: string[];
  createdAt?: string;
}
export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: string;
}
export interface ConversationDetail {
  conversationId: string;
  messages: ChatMessage[];
}

/** Implemented by REST, Socket.IO/WebSocket and mock transports. */
export interface ChatTransport {
  sendMessage(request: SendMessageRequest): Promise<ChatReply>;
  /** Server-pushed assistant messages (streaming/socket). Returns an unsubscribe function. */
  subscribeToMessage(handler: (reply: ChatReply) => void): () => void;
  disconnect(): void;
}

export class ChatError extends Error {
  code: ChatErrorCode;
  constructor(code: ChatErrorCode) {
    super(code);
    this.name = 'ChatError';
    this.code = code;
  }
}

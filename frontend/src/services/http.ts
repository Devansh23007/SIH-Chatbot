import { chatbotConfig } from '../config/chatbotConfig';
import { ChatError } from '../types/chatbot';

type AuthHeaders = () => Record<string, string>;
let getAuthHeaders: AuthHeaders = () => ({});

/**
 * INTEGRATION POINT (auth): sessions with cookies work out of the box (credentials: 'include').
 * If NCCT uses bearer tokens, call this once from the host app, e.g.
 *   configureChatbotHttp({ getAuthHeaders: () => ({ Authorization: `Bearer ${auth.token}` }) })
 * so tokens never appear in chatbot UI components.
 */
export function configureChatbotHttp(opts: { getAuthHeaders: AuthHeaders }) {
  getAuthHeaders = opts.getAuthHeaders;
}

export async function httpJson<T>(
  url: string,
  opts: { method?: 'GET' | 'POST'; body?: unknown; timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? chatbotConfig.requestTimeoutMs);
  try {
    const res = await fetch(url, {
      method: opts.method ?? 'GET',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...getAuthHeaders() },
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: controller.signal,
    });
    if (res.status === 401 || res.status === 403) throw new ChatError('auth');
    if (!res.ok) throw new ChatError('server');
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ChatError) throw e;
    if ((e as Error).name === 'AbortError') throw new ChatError('timeout');
    throw new ChatError('network');
  } finally {
    clearTimeout(timer);
  }
}

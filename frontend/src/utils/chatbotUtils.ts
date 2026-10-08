import type { RecommendationBlock } from '../types/chatbot';
import type { UserProfile } from '../types/user';

export const createId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const formatTime = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(iso));

/** Only allow http(s) links from backend content. */
export const safeUrl = (url?: string) => (url && /^https?:\/\//i.test(url) ? url : undefined);

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const getFirstName = (profile: UserProfile | null) => profile?.name?.trim().split(/\s+/)[0] ?? '';

export function buildGreeting(profile: UserProfile | null) {
  const name = getFirstName(profile);
  return `Hi${name ? ` ${name}` : ' there'}! 👋\n\nI'm your AI Career Guidance Assistant.\n\nI can help you explore careers, the education and skills they need, useful courses and certifications, and entry-level roles.\n\nWhich career are you curious about?`;
}

/** Same for every user: shown before the conversation starts. */
export const INITIAL_SUGGESTIONS = [
  'How do I become a pilot?',
  'What skills does a graphic designer need?',
  'Courses and certifications for Data Engineer',
  'What does an architect do?',
  'Tell me about becoming a doctor',
];

type Topic = 'plan' | 'courses' | 'demand' | 'jobs' | 'skills' | 'career' | 'general';

const FOLLOW_UPS: Record<Topic, string[]> = {
  career: ['Which skills do I need for this career?', 'Show me a learning plan for this role', 'Recommend courses for this career', 'What jobs are available in this field?'],
  skills: ['Recommend courses to close these gaps', 'Create a learning plan for me', 'Which of these skills is most in demand?', 'How long will it take to learn these?'],
  courses: ['Which course should I start with?', 'What skills will these courses add?', 'Show me a learning plan with these courses', 'What careers do these courses lead to?'],
  jobs: ['What skills do I need for these roles?', 'How can I prepare for this role?', 'What is the career path from here?', 'Recommend courses for this role'],
  demand: ['Which of these skills match my profile?', 'Recommend courses for these skills', 'What careers use these skills?'],
  plan: ['Recommend courses for the first step', 'How long will this plan take?', 'What jobs can I apply to after this?'],
  general: ['Suggest a career path for me', 'Identify my skill gaps', 'Recommend courses for my career'],
};

const BLOCK_TOPIC: Record<RecommendationBlock['type'], Topic> = {
  career_recommendation: 'career', course_recommendation: 'courses', skill_gap: 'skills', learning_path: 'plan', job_role: 'jobs',
};

function detectTopic(userText: string, blocks?: RecommendationBlock[]): Topic {
  if (blocks?.length) return BLOCK_TOPIC[blocks[0].type];
  const t = userText.toLowerCase();
  if (/what is|who are you|what can you do/.test(t)) return 'general';
  if (/\b(plan|roadmap|learning path)\b/.test(t)) return 'plan';
  if (/course|certif/.test(t)) return 'courses';
  if (/demand|trend|market/.test(t)) return 'demand';
  if (/\bjobs?\b|role|opportunit|hiring|interview/.test(t)) return 'jobs';
  if (/gap|improve|skill|learn/.test(t)) return 'skills';
  if (/career|path/.test(t)) return 'career';
  return 'general';
}

/**
 * Fallback follow-ups when the backend sends no `suggestions`. Static prompts picked by topic only;
 * the AI-driven version should come from the backend (ChatReply.suggestions).
 */
export function buildFollowUps(lastUserText: string, blocks?: RecommendationBlock[]): string[] {
  const asked = lastUserText.trim().toLowerCase();
  return FOLLOW_UPS[detectTopic(lastUserText, blocks)].filter((s) => s.toLowerCase() !== asked).slice(0, 4);
}

// Teaser dismissal is a harmless UI flag, kept per browser tab session only.
const TEASER_KEY = 'ncct-career-ai-teaser-dismissed';
export const isTeaserDismissed = () => {
  try { return sessionStorage.getItem(TEASER_KEY) === '1'; } catch { return false; }
};
export const rememberTeaserDismissed = () => {
  try { sessionStorage.setItem(TEASER_KEY, '1'); } catch { /* storage unavailable: ignore */ }
};
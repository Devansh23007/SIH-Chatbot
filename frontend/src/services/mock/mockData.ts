// MOCK ONLY. Delete this folder once the real backend is connected.
import type { ChatReply, RecommendationBlock } from '../../types/chatbot';
import type { UserProfile } from '../../types/user';

export const mockProfile: UserProfile = {
  id: 'mock-1',
  name: 'Aarav Sharma',
  education: 'B.Tech',
  branch: 'Computer Science',
  year: 3,
  skills: ['JavaScript', 'React', 'Python'],
  interests: ['Web Development', 'Artificial Intelligence'],
  careerInterests: ['Software Development', 'AI Engineering'],
};

const blocks: Record<string, RecommendationBlock[]> = {
  career: [
    {
      type: 'career_recommendation',
      title: 'Full-Stack Developer',
      description: 'Builds both the interface and the server side of web products.',
      matchPercentage: 87,
      requiredSkills: ['React', 'JavaScript', 'Node.js', 'SQL'],
      missingSkills: ['Node.js', 'SQL', 'Testing'],
    },
  ],
  course: [
    { type: 'course_recommendation', title: 'Backend Development with Node.js', provider: 'NCCT Learning', level: 'Intermediate', duration: '6 weeks', skills: ['Node.js', 'REST APIs'] },
  ],
  gap: [{ type: 'skill_gap', targetRole: 'Full-Stack Developer', missingSkills: ['SQL', 'Testing'], partialSkills: ['TypeScript'] }],
  plan: [
    {
      type: 'learning_path',
      title: 'Path to Full-Stack Developer',
      steps: [
        { title: 'Strengthen TypeScript', duration: '2 weeks' },
        { title: 'Learn Node.js and REST APIs', duration: '4 weeks' },
        { title: 'Add SQL and testing', duration: '3 weeks' },
      ],
    },
  ],
  job: [{ type: 'job_role', title: 'Junior Frontend Developer', company: 'Sample Company', location: 'Remote', skills: ['React', 'JavaScript'] }],
};

export function buildMockReply(message: string, conversationId: string): ChatReply {
  const m = message.toLowerCase();
  const base = { conversationId, messageId: `mock-${Date.now()}` };

  if (/what is.*(ncct|career ai|assistant)/.test(m)) {
    return { ...base, content: '**NCCT Career AI** is your career guidance assistant. It uses your NCCT profile to help you:\n\n- Explore career paths that fit your skills and interests\n- See where you stand and spot skill gaps\n- Find courses and build a learning path\n- Learn which skills are in demand\n\n(Mock reply: the real answer will come from the backend.)' };
  }
  if (m.includes('stand')) {
    return {
      ...base,
      content: '**Mock response.** Here is how your profile compares with a sample role:',
      blocks: [
        { type: 'career_recommendation', title: 'Full-Stack Developer', matchPercentage: 72, requiredSkills: ['React', 'JavaScript', 'Node.js', 'SQL'], missingSkills: ['Node.js', 'SQL'] },
        blocks.gap[0],
      ],
    };
  }
  const key = m.includes('course') ? 'course' : m.includes('gap') || m.includes('improve') ? 'gap'
    : m.includes('plan') || m.includes('learn') ? 'plan' : m.includes('job') ? 'job'
    : m.includes('career') || m.includes('path') ? 'career' : null;
  return {
    ...base,
    content: key
      ? '**Mock response.** Here is how structured results will look once the backend is connected:'
      : 'This is a **mock reply**. Try asking about courses, careers, skill gaps, jobs or a learning plan.\n\n- Type /fail to test the error state\n- Type /auth to test an auth failure',
    blocks: key ? blocks[key] : undefined,
  };
}

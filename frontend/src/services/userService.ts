import { chatbotConfig } from '../config/chatbotConfig';
import type { UserProfile } from '../types/user';
import { httpJson } from './http';
import { mockProfile } from './mock/mockData';

/** Map whatever the NCCT API returns into the shape the chatbot needs. Adjust field names here only. */
function normalizeProfile(raw: Partial<UserProfile>): UserProfile {
  return {
    ...raw,
    id: String(raw.id ?? ''),
    name: raw.name ?? '',
    skills: raw.skills ?? [],
    interests: raw.interests ?? [],
    careerInterests: raw.careerInterests ?? [],
  };
}

export const userService = {
  /**
   * INTEGRATION POINT (profile): reads the authenticated user's profile.
   * Alternative: skip this call and pass the user from NCCT's auth context: <ChatbotWidget user={user} />
   */
  async getProfile(): Promise<UserProfile> {
    if (chatbotConfig.transport === 'mock' && !chatbotConfig.profileUrl) return mockProfile;
    const target = chatbotConfig.profileUrl || `${chatbotConfig.apiBaseUrl}${chatbotConfig.endpoints.profile}`;
    return normalizeProfile(await httpJson<Partial<UserProfile>>(target));
  },
};

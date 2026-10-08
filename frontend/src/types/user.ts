/** Authenticated user's profile, as returned by GET /api/user/profile (shape is adjustable in userService.normalizeProfile). */
export interface UserProfile {
  id: string;
  name: string;
  email?: string;
  education?: string;
  branch?: string;
  year?: number;
  skills: string[];
  interests: string[];
  careerInterests: string[];
  experience?: string;
  certifications?: string[];
}

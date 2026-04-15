/**
 * Gamification + profile types — mirror backend Pydantic schemas in
 * backend/app/schemas/gamification.py
 */

export type Tier = 'diamond' | 'platinum' | 'gold' | 'silver' | 'bronze'
export type UnlockState = 'locked' | 'unlocked' | 'mastered'

export interface LeaderboardRowResponse {
  rank: number
  student_id: string
  name: string
  total_score: number
  academic: number
  skill: number
  interview: number
  placement: number
  tier: Tier
  xp_total: number
  current_level: number
  is_current_user: boolean
}

export interface LeaderboardResponse {
  rows: LeaderboardRowResponse[]
  my_row: LeaderboardRowResponse | null
  total_students: number
}

export interface SkillNodeStateResponse {
  name: string
  domain: string
  description: string
  difficulty_tier: number
  mastery: number
  state: UnlockState
}

export interface DomainProgressResponse {
  name: string
  total_skills: number
  mastered_count: number
  unlocked_count: number
  progress_percent: number
  skills: SkillNodeStateResponse[]
}

export interface SkillTreeResponse {
  domains: DomainProgressResponse[]
  mastered_count: number
  total_count: number
  overall_percent: number
}

export interface BadgeResponse {
  id: string
  badge_type: string
  name: string
  description: string | null
  icon: string | null
  earned_at: string
}

export interface PublicProfileResponse {
  user_id: string
  name: string
  role: string
  branch: string | null
  semester: number | null
  cgpa: number | null
  github_url: string | null
  linkedin_url: string | null
  skills: string[]
  target_companies: string[]
  target_role: string | null
  xp_total: number
  current_level: number
  streak_days: number
  campus_iq_score: number
  rank: number | null
  tier: Tier
  academic_pillar: number
  skill_pillar: number
  interview_pillar: number
  placement_pillar: number
  badges: BadgeResponse[]
  member_since: string
}

export interface ProfileUpdateRequest {
  branch?: string | null
  semester?: number | null
  cgpa?: number | null
  github_url?: string | null
  linkedin_url?: string | null
  skills?: string[]
  target_companies?: string[]
  target_role?: string | null
}

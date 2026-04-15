/**
 * Student Dashboard types — mirror backend Pydantic schemas in
 * backend/app/schemas/dashboard.py
 */

import type { Announcement } from './announcement'

export type TaskPriority = 'urgent' | 'high' | 'medium' | 'low'
export type TaskKind = 'quiz' | 'retake' | 'weak_area' | 'daily_login'

export interface XPProgress {
  xp_total: number
  current_level: number
  streak_days: number
  streak_multiplier: number
  xp_into_level: number
  next_level_threshold: number
  xp_to_next_level: number
}

export interface CampusIQScoreBreakdown {
  total: number
  academic: number
  skill: number
  interview: number
  placement: number
  last_calculated_at: string | null
}

export interface DashboardStats {
  quizzes_attempted: number
  quizzes_passed: number
  avg_quiz_score: number | null
  weekly_rank: number | null
}

export interface DashboardTaskItem {
  title: string
  reason: string
  priority: TaskPriority
  score: number
  kind: TaskKind
  action_url: string | null
  quiz_id: string | null
  subject_code: string | null
}

export interface DashboardActivityItem {
  id: string
  event_type: string
  xp_earned: number
  created_at: string
  title: string
}

export interface DashboardResponse {
  student_id: string
  full_name: string
  semester: number | null
  branch: string | null
  xp: XPProgress
  score: CampusIQScoreBreakdown
  stats: DashboardStats
  tasks: DashboardTaskItem[]
  recent_activity: DashboardActivityItem[]
  announcements: Announcement[]
}

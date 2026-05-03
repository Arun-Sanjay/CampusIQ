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

// ── Teacher dashboard ──

import type { DocumentProcessingStatus } from './content'

export interface TeacherStat {
  label: string
  value: string
  trend: number | null
}

export interface RecentUploadRow {
  id: string
  name: string
  subject_code: string | null
  subject_name: string | null
  created_at: string
  status: DocumentProcessingStatus
}

export interface TeacherDashboardResponse {
  teacher_id: string
  full_name: string
  department: string | null
  stats: TeacherStat[]
  recent_uploads: RecentUploadRow[]
  class_average: number | null
  students_total: number
}

// ── Admin dashboard ──

export interface AdminStat {
  label: string
  value: string
  trend: number | null
}

export type AdminUserRole = 'student' | 'teacher' | 'admin'

export interface UserBreakdownRow {
  role: AdminUserRole
  count: number
}

export interface PlatformActivityItem {
  text: string
  created_at: string
}

export interface PlatformHealth {
  api_response_ms: number
  storage_used_gb: number
  storage_quota_gb: number
  uptime_pct: number
}

export interface AdminDashboardResponse {
  stats: AdminStat[]
  user_breakdown: UserBreakdownRow[]
  recent_activity: PlatformActivityItem[]
  platform_health: PlatformHealth
}

// ── Admin user list ──

export interface AdminUserRow {
  id: string
  email: string
  full_name: string
  role: AdminUserRole
  is_active: boolean
  branch: string | null
  semester: number | null
  department: string | null
  last_login: string | null
  created_at: string
}

export interface AdminUserListResponse {
  total: number
  items: AdminUserRow[]
}

// ── Per-student detail ──

export interface StudentQuizScore {
  quiz_id: string
  label: string
  value: number
  completed_at: string
}

export interface StudentDetailResponse {
  student_id: string
  name: string
  branch: string | null
  semester: number | null
  quiz_scores: StudentQuizScore[]
  weak_areas: string[]
  xp_total: number
  streak_days: number
  community_contributions: number
}

/**
 * Announcement + analytics types — mirror backend Pydantic schemas in
 * backend/app/schemas/announcement.py and analytics.py
 */

export type AnnouncementTarget = 'all' | 'subject' | 'college'

export interface Announcement {
  id: string
  author_id: string
  author_name: string | null
  subject_id: string | null
  subject_code: string | null
  subject_name: string | null
  college_id: string | null
  title: string
  body: string
  target: AnnouncementTarget
  created_at: string
}

export interface AnnouncementCreate {
  title: string
  body: string
  target: AnnouncementTarget
  subject_id?: string | null
}

export interface AnnouncementUpdate {
  title?: string
  body?: string
}

// ── Analytics ──

export type Trend = 'up' | 'down' | 'flat'

export interface AnalyticsHeadline {
  class_average: number | null
  completion_rate: number | null
  most_missed_topic: string | null
  active_students: number
}

export interface WeakTopicRow {
  topic: string
  score_percent: number
  attempts: number
  subject_code: string | null
}

export interface ScoreBucket {
  label: string
  range_start: number
  range_end: number
  count: number
}

export interface StudentPerformanceRow {
  student_id: string
  name: string
  quizzes_taken: number
  avg_score: number | null
  last_attempt_at: string | null
  trend: Trend
  weak_area: string | null
}

export interface ClassAnalytics {
  teacher_id: string
  subject_id: string | null
  headline: AnalyticsHeadline
  weak_topics: WeakTopicRow[]
  score_distribution: ScoreBucket[]
  student_performance: StudentPerformanceRow[]
}

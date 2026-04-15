/**
 * Auth types — mirror backend Pydantic schemas in backend/app/schemas/auth.py
 */

export type UserRole = 'student' | 'teacher' | 'admin'

export interface StudentProfile {
  branch: string | null
  semester: number | null
  cgpa: number | null
  github_url: string | null
  linkedin_url: string | null
  skills: string[] | null
  target_companies: string[] | null
  target_role: string | null
  xp_total: number
  current_level: number
  streak_days: number
  last_active_date: string | null
}

export interface TeacherProfile {
  department_name: string | null
  designation: string | null
}

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  college_id: string | null
  last_login: string | null
  created_at: string
  student_profile: StudentProfile | null
  teacher_profile: TeacherProfile | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in_seconds: number
  user: User
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SignupRequest {
  email: string
  password: string
  full_name: string
  role: UserRole
  // Student-specific
  branch?: string
  semester?: number
  cgpa?: number
  // Teacher-specific
  department_name?: string
  designation?: string
  // Invitation code (teacher/admin only)
  invitation_code?: string
}

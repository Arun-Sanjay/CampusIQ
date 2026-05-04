/**
 * Resume Builder types — mirror backend Pydantic schemas in
 * backend/app/schemas/resume.py
 */

export type ResumeTemplate = 'technical' | 'product' | 'research' | 'general'

export interface ResumePersonal {
  name: string
  email: string
  phone: string
  location: string
  linkedin: string
  github: string
  portfolio: string
  photo_url: string
}

export interface ResumeEducation {
  institution: string
  degree: string
  branch: string
  start_year: string
  end_year: string
  cgpa: string
  highlights: string[]
}

export interface ResumeExperience {
  company: string
  role: string
  location: string
  start_date: string
  end_date: string
  bullets: string[]
}

export interface ResumeProject {
  name: string
  description: string
  tech: string[]
  url: string
  highlights: string[]
}

export interface ResumeLanguage {
  name: string
  proficiency: string
}

export interface ResumeContent {
  personal: ResumePersonal
  summary: string
  education: ResumeEducation[]
  experience: ResumeExperience[]
  projects: ResumeProject[]
  skills: string[]
  certifications: string[]
  achievements: string[]
  languages: ResumeLanguage[]
}

export interface ResumeResponse {
  id: string
  student_id: string
  template: ResumeTemplate
  content: ResumeContent
  ats_score: number | null
  last_job_description: string | null
  last_updated: string
  created_at: string
}

export interface ResumeContentUpdate {
  template?: ResumeTemplate
  content: ResumeContent
}

export interface ResumeChatRequest {
  message: string
}

export interface ResumeChatResponse {
  ai_message: string
  content: ResumeContent
  patch_applied: boolean
}

export interface ResumeChatHistoryItem {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ResumeChatHistory {
  messages: ResumeChatHistoryItem[]
}

export interface ATSScoreRequest {
  job_description: string
}

export interface ATSScoreResponse {
  score: number
  matched_keywords: string[]
  missing_keywords: string[]
  suggestions: string[]
}

export interface GitHubImportRequest {
  username: string
  top_n?: number
}

export interface GitHubProjectImport {
  name: string
  description: string
  tech: string[]
  url: string
  stars: number
}

export interface GitHubImportResponse {
  username: string
  imported_count: number
  projects: GitHubProjectImport[]
  content: ResumeContent
}

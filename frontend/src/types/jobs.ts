/**
 * Job Tracker types — mirror backend Pydantic schemas in
 * backend/app/schemas/jobs.py
 */

export type JobType = 'full_time' | 'internship' | 'contract' | 'part_time'
export type JobListingSource = 'admin_added' | 'student_added'
export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'oa_received'
  | 'interview_scheduled'
  | 'offer_received'
  | 'rejected'

export interface JobListingResponse {
  id: string
  title: string
  company_name: string
  description: string | null
  requirements: string | null
  location: string | null
  job_type: JobType
  application_deadline: string | null
  source: JobListingSource
  created_at: string
  fit_score: number | null
}

export interface JobListingCreate {
  title: string
  company_name: string
  description?: string | null
  requirements?: string | null
  location?: string | null
  job_type?: JobType
  application_deadline?: string | null
}

export interface JobApplicationResponse {
  id: string
  student_id: string
  job_listing_id: string
  status: ApplicationStatus
  fit_score: number | null
  notes: string | null
  created_at: string
  updated_at: string
  job: JobListingResponse
}

export interface JobApplicationCreate {
  job_listing_id: string
  status?: ApplicationStatus
  notes?: string | null
}

export interface JobApplicationUpdate {
  status?: ApplicationStatus
  notes?: string | null
}

export interface JobBoardResponse {
  saved: JobApplicationResponse[]
  applied: JobApplicationResponse[]
  oa_received: JobApplicationResponse[]
  interview_scheduled: JobApplicationResponse[]
  offer_received: JobApplicationResponse[]
  rejected: JobApplicationResponse[]
}

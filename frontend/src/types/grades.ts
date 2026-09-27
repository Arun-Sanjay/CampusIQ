// Mirrors backend/app/schemas/grades.py

import type { COAttainmentRow } from './grading'

export interface SubjectGradeRow {
  subject_id: string
  subject_code: string
  subject_name: string
  credits: number
  semester: number | null
  cie_obtained: number | null
  cie_max: number | null
  see_obtained: number | null
  see_max: number | null
  cie_50: number | null
  see_50: number | null
  final_score: number | null
  final_rounded: number | null
  letter_grade: string | null
  grade_point: number | null
  passed: boolean
  gate_failed: string
  is_transitional: boolean
  finalized: boolean
  per_co: COAttainmentRow[]
}

export interface SemesterGrades {
  semester: number
  sgpa: number
  total_credits: number
  subjects: SubjectGradeRow[]
}

export interface TranscriptResponse {
  cgpa: number
  percentage: number
  semesters: SemesterGrades[]
}

export interface ClassGradeRow {
  student_id: string
  student_name: string
  usn: string | null
  cie_obtained: number | null
  cie_max: number | null
  see_obtained: number | null
  final_score: number | null
  letter_grade: string | null
  grade_point: number | null
  passed: boolean
  finalized: boolean
}

export interface ClassGradeOverview {
  subject_id: string
  subject_code: string
  subject_name: string
  students: ClassGradeRow[]
  co_attainment: COAttainmentRow[]
}

/**
 * Enrollment types — mirror backend/app/schemas/enrollment.py
 */

export interface EnrolledStudent {
  student_id: string
  username: string
  full_name: string
  email: string
  branch: string | null
  semester: number | null
  enrolled_at: string
}

export interface SubjectRoster {
  subject_id: string
  subject_code: string
  subject_name: string
  students: EnrolledStudent[]
}

export interface TeacherSubjectCount {
  subject_id: string
  code: string
  name: string
  student_count: number
}

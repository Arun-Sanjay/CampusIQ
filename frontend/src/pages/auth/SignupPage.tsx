import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, Mail, Lock, User as UserIcon, GraduationCap, BookOpen, Shield, AlertCircle, type LucideIcon } from 'lucide-react'
import { Button, Input } from '../../components/ui'
import { clsx } from 'clsx'
import { authApi, ApiError } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import type { SignupRequest, UserRole } from '../../types'

interface RoleOption {
  value: UserRole
  label: string
  icon: LucideIcon
  desc: string
}

const roles: RoleOption[] = [
  { value: 'student', label: 'Student', icon: GraduationCap, desc: 'Access courses, quizzes, and placement prep' },
  { value: 'teacher', label: 'Teacher', icon: BookOpen, desc: 'Upload content, create quizzes, track students' },
  { value: 'admin', label: 'Admin', icon: Shield, desc: 'Manage platform, users, and college data' },
]

const roleToHome: Record<UserRole, string> = {
  student: '/student',
  teacher: '/teacher',
  admin: '/admin',
}

interface FormState {
  name: string
  email: string
  password: string
  role: UserRole | ''
  branch: string
  semester: string
  cgpa: string
  department_name: string
  designation: string
}

export default function SignupPage() {
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const [form, setForm] = useState<FormState>({
    name: '',
    email: '',
    password: '',
    role: '',
    branch: '',
    semester: '',
    cgpa: '',
    department_name: '',
    designation: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)

    if (!form.role) {
      setError('Please select your role')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setLoading(true)
    try {
      const payload: SignupRequest = {
        email: form.email.trim(),
        password: form.password,
        full_name: form.name.trim(),
        role: form.role,
      }
      if (form.role === 'student') {
        if (form.branch) payload.branch = form.branch
        if (form.semester) payload.semester = parseInt(form.semester, 10)
        if (form.cgpa) payload.cgpa = parseFloat(form.cgpa)
      } else if (form.role === 'teacher') {
        if (form.department_name) payload.department_name = form.department_name
        if (form.designation) payload.designation = form.designation
      }

      const response = await authApi.signup(payload)
      setSession({ user: response.user, token: response.access_token })
      navigate(roleToHome[response.user.role], { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        // Pydantic validation errors come as a list; pull out the first message
        let detail: unknown = err.detail
        if (Array.isArray(detail)) {
          detail = detail[0]?.msg || 'Invalid input'
        }
        setError(typeof detail === 'string' ? detail : 'Signup failed')
      } else {
        setError('Could not reach the server. Is the backend running?')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 py-8" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Create your account</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Join CampusIQ today</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Input
            label="FULL NAME"
            icon={UserIcon}
            placeholder="Your full name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            disabled={loading}
            autoComplete="name"
          />
          <Input
            label="EMAIL"
            type="email"
            icon={Mail}
            placeholder="you@college.edu"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
            disabled={loading}
            autoComplete="email"
          />
          <Input
            label="PASSWORD"
            type="password"
            icon={Lock}
            placeholder="Min 8 chars, letters + numbers"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            disabled={loading}
            autoComplete="new-password"
          />

          <div className="space-y-1.5">
            <label className="label">I AM A</label>
            <div className="grid grid-cols-3 gap-2">
              {roles.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setForm({ ...form, role: r.value })}
                  disabled={loading}
                  className={clsx(
                    'flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all duration-200',
                    form.role === r.value
                      ? 'border-primary bg-primary/5 text-[var(--text-primary)]'
                      : 'border-[var(--border-default)] text-[var(--text-tertiary)] hover:border-[var(--border-strong)] hover:text-[var(--text-secondary)]',
                    loading && 'opacity-50 cursor-not-allowed',
                  )}
                >
                  <r.icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{r.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Role-specific fields */}
          {form.role === 'student' && (
            <div className="grid grid-cols-2 gap-2">
              <Input
                label="BRANCH"
                placeholder="CSE"
                value={form.branch}
                onChange={(e) => setForm({ ...form, branch: e.target.value })}
                disabled={loading}
              />
              <Input
                label="SEMESTER"
                type="number"
                min="1"
                max="8"
                placeholder="4"
                value={form.semester}
                onChange={(e) => setForm({ ...form, semester: e.target.value })}
                disabled={loading}
              />
            </div>
          )}
          {form.role === 'teacher' && (
            <>
              <Input
                label="DEPARTMENT"
                placeholder="Computer Science"
                value={form.department_name}
                onChange={(e) => setForm({ ...form, department_name: e.target.value })}
                disabled={loading}
              />
              <Input
                label="DESIGNATION"
                placeholder="Assistant Professor"
                value={form.designation}
                onChange={(e) => setForm({ ...form, designation: e.target.value })}
                disabled={loading}
              />
            </>
          )}

          <Button className="w-full" type="submit" loading={loading} disabled={!form.role}>
            {loading ? 'Creating account…' : 'Create Account'}
          </Button>
        </form>

        <p className="text-sm text-[var(--text-secondary)] text-center mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-[var(--text-primary)] font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}

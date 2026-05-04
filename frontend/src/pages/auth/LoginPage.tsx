import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  ChevronRight,
  GraduationCap,
  Lock,
  Mail,
  Shield,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Button, Input } from '../../components/ui'
import { authApi, ApiError } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import type { UserRole } from '../../types'

interface RoleOption {
  value: UserRole
  label: string
  icon: LucideIcon
  description: string
  accent: string // tailwind classes for the accent ring/icon tint
}

const ROLE_OPTIONS: RoleOption[] = [
  {
    value: 'student',
    label: 'Student',
    icon: GraduationCap,
    description: 'Notes, quizzes, placement prep, gamification.',
    accent: 'text-primary border-primary/30 hover:border-primary',
  },
  {
    value: 'teacher',
    label: 'Teacher',
    icon: BookOpen,
    description: 'Upload content, create quizzes, track classes.',
    accent: 'text-success border-success/30 hover:border-success',
  },
  {
    value: 'admin',
    label: 'Admin',
    icon: Shield,
    description: 'Manage platform, users, and college data.',
    accent: 'text-warning border-warning/30 hover:border-warning',
  },
]

const ROLE_TO_HOME: Record<UserRole, string> = {
  student: '/student',
  teacher: '/teacher',
  admin: '/admin',
}

interface LocationState {
  from?: string
}

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useAuthStore((s) => s.setSession)

  const [pickedRole, setPickedRole] = useState<UserRole | null>(null)
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const stage: 'role' | 'credentials' = pickedRole ? 'credentials' : 'role'

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!pickedRole) return
    setError(null)
    setLoading(true)
    try {
      const response = await authApi.login(form.email.trim(), form.password)
      // Guard the role-gated entry: if the account's actual role doesn't
      // match the portal they picked, surface it instead of silently
      // dumping them somewhere unexpected.
      if (response.user.role !== pickedRole) {
        setError(
          `This account is registered as a ${response.user.role}, not a ${pickedRole}.` +
            ` Go back and pick the ${response.user.role} portal.`,
        )
        setLoading(false)
        return
      }
      setSession({ user: response.user, token: response.access_token })
      const state = location.state as LocationState | null
      const redirectTo =
        state?.from || ROLE_TO_HOME[response.user.role] || '/student'
      navigate(redirectTo, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === 'string' ? err.detail : 'Login failed')
      } else {
        setError('Could not reach the server. Is the backend running?')
      }
    } finally {
      setLoading(false)
    }
  }

  const goBackToRoles = () => {
    setPickedRole(null)
    setError(null)
    setForm({ email: '', password: '' })
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: 'var(--bg-secondary)' }}
    >
      <div className="w-full max-w-2xl">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {stage === 'role' ? 'Welcome to CampusIQ' : 'Welcome back'}
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            {stage === 'role'
              ? 'Choose your portal to continue'
              : `Signing in as ${pickedRole}`}
          </p>
        </div>

        <AnimatePresence mode="wait">
          {stage === 'role' ? (
            <motion.div
              key="role"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="grid grid-cols-1 md:grid-cols-3 gap-4"
            >
              {ROLE_OPTIONS.map((opt) => {
                const Icon = opt.icon
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setPickedRole(opt.value)}
                    className={clsx(
                      'group card p-6 text-left flex flex-col gap-3 border-2 transition-all',
                      'hover:-translate-y-0.5 hover:shadow-lg',
                      opt.accent,
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div
                        className={clsx(
                          'h-11 w-11 rounded-xl flex items-center justify-center',
                          'bg-[var(--bg-tertiary)] group-hover:bg-[var(--bg-elevated)] transition-colors',
                        )}
                      >
                        <Icon className="h-6 w-6" />
                      </div>
                      <ChevronRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                        {opt.label}
                      </h2>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                        {opt.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </motion.div>
          ) : (
            <motion.form
              key="credentials"
              onSubmit={handleSubmit}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="card p-6 space-y-4 mx-auto max-w-sm"
            >
              <button
                type="button"
                onClick={goBackToRoles}
                className="flex items-center gap-1 text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Change portal
              </button>

              {error && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

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
                placeholder="Enter password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
                disabled={loading}
                autoComplete="current-password"
              />
              <Button className="w-full" type="submit" loading={loading}>
                {loading ? 'Signing in…' : `Sign in as ${pickedRole}`}
              </Button>
            </motion.form>
          )}
        </AnimatePresence>

        <p className="text-sm text-[var(--text-secondary)] text-center mt-6">
          Don't have an account?{' '}
          <Link
            to="/signup"
            className="text-[var(--text-primary)] font-medium hover:underline"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}

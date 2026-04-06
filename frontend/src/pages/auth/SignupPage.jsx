import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, Mail, Lock, User, GraduationCap, BookOpen, Shield } from 'lucide-react'
import { Button, Input } from '../../components/ui'
import { clsx } from 'clsx'

const roles = [
  { value: 'student', label: 'Student', icon: GraduationCap, desc: 'Access courses, quizzes, and placement prep' },
  { value: 'teacher', label: 'Teacher', icon: BookOpen, desc: 'Upload content, create quizzes, track students' },
  { value: 'admin', label: 'Admin', icon: Shield, desc: 'Manage platform, users, and college data' },
]

export default function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', role: '' })

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate(form.role === 'teacher' ? '/teacher' : form.role === 'admin' ? '/admin' : '/student')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Create your account</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Join CampusIQ today</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <Input
            label="FULL NAME"
            icon={User}
            placeholder="Your full name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label="EMAIL"
            type="email"
            icon={Mail}
            placeholder="you@college.edu"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Input
            label="PASSWORD"
            type="password"
            icon={Lock}
            placeholder="Create a password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />

          <div className="space-y-1.5">
            <label className="label">I AM A</label>
            <div className="grid grid-cols-3 gap-2">
              {roles.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setForm({ ...form, role: r.value })}
                  className={clsx(
                    'flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all duration-200',
                    form.role === r.value
                      ? 'border-primary bg-primary/5 text-[var(--text-primary)]'
                      : 'border-[var(--border-default)] text-[var(--text-tertiary)] hover:border-[var(--border-strong)] hover:text-[var(--text-secondary)]',
                  )}
                >
                  <r.icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{r.label}</span>
                </button>
              ))}
            </div>
          </div>

          <Button className="w-full" type="submit" disabled={!form.role}>
            Create Account
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

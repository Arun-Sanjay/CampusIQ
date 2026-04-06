import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, Mail, Lock } from 'lucide-react'
import { Button, Input } from '../../components/ui'

export default function LoginPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/student')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Welcome back</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Sign in to CampusIQ</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
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
            placeholder="Enter password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <Button className="w-full" type="submit">Sign In</Button>
        </form>

        <p className="text-sm text-[var(--text-secondary)] text-center mt-4">
          Don't have an account?{' '}
          <Link to="/signup" className="text-[var(--text-primary)] font-medium hover:underline">Sign up</Link>
        </p>
      </div>
    </div>
  )
}

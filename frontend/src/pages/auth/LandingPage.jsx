import { Link } from 'react-router-dom'
import { Zap, BookOpen, Target, Shield, ArrowRight } from 'lucide-react'
import Button from '../../components/ui/Button'

const features = [
  { icon: BookOpen, title: 'AI Note Assistant', desc: 'Ask questions, get answers from your actual course notes with RAG-powered AI' },
  { icon: Target, title: 'Smart Placement Prep', desc: 'Resume builder, mock interviews, skill gap analysis — all AI-powered' },
  { icon: Shield, title: 'CampusIQ Score', desc: 'One score that tracks your academic and placement readiness across 4 pillars' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-[var(--border-default)]">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-[var(--text-primary)] font-bold text-lg">CampusIQ</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors px-3 py-1.5">
            Log In
          </Link>
          <Link to="/signup">
            <Button size="sm">Get Started</Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="flex flex-col items-center justify-center text-center px-4 pt-24 pb-20">
        <div className="h-16 w-16 rounded-2xl bg-[var(--bg-tertiary)] border border-[var(--border-default)] flex items-center justify-center mb-8">
          <Zap className="h-8 w-8 text-[var(--text-primary)]" />
        </div>
        <h1 className="text-5xl md:text-6xl font-bold text-[var(--text-primary)] max-w-3xl leading-tight">
          Most platforms ask what you want to{' '}
          <span className="text-[var(--text-tertiary)]">learn.</span>
          <br />
          We ask who you want to{' '}
          <span className="text-[var(--text-primary)] underline decoration-2 underline-offset-4">become.</span>
        </h1>
        <p className="mt-6 text-[var(--text-secondary)] text-lg max-w-xl leading-relaxed">
          CampusIQ is the AI companion that guides engineering students from their first day of college to their first day of work.
        </p>
        <div className="mt-8 flex items-center gap-3">
          <Link to="/signup">
            <Button size="lg" iconRight={ArrowRight}>Start Free</Button>
          </Link>
          <Link to="/login">
            <Button variant="secondary" size="lg">Log In</Button>
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto px-4 pb-24">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] text-center mb-12">
          Everything you need. One platform.
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="card p-6">
              <f.icon className="h-8 w-8 text-[var(--text-primary)] mb-4" />
              <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">{f.title}</h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

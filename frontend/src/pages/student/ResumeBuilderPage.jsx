import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Send,
  Download,
  BarChart3,
  Code,
  Mail,
  Phone,
  MapPin,
  Bot,
  User,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const templates = ['Technical', 'Product', 'Research', 'General']

const initialMessages = [
  { role: 'ai', text: "Let's build your resume! What's your full name and email?" },
  { role: 'user', text: 'Arun Sanjay, arun@rvce.edu.in' },
  { role: 'ai', text: 'Great! Tell me about your education \u2014 college, branch, semester, CGPA' },
  { role: 'user', text: 'RVCE, B.Tech CS, 4th semester, 8.5 CGPA' },
  { role: 'ai', text: 'Now tell me about any projects you\'ve worked on' },
]

const resumeData = {
  name: 'Arun Sanjay',
  email: 'arun@rvce.edu.in',
  phone: '+91 98765 43210',
  location: 'Bangalore, India',
  education: {
    college: 'RV College of Engineering',
    degree: 'B.Tech Computer Science',
    semester: '4th Semester',
    cgpa: '8.5 / 10',
  },
  projects: [
    {
      name: 'CampusIQ Platform',
      description: 'AI-powered campus placement preparation system with mock interviews, skill gap analysis, and resume building.',
      tech: ['React', 'Node.js', 'PostgreSQL'],
    },
    {
      name: 'Smart Attendance System',
      description: 'Face-recognition based attendance tracker using OpenCV and deep learning, deployed on Raspberry Pi.',
      tech: ['Python', 'OpenCV', 'TensorFlow'],
    },
  ],
  skills: ['Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'Git', 'Data Structures', 'Machine Learning'],
}

export default function ResumeBuilderPage() {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [activeTemplate, setActiveTemplate] = useState('Technical')

  const handleSend = () => {
    if (!input.trim()) return
    setMessages(prev => [...prev, { role: 'user', text: input }])
    setInput('')
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        { role: 'ai', text: 'Thanks! I\'ve updated your resume preview. Would you like to add any certifications or extracurricular activities?' },
      ])
    }, 600)
  }

  return (
    <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
      {/* Top bar: Template tabs + ATS Score */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div className="flex gap-2">
          {templates.map(t => (
            <Button
              key={t}
              variant={activeTemplate === t ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setActiveTemplate(t)}
            >
              {t}
            </Button>
          ))}
        </div>
        <Badge variant="success" size="lg">ATS Score: 72/100</Badge>
      </motion.div>

      {/* Split layout */}
      <motion.div variants={fadeUp} className="flex gap-4" style={{ height: 'calc(100vh - 14rem)' }}>
        {/* Left: Chat */}
        <div className="w-1/2 flex flex-col card">
          <div className="p-3 border-b border-[var(--border-default)]">
            <CardLabel>AI Resume Builder</CardLabel>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={clsx('flex gap-2', msg.role === 'user' && 'justify-end')}>
                {msg.role === 'ai' && (
                  <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}
                <div
                  className={clsx(
                    'max-w-[80%] rounded-lg px-3 py-2 text-sm',
                    msg.role === 'ai'
                      ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                      : 'bg-primary text-primary-foreground',
                  )}
                >
                  {msg.text}
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center shrink-0">
                    <User className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-[var(--border-default)] flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Tell me about your experience..."
              className="input-base flex-1"
            />
            <Button size="sm" icon={Send} onClick={handleSend}>Send</Button>
          </div>
        </div>

        {/* Right: Resume Preview */}
        <div className="w-1/2 overflow-y-auto">
          <Card className="h-full">
            <div className="border-b border-[var(--border-default)] pb-4 mb-4">
              <h2 className="text-xl font-bold text-[var(--text-primary)]">{resumeData.name}</h2>
              <div className="flex flex-wrap gap-3 mt-2 text-xs text-[var(--text-secondary)]">
                <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{resumeData.email}</span>
                <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{resumeData.phone}</span>
                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{resumeData.location}</span>
              </div>
            </div>

            <div className="space-y-4">
              {/* Education */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider mb-2">Education</h3>
                <div className="text-sm text-[var(--text-secondary)]">
                  <p className="font-medium text-[var(--text-primary)]">{resumeData.education.college}</p>
                  <p>{resumeData.education.degree} &middot; {resumeData.education.semester}</p>
                  <p>CGPA: {resumeData.education.cgpa}</p>
                </div>
              </div>

              {/* Projects */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider mb-2">Projects</h3>
                <div className="space-y-3">
                  {resumeData.projects.map((p, i) => (
                    <div key={i}>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{p.name}</p>
                      <p className="text-xs text-[var(--text-secondary)] mt-0.5">{p.description}</p>
                      <div className="flex gap-1.5 mt-1.5">
                        {p.tech.map(t => (
                          <Badge key={t} size="sm">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Skills */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider mb-2">Skills</h3>
                <div className="flex flex-wrap gap-1.5">
                  {resumeData.skills.map(s => (
                    <Badge key={s} variant="primary" size="sm">{s}</Badge>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </motion.div>

      {/* Bottom bar */}
      <motion.div variants={fadeUp} className="flex gap-3">
        <Button icon={Download}>Download PDF</Button>
        <Button variant="secondary" icon={BarChart3}>ATS Score</Button>
        <Button variant="secondary" icon={Code}>Import from GitHub</Button>
      </motion.div>
    </motion.div>
  )
}

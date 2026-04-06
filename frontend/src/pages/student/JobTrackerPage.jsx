import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Plus,
  Search,
  MapPin,
  Calendar,
  Briefcase,
} from 'lucide-react'
import Card, { CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Input from '../../components/ui/Input'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const columns = [
  {
    title: 'Saved',
    jobs: [
      {
        company: 'Google',
        role: 'SWE Intern',
        fit: 92,
        location: 'Bangalore',
        deadline: 'Apr 20',
        type: 'Internship',
      },
      {
        company: 'Flipkart',
        role: 'Backend Engineer',
        fit: 78,
        location: 'Bangalore',
        deadline: 'Apr 25',
        type: 'Full-time',
      },
    ],
  },
  {
    title: 'Applied',
    jobs: [
      {
        company: 'Amazon',
        role: 'SDE-1',
        fit: 85,
        location: 'Hyderabad',
        deadline: 'Apr 15',
        type: 'Full-time',
      },
      {
        company: 'Microsoft',
        role: 'SWE Intern',
        fit: 88,
        location: 'Noida',
        deadline: 'Apr 18',
        type: 'Internship',
      },
      {
        company: 'Razorpay',
        role: 'Full Stack Dev',
        fit: 71,
        location: 'Bangalore',
        deadline: 'Apr 22',
        type: 'Full-time',
      },
    ],
  },
  {
    title: 'OA Received',
    jobs: [
      {
        company: 'TCS',
        role: 'Systems Engineer',
        fit: 65,
        location: 'Chennai',
        deadline: 'Apr 12',
        type: 'Full-time',
      },
    ],
  },
  {
    title: 'Interview',
    jobs: [
      {
        company: 'Infosys',
        role: 'Power Programmer',
        fit: 74,
        location: 'Mysore',
        deadline: 'Apr 10',
        type: 'Full-time',
      },
      {
        company: 'Atlassian',
        role: 'SWE Intern',
        fit: 90,
        location: 'Bangalore',
        deadline: 'Apr 14',
        type: 'Internship',
      },
    ],
  },
  {
    title: 'Offer / Rejected',
    jobs: [
      {
        company: 'Zoho',
        role: 'Member Technical',
        fit: 68,
        location: 'Chennai',
        deadline: 'Offered',
        type: 'Full-time',
        status: 'offer',
      },
      {
        company: 'Wipro',
        role: 'Project Engineer',
        fit: 52,
        location: 'Pune',
        deadline: 'Rejected',
        type: 'Full-time',
        status: 'rejected',
      },
    ],
  },
]

function getFitVariant(fit) {
  if (fit >= 85) return 'success'
  if (fit >= 70) return 'warning'
  return 'default'
}

export default function JobTrackerPage() {
  const [search, setSearch] = useState('')

  return (
    <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
      {/* Top bar */}
      <motion.div variants={fadeUp} className="flex items-center gap-3">
        <Button icon={Plus}>Add Listing</Button>
        <div className="w-72">
          <Input
            icon={Search}
            placeholder="Search jobs..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </motion.div>

      {/* Kanban board */}
      <motion.div variants={fadeUp} className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: 'calc(100vh - 14rem)' }}>
        {columns.map(col => (
          <div key={col.title} className="w-64 shrink-0 flex flex-col">
            {/* Column header */}
            <div className="flex items-center gap-2 mb-3">
              <CardLabel>{col.title}</CardLabel>
              <Badge size="sm">{col.jobs.length}</Badge>
            </div>

            {/* Job cards */}
            <div className="space-y-3 flex-1">
              {col.jobs.map((job, i) => (
                <Card key={i} hover className="cursor-pointer">
                  <div className="flex items-start justify-between mb-1.5">
                    <p className="font-semibold text-sm text-[var(--text-primary)]">{job.company}</p>
                    {job.status === 'offer' && <Badge variant="success" size="sm">Offer</Badge>}
                    {job.status === 'rejected' && <Badge variant="danger" size="sm">Rejected</Badge>}
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mb-2">{job.role}</p>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={getFitVariant(job.fit)} size="sm">{job.fit}% match</Badge>
                    <Badge size="sm">{job.type}</Badge>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[var(--text-tertiary)]">
                    <span className="flex items-center gap-0.5">
                      <MapPin className="h-3 w-3" />{job.location}
                    </span>
                    <span className="flex items-center gap-0.5">
                      <Calendar className="h-3 w-3" />{job.deadline}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </motion.div>
    </motion.div>
  )
}

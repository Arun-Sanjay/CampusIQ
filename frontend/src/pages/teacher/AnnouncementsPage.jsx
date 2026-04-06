import { motion } from 'framer-motion'
import { Megaphone, Edit, Trash2 } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import TextArea from '../../components/ui/TextArea'
import Select from '../../components/ui/Select'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const targetOptions = [
  { value: 'all', label: 'All Students' },
  { value: 'daa', label: 'DAA' },
  { value: 'cn', label: 'CN' },
  { value: 'dms', label: 'DMS' },
  { value: 'os', label: 'OS' },
]

const announcements = [
  {
    id: 1,
    title: 'DAA Assignment 3 Deadline Extended',
    body: 'The deadline for Assignment 3 on Graph Algorithms has been extended to April 12. Please submit before midnight.',
    target: 'DAA',
    date: 'Apr 3, 2026',
  },
  {
    id: 2,
    title: 'CN Lab Cancelled Tomorrow',
    body: 'Due to the department meeting, the CN lab session for Section B is cancelled. Will be rescheduled to next week.',
    target: 'CN',
    date: 'Apr 2, 2026',
  },
  {
    id: 3,
    title: 'Mid-Semester Exam Schedule Released',
    body: 'Check the exam portal for your personalized mid-semester timetable. Report discrepancies to the academic office immediately.',
    target: 'All Students',
    date: 'Mar 30, 2026',
  },
  {
    id: 4,
    title: 'Guest Lecture: Introduction to Quantum Computing',
    body: 'Dr. Ramanujan from IISc will deliver a guest lecture on quantum computing fundamentals this Friday at 3 PM in Seminar Hall.',
    target: 'All Students',
    date: 'Mar 28, 2026',
  },
]

export default function AnnouncementsPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Announcements</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Post updates and notices for your students</p>
        </div>
      </motion.div>

      {/* New Announcement */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Megaphone className="h-4 w-4 text-[var(--text-secondary)]" />
              <CardTitle>New Announcement</CardTitle>
            </div>
          </CardHeader>
          <div className="space-y-4">
            <Input label="Title" placeholder="Enter announcement title..." />
            <TextArea label="Body" placeholder="Write your announcement here..." rows={4} />
            <div className="flex items-end gap-4">
              <div className="w-48">
                <Select label="Target" options={targetOptions} />
              </div>
              <Button icon={Megaphone}>Post Announcement</Button>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Divider */}
      <div className="border-t border-[var(--border-default)]" />

      {/* Posted Announcements */}
      <motion.div variants={fadeUp}>
        <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-3 uppercase tracking-wider">Posted Announcements</h2>
      </motion.div>

      {announcements.map((ann, i) => (
        <motion.div
          key={ann.id}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <Card>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-[var(--text-primary)]">{ann.title}</h3>
                  <Badge variant="default" size="sm">{ann.target}</Badge>
                </div>
                <p className="text-sm text-[var(--text-secondary)] line-clamp-2">{ann.body}</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-2">{ann.date}</p>
              </div>
              <div className="flex gap-1 shrink-0">
                <Button variant="ghost" size="sm" icon={Edit} />
                <Button variant="ghost" size="sm" icon={Trash2} />
              </div>
            </div>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  )
}

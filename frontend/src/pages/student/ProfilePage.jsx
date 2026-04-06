import { motion } from 'framer-motion'
import {
  Share2, Download, Award, MessageCircle, Flame, Swords,
  Edit, Brain, ClipboardCheck, Link,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import Button from '../../components/ui/Button'
import ProgressBar from '../../components/ui/ProgressBar'
import StatCard from '../../components/dashboard/StatCard'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const pillars = [
  { label: 'Academic', value: 72, color: 'primary' },
  { label: 'Skills', value: 58, color: 'purple' },
  { label: 'Interview', value: 65, color: 'warning' },
  { label: 'Placement', value: 73, color: 'success' },
]

const skills = [
  'Python', 'JavaScript', 'SQL', 'React', 'Git',
  'Data Structures', 'Machine Learning', 'REST APIs', 'Docker', 'PostgreSQL',
]

const badges = [
  { name: 'Quiz Streak x7', icon: Flame, date: 'Mar 28, 2026' },
  { name: 'First Mock Interview', icon: MessageCircle, date: 'Mar 15, 2026' },
  { name: 'Community Helper', icon: Award, date: 'Mar 10, 2026' },
  { name: 'Boss Battle Survivor', icon: Swords, date: 'Feb 20, 2026' },
]

export default function ProfilePage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Profile Header */}
      <motion.div variants={fadeUp}>
        <Card>
          <div className="flex items-center gap-5">
            <Avatar name="Arun Sanjay" size="xl" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-bold text-[var(--text-primary)]">Arun Sanjay</h1>
                <Badge variant="gold" size="sm">Gold</Badge>
              </div>
              <p className="text-sm text-[var(--text-secondary)] mt-1">RVCE · B.Tech CS · Sem 4</p>
            </div>
            <Button variant="secondary" icon={Edit} size="sm">Edit Profile</Button>
          </div>
        </Card>
      </motion.div>

      {/* CampusIQ Score */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>CampusIQ Score</CardTitle>
          </CardHeader>
          <div className="flex items-center gap-6">
            <div className="text-center shrink-0">
              <span className="text-4xl font-bold text-[var(--text-primary)]">67</span>
              <span className="text-lg text-[var(--text-tertiary)]"> / 100</span>
            </div>
            <div className="flex-1 space-y-3">
              {pillars.map((p) => (
                <ProgressBar
                  key={p.label}
                  label={p.label}
                  value={p.value}
                  showValue
                  color={p.color}
                  size="sm"
                />
              ))}
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Skills */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Skills</CardTitle>
          </CardHeader>
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <Badge key={skill} variant="primary" size="lg">{skill}</Badge>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Badges */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Earned Badges</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-4 gap-3">
            {badges.map((badge) => {
              const IconComp = badge.icon
              return (
                <div
                  key={badge.name}
                  className="flex flex-col items-center text-center p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-default)]"
                >
                  <div className="h-10 w-10 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center mb-2">
                    <IconComp className="h-5 w-5 text-[var(--text-secondary)]" />
                  </div>
                  <span className="text-xs font-semibold text-[var(--text-primary)]">{badge.name}</span>
                  <span className="text-[10px] text-[var(--text-tertiary)] mt-0.5">{badge.date}</span>
                </div>
              )
            })}
          </div>
        </Card>
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
        <StatCard label="QUIZZES" value="24" icon={ClipboardCheck} />
        <StatCard label="INTERVIEWS" value="8" icon={MessageCircle} />
        <StatCard label="COMMUNITY ANSWERS" value="15" icon={Award} />
        <StatCard label="BEST STREAK" value="12 days" icon={Flame} />
      </motion.div>

      {/* Actions */}
      <motion.div variants={fadeUp}>
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs text-[var(--text-tertiary)]">
              <Link className="h-3 w-3" />
              <span>campusiq.app/profile/arun-sanjay</span>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" icon={Share2}>Share Profile</Button>
              <Button icon={Download}>Download Resume</Button>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}

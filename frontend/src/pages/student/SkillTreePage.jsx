import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Globe, Brain, Code2, Layers, Briefcase, Cpu,
  Lock, Zap, Target, Flame,
} from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import ProgressBar from '../../components/ui/ProgressBar'
import StatCard from '../../components/dashboard/StatCard'

const stagger = {
  animate: { transition: { staggerChildren: 0.07 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const domains = [
  {
    name: 'Web Development',
    icon: Globe,
    level: 3,
    maxLevel: 5,
    color: 'primary',
    skills: [
      { name: 'HTML/CSS', unlocked: true },
      { name: 'JavaScript', unlocked: true },
      { name: 'React', unlocked: true, current: true },
      { name: 'Node.js', unlocked: false },
      { name: 'REST APIs', unlocked: true },
    ],
  },
  {
    name: 'Machine Learning',
    icon: Brain,
    level: 2,
    maxLevel: 5,
    color: 'purple',
    skills: [
      { name: 'Linear Algebra', unlocked: true },
      { name: 'Regression', unlocked: true },
      { name: 'Neural Nets', unlocked: false },
      { name: 'NLP', unlocked: false },
      { name: 'CNNs', unlocked: false },
    ],
  },
  {
    name: 'DSA',
    icon: Code2,
    level: 4,
    maxLevel: 5,
    color: 'success',
    skills: [
      { name: 'Arrays', unlocked: true },
      { name: 'Trees', unlocked: true },
      { name: 'Graphs', unlocked: true },
      { name: 'DP', unlocked: true, current: true },
      { name: 'Greedy', unlocked: false },
    ],
  },
  {
    name: 'System Design',
    icon: Layers,
    level: 1,
    maxLevel: 5,
    color: 'warning',
    skills: [
      { name: 'Load Balancing', unlocked: true },
      { name: 'Caching', unlocked: false },
      { name: 'DB Sharding', unlocked: false },
      { name: 'Microservices', unlocked: false },
    ],
  },
  {
    name: 'Product Management',
    icon: Briefcase,
    level: 2,
    maxLevel: 5,
    color: 'info',
    skills: [
      { name: 'User Research', unlocked: true },
      { name: 'Wireframing', unlocked: true },
      { name: 'PRDs', unlocked: true, current: true },
      { name: 'Metrics', unlocked: false },
      { name: 'Go-to-Market', unlocked: false },
    ],
  },
  {
    name: 'Core CS',
    icon: Cpu,
    level: 3,
    maxLevel: 5,
    color: 'danger',
    skills: [
      { name: 'OS Basics', unlocked: true },
      { name: 'Networking', unlocked: true },
      { name: 'DBMS', unlocked: true },
      { name: 'Compilers', unlocked: false },
      { name: 'TOC', unlocked: false },
    ],
  },
]

export default function SkillTreePage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Skill Tree</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Track your progression across domains</p>
        </div>
      </motion.div>

      {/* Top Stats */}
      <motion.div variants={fadeUp} className="grid grid-cols-3 gap-4">
        <StatCard label="TOTAL XP" value="3,450" icon={Zap} trend={8} />
        <StatCard label="SKILLS UNLOCKED" value="28 / 65" icon={Target} />
        <StatCard label="CURRENT STREAK" value="5 days" icon={Flame} trend={2} />
      </motion.div>

      {/* Overall Progress */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Overall Progress</CardTitle>
          </CardHeader>
          <ProgressBar value={43} max={100} showValue label="43% Complete" size="lg" color="primary" />
        </Card>
      </motion.div>

      {/* Domain Grid */}
      <motion.div variants={fadeUp} className="grid grid-cols-2 gap-4">
        {domains.map((domain, i) => {
          const IconComp = domain.icon
          return (
            <motion.div
              key={domain.name}
              initial={{ opacity: 0, y: 20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.15 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <IconComp className="h-4 w-4 text-[var(--text-secondary)]" />
                    <CardTitle>{domain.name}</CardTitle>
                  </div>
                </CardHeader>
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-[var(--text-tertiary)]">
                      Level {domain.level} / {domain.maxLevel}
                    </span>
                  </div>
                  <ProgressBar
                    value={domain.level}
                    max={domain.maxLevel}
                    size="sm"
                    color={domain.color}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {domain.skills.map((skill) => (
                    <span
                      key={skill.name}
                      className={clsx(
                        'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
                        skill.current
                          ? 'border-2 border-[var(--border-strong)] text-[var(--text-primary)] bg-[var(--bg-tertiary)]'
                          : skill.unlocked
                            ? 'border border-[var(--border-default)] text-[var(--text-secondary)] bg-[var(--bg-secondary)]'
                            : 'border border-dashed border-[var(--border-default)] text-[var(--text-tertiary)]'
                      )}
                    >
                      {!skill.unlocked && <Lock className="h-3 w-3" />}
                      {skill.name}
                    </span>
                  ))}
                </div>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>
    </motion.div>
  )
}

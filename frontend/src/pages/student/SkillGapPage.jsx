import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Target, Clock, TrendingUp, Minus, Plus, Zap } from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'
import Select from '../../components/ui/Select'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const companyOptions = [
  { value: 'google', label: 'Google' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'tcs', label: 'TCS' },
  { value: 'infosys', label: 'Infosys' },
  { value: 'startup', label: 'Startup' },
]

const roleOptions = [
  { value: 'swe', label: 'Software Engineer' },
  { value: 'ds', label: 'Data Scientist' },
  { value: 'pm', label: 'Product Manager' },
]

const currentSkills = [
  { name: 'Python', hours: '0h' },
  { name: 'SQL', hours: '0h' },
  { name: 'Git', hours: '0h' },
  { name: 'HTML/CSS', hours: '0h' },
]

const missingSkills = [
  { name: 'System Design', hours: '8h' },
  { name: 'DSA Advanced', hours: '12h' },
  { name: 'React', hours: '6h' },
  { name: 'Cloud (AWS)', hours: '10h' },
]

const pathSkills = [
  { name: 'DSA Basics', hours: '4h' },
  { name: 'DSA Intermediate', hours: '6h' },
  { name: 'DSA Advanced', hours: '12h' },
]

const knapsackResults = [
  { topic: 'DSA Advanced', timeCost: '4h', improvement: '+12%', included: true },
  { topic: 'System Design Basics', timeCost: '3h', improvement: '+8%', included: true },
  { topic: 'React Fundamentals', timeCost: '2h', improvement: '+5%', included: true },
  { topic: 'Cloud Concepts', timeCost: '2h', improvement: '+4%', included: true },
  { topic: 'Machine Learning', timeCost: '5h', improvement: '+6%', included: false },
  { topic: 'Kubernetes', timeCost: '4h', improvement: '+3%', included: false },
]

export default function SkillGapPage() {
  const [company, setCompany] = useState('google')
  const [role, setRole] = useState('swe')
  const [hours, setHours] = useState(15)

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Top filters */}
      <motion.div variants={fadeUp} className="flex gap-4">
        <div className="w-64">
          <Select
            label="Target Company"
            options={companyOptions}
            value={company}
            onChange={e => setCompany(e.target.value)}
          />
        </div>
        <div className="w-64">
          <Select
            label="Target Role"
            options={roleOptions}
            value={role}
            onChange={e => setRole(e.target.value)}
          />
        </div>
      </motion.div>

      {/* Gap Score */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Gap Score</CardTitle>
          </CardHeader>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <span className="stat-value text-4xl">34%</span>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">Skills gap remaining</p>
            </div>
            <div className="flex-1">
              <ProgressBar value={66} label="Readiness" showValue color="success" size="lg" />
              <p className="text-xs text-[var(--text-secondary)] mt-2">You are 66% ready for Google SWE</p>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Skill Graph */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Skill Map</CardTitle>
            <div className="flex gap-3">
              <span className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                <span className="w-3 h-3 rounded border-2 border-success bg-success/10" /> Current
              </span>
              <span className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                <span className="w-3 h-3 rounded border-2 border-danger border-dashed" /> Missing
              </span>
              <span className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                <span className="w-3 h-3 rounded border-2 border-primary bg-primary/10" /> Path
              </span>
            </div>
          </CardHeader>
          <div className="grid grid-cols-4 gap-4">
            {currentSkills.map(skill => (
              <div
                key={skill.name}
                className="rounded-lg border-2 border-success bg-success/5 p-3 text-center"
              >
                <p className="text-sm font-medium text-[var(--text-primary)]">{skill.name}</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-1">{skill.hours}</p>
              </div>
            ))}
            {pathSkills.map((skill, i) => (
              <div key={skill.name} className="relative">
                <div className="rounded-lg border-2 border-primary bg-primary/5 p-3 text-center">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{skill.name}</p>
                  <p className="text-xs text-[var(--text-tertiary)] mt-1">{skill.hours}</p>
                </div>
                {i < pathSkills.length - 1 && (
                  <div className="absolute top-1/2 -right-4 w-4 h-0.5 bg-primary" />
                )}
              </div>
            ))}
            <div />
            {missingSkills.map(skill => (
              <div
                key={skill.name}
                className="rounded-lg border-2 border-dashed border-danger bg-danger/5 p-3 text-center"
              >
                <p className="text-sm font-medium text-[var(--text-primary)]">{skill.name}</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-1">{skill.hours}</p>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Time Budget */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Time Budget</CardTitle>
          </CardHeader>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[var(--text-secondary)]">Available hours per week:</span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                icon={Minus}
                onClick={() => setHours(h => Math.max(1, h - 1))}
              />
              <span className="stat-value text-2xl w-16 text-center">{hours}</span>
              <Button
                variant="secondary"
                size="sm"
                icon={Plus}
                onClick={() => setHours(h => h + 1)}
              />
            </div>
            <span className="text-sm text-[var(--text-tertiary)]">hours</span>
          </div>
        </Card>
      </motion.div>

      {/* Knapsack Results */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Optimized Study Plan (Knapsack)</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left py-2 text-[var(--text-tertiary)] font-medium">Topic</th>
                  <th className="text-left py-2 text-[var(--text-tertiary)] font-medium">Time Cost</th>
                  <th className="text-left py-2 text-[var(--text-tertiary)] font-medium">Predicted Improvement</th>
                  <th className="text-left py-2 text-[var(--text-tertiary)] font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {knapsackResults.map((row, i) => (
                  <tr key={i} className="border-b border-[var(--border-default)] last:border-0">
                    <td className="py-2.5 text-[var(--text-primary)] font-medium">{row.topic}</td>
                    <td className="py-2.5 text-[var(--text-secondary)]">{row.timeCost}</td>
                    <td className="py-2.5 text-success font-medium">{row.improvement}</td>
                    <td className="py-2.5">
                      <Badge variant={row.included ? 'success' : 'default'}>
                        {row.included ? 'INCLUDED' : 'EXCLUDED'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--border-default)]">
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Total: <span className="text-success">+29% improvement</span> in <span className="text-[var(--text-secondary)]">11 hours</span>
            </p>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}

import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Filter, Download, Users } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Select from '../../components/ui/Select'
import StatCard from '../../components/dashboard/StatCard'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const skillOptions = [
  { value: 'python', label: 'Python' },
  { value: 'sql', label: 'SQL' },
  { value: 'java', label: 'Java' },
  { value: 'react', label: 'React' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'git', label: 'Git' },
  { value: 'docker', label: 'Docker' },
  { value: 'ml', label: 'Machine Learning' },
]

const operators = ['AND', 'OR', 'NOT']

export default function SkillAnalyticsPage() {
  const [op1, setOp1] = useState('AND')
  const [op2, setOp2] = useState('NOT')

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Skill Analytics</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Filter students by skill combinations using inclusion-exclusion analysis</p>
        </div>
      </motion.div>

      {/* Filter Builder */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-[var(--text-secondary)]" />
              <CardTitle>Filter Builder</CardTitle>
            </div>
          </CardHeader>
          <div className="flex items-end gap-3 flex-wrap">
            <div className="w-40">
              <Select label="Skill 1" options={skillOptions} placeholder="Select skill" />
            </div>

            <div className="flex gap-1 pb-0.5">
              {operators.map((o) => (
                <button
                  key={`op1-${o}`}
                  onClick={() => setOp1(o)}
                  className={clsx(
                    'px-3 py-2 text-xs font-semibold rounded-md border transition-all',
                    op1 === o
                      ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-strong)]'
                      : 'text-[var(--text-tertiary)] border-[var(--border-default)] hover:text-[var(--text-secondary)]'
                  )}
                >
                  {o}
                </button>
              ))}
            </div>

            <div className="w-40">
              <Select label="Skill 2" options={skillOptions} placeholder="Select skill" />
            </div>

            <div className="flex gap-1 pb-0.5">
              {operators.map((o) => (
                <button
                  key={`op2-${o}`}
                  onClick={() => setOp2(o)}
                  className={clsx(
                    'px-3 py-2 text-xs font-semibold rounded-md border transition-all',
                    op2 === o
                      ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-strong)]'
                      : 'text-[var(--text-tertiary)] border-[var(--border-default)] hover:text-[var(--text-secondary)]'
                  )}
                >
                  {o}
                </button>
              ))}
            </div>

            <div className="w-40">
              <Select label="Skill 3" options={skillOptions} placeholder="Select skill" />
            </div>

            <Button icon={Filter}>Apply Filter</Button>
          </div>

          <div className="mt-3 text-sm text-[var(--text-secondary)]">
            Current filter: <span className="font-semibold text-[var(--text-primary)]">Python {op1} SQL {op2} Java</span>
          </div>
        </Card>
      </motion.div>

      {/* Results */}
      <motion.div variants={fadeUp}>
        <StatCard label="MATCHING STUDENTS" value="42 / 156" icon={Users} />
      </motion.div>

      {/* Venn Diagram */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Skill Overlap Visualization</CardTitle>
          </CardHeader>
          <div className="relative mx-auto" style={{ width: 400, height: 320 }}>
            {/* Circle 1 — Python */}
            <div
              className="absolute rounded-full border-2 border-primary/60 flex items-center justify-center"
              style={{
                width: 200,
                height: 200,
                left: 40,
                top: 30,
                backgroundColor: 'rgba(var(--color-primary-rgb, 99, 102, 241), 0.08)',
              }}
            >
              <span className="text-sm font-semibold text-[var(--text-primary)] -translate-x-6 -translate-y-4">
                Python (89)
              </span>
            </div>

            {/* Circle 2 — SQL */}
            <div
              className="absolute rounded-full border-2 border-success/60 flex items-center justify-center"
              style={{
                width: 200,
                height: 200,
                left: 160,
                top: 30,
                backgroundColor: 'rgba(34, 197, 94, 0.08)',
              }}
            >
              <span className="text-sm font-semibold text-[var(--text-primary)] translate-x-6 -translate-y-4">
                SQL (72)
              </span>
            </div>

            {/* Circle 3 — Java */}
            <div
              className="absolute rounded-full border-2 border-warning/60 flex items-center justify-center"
              style={{
                width: 200,
                height: 200,
                left: 100,
                top: 100,
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
              }}
            >
              <span className="text-sm font-semibold text-[var(--text-primary)] translate-y-8">
                Java (54)
              </span>
            </div>

            {/* Center overlap */}
            <div
              className="absolute flex items-center justify-center"
              style={{ left: 155, top: 105, width: 90, height: 50 }}
            >
              <span className="text-xs font-bold text-[var(--text-primary)] bg-[var(--bg-elevated)] px-2 py-1 rounded-md border border-[var(--border-default)]">
                All 3: 28
              </span>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Export */}
      <motion.div variants={fadeUp} className="flex justify-end">
        <Button variant="secondary" icon={Download}>Export Filtered List</Button>
      </motion.div>
    </motion.div>
  )
}

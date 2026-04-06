import { motion } from 'framer-motion'
import { ShieldAlert, Eye, Info, FileText } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
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

const quizOptions = [
  { value: 'daa3', label: 'DAA Quiz 3 — Graph Algorithms' },
  { value: 'cn4', label: 'CN Quiz 4 — Transport Layer' },
  { value: 'os2', label: 'OS Quiz 2 — Process Scheduling' },
  { value: 'dms1', label: 'DMS Quiz 1 — Set Theory' },
]

const flaggedPairs = [
  {
    id: 1,
    studentA: 'Arjun Singh',
    studentB: 'Vikram Reddy',
    hammingDistance: 1,
    similarity: 95,
    status: 'Pending',
  },
  {
    id: 2,
    studentA: 'Meera Patel',
    studentB: 'Sneha Gupta',
    hammingDistance: 1,
    similarity: 90,
    status: 'Reviewed',
  },
  {
    id: 3,
    studentA: 'Karthik Nair',
    studentB: 'Rahul Verma',
    hammingDistance: 2,
    similarity: 85,
    status: 'Dismissed',
  },
]

function getStatusVariant(status) {
  if (status === 'Pending') return 'warning'
  if (status === 'Reviewed') return 'success'
  return 'default'
}

export default function SimilarityCheckerPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Similarity Checker</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Detect suspiciously similar quiz submissions using Hamming distance</p>
        </div>
      </motion.div>

      {/* Quiz Selector */}
      <motion.div variants={fadeUp} className="w-80">
        <Select label="Select Quiz" options={quizOptions} />
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeUp} className="grid grid-cols-3 gap-4">
        <StatCard label="TOTAL SUBMISSIONS" value="48" icon={FileText} />
        <StatCard label="FLAGGED PAIRS" value="3" icon={ShieldAlert} />
        <StatCard label="AVERAGE SIMILARITY" value="12%" />
      </motion.div>

      {/* Flagged Pairs Table */}
      <motion.div variants={fadeUp}>
        <Card padding={false}>
          <div className="px-4 pt-4 pb-2">
            <CardTitle>Flagged Pairs</CardTitle>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Student A</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Student B</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Hamming Distance</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Similarity %</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Status</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {flaggedPairs.map((pair, i) => (
                  <motion.tr
                    key={pair.id}
                    className="border-b border-[var(--border-default)] last:border-b-0"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 + i * 0.06 }}
                  >
                    <td className="px-4 py-3 text-[var(--text-primary)] font-medium">{pair.studentA}</td>
                    <td className="px-4 py-3 text-[var(--text-primary)] font-medium">{pair.studentB}</td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{pair.hammingDistance}</td>
                    <td className="px-4 py-3 font-semibold text-danger">{pair.similarity}%</td>
                    <td className="px-4 py-3">
                      <Badge variant={getStatusVariant(pair.status)} size="sm">{pair.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" icon={Eye}>Review</Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>

      {/* How it works */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-[var(--text-secondary)]" />
              <CardTitle>How it works</CardTitle>
            </div>
          </CardHeader>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
            Answers are encoded as binary vectors. Hamming distance measures bit differences between two answer
            vectors. Pairs with distance &lt; 2 on a 20-question quiz are flagged for review, as this indicates
            near-identical answer patterns that may warrant further investigation.
          </p>
        </Card>
      </motion.div>
    </motion.div>
  )
}

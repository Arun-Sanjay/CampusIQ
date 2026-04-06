import { motion } from 'framer-motion'
import {
  Users, FileText, Brain, TrendingUp,
  Upload, PlusCircle, Megaphone, ChevronRight,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import StatCard from '../../components/dashboard/StatCard'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const quickActions = [
  {
    title: 'Upload Document',
    description: 'Upload PDFs, DOCX, or PPTX files for AI processing',
    icon: Upload,
  },
  {
    title: 'Create Quiz',
    description: 'Generate quizzes automatically from your documents',
    icon: PlusCircle,
  },
  {
    title: 'Post Announcement',
    description: 'Notify students about deadlines and updates',
    icon: Megaphone,
  },
]

const recentUploads = [
  { name: 'DAA_Chapter5_Graphs.pdf', subject: 'Design & Analysis of Algorithms', date: 'Apr 5, 2026', status: 'Ready' },
  { name: 'OS_Deadlock_Notes.pdf', subject: 'Operating Systems', date: 'Apr 4, 2026', status: 'Ready' },
  { name: 'CN_Transport_Layer.docx', subject: 'Computer Networks', date: 'Apr 4, 2026', status: 'Processing' },
  { name: 'DBMS_Normalization.pptx', subject: 'Database Management', date: 'Apr 3, 2026', status: 'Ready' },
]

const statusVariant = {
  Ready: 'success',
  Processing: 'warning',
  Failed: 'danger',
}

export default function DashboardPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Stats Row */}
      <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
        {[
          { label: 'TOTAL STUDENTS', value: '156', icon: Users, trend: 5 },
          { label: 'DOCUMENTS', value: '42', icon: FileText, trend: 12 },
          { label: 'QUIZZES PUBLISHED', value: '18', icon: Brain, trend: 3 },
          { label: 'CLASS AVERAGE', value: '72%', icon: TrendingUp, trend: -2 },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.1 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <StatCard {...stat} />
          </motion.div>
        ))}
      </motion.div>

      {/* Quick Actions */}
      <motion.div variants={fadeUp}>
        <CardLabel className="mb-3 block">QUICK ACTIONS</CardLabel>
        <div className="grid grid-cols-3 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Card key={action.title} hover className="cursor-pointer group">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] group-hover:bg-primary/10 transition-colors">
                    <Icon className="h-5 w-5 text-[var(--text-secondary)] group-hover:text-primary transition-colors" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-[var(--text-primary)]">{action.title}</p>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{action.description}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                </div>
              </Card>
            )
          })}
        </div>
      </motion.div>

      {/* Recent Uploads */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader action={<span className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)]">View All</span>}>
            <CardTitle>Recent Uploads</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {recentUploads.map((doc) => (
              <div
                key={doc.name}
                className="flex items-center justify-between py-2 border-b border-[var(--border-default)] last:border-0"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="h-4 w-4 text-[var(--text-tertiary)] shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{doc.name}</p>
                    <p className="text-xs text-[var(--text-tertiary)]">{doc.subject}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <span className="text-xs text-[var(--text-tertiary)]">{doc.date}</span>
                  <Badge variant={statusVariant[doc.status]} size="sm" dot>{doc.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Class Performance Trend Placeholder */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Class Performance Trend</CardTitle>
          </CardHeader>
          <div className="h-48 flex items-center justify-center border border-dashed border-[var(--border-default)] rounded-lg">
            <p className="text-sm text-[var(--text-tertiary)]">Chart will render here</p>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}

import { motion } from 'framer-motion'
import { Plus, ChevronRight, FileText, Users, Brain } from 'lucide-react'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const subjects = [
  {
    code: 'CS341',
    name: 'Design & Analysis of Algorithms',
    description: 'Greedy methods, dynamic programming, graph algorithms, and NP-completeness',
    documents: 12,
    students: 156,
    quizzes: 4,
  },
  {
    code: 'CS302',
    name: 'Operating Systems',
    description: 'Process management, memory management, file systems, and deadlocks',
    documents: 9,
    students: 148,
    quizzes: 3,
  },
  {
    code: 'CS303',
    name: 'Computer Networks',
    description: 'OSI model, TCP/IP, routing algorithms, and network security',
    documents: 8,
    students: 152,
    quizzes: 5,
  },
  {
    code: 'CS401',
    name: 'Database Management Systems',
    description: 'Relational algebra, SQL, normalization, transactions, and indexing',
    documents: 7,
    students: 140,
    quizzes: 3,
  },
  {
    code: 'CS402',
    name: 'Machine Learning',
    description: 'Supervised learning, neural networks, clustering, and model evaluation',
    documents: 6,
    students: 98,
    quizzes: 3,
  },
]

export default function SubjectsPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">My Subjects</h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-0.5">{subjects.length} subjects this semester</p>
        </div>
        <Button icon={Plus}>Create Subject</Button>
      </motion.div>

      {/* Subject Grid */}
      <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {subjects.map((subject, i) => (
          <motion.div
            key={subject.code}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.1 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <Card hover className="cursor-pointer group">
              <div className="flex items-start justify-between mb-2">
                <Badge variant="primary" size="sm">{subject.code}</Badge>
                <ChevronRight className="h-4 w-4 text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] text-sm mb-1">{subject.name}</h3>
              <p className="text-xs text-[var(--text-tertiary)] line-clamp-1 mb-3">{subject.description}</p>
              <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
                <span className="inline-flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {subject.documents} documents
                </span>
                <span className="inline-flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {subject.students} students
                </span>
                <span className="inline-flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  {subject.quizzes} quizzes
                </span>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  )
}

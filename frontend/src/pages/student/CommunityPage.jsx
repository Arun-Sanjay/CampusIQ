import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, Plus, MessageCircle, ThumbsUp, Clock, Bot } from 'lucide-react'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'

const stagger = {
  animate: { transition: { staggerChildren: 0.06 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const filterTags = ['All', 'DAA', 'CN', 'DMS', 'OS']

const doubts = [
  {
    id: 1,
    title: 'Why does Dijkstra fail with negative edge weights?',
    body: 'I understand that Dijkstra uses a greedy approach and picks the shortest known distance at each step, but can someone explain with a concrete example why negative edges break it? Bellman-Ford handles this, but...',
    tags: ['DAA', 'Graph Theory'],
    answers: 5,
    upvotes: 18,
    time: '45m ago',
    aiAnswered: true,
  },
  {
    id: 2,
    title: 'Difference between TCP and UDP — when to use each?',
    body: 'I know TCP is reliable and UDP is faster, but in practical scenarios like gaming, video streaming, or file transfer, what decides which protocol to use? Are there cases where UDP is preferred even when...',
    tags: ['CN', 'Transport Layer'],
    answers: 3,
    upvotes: 12,
    time: '2h ago',
    aiAnswered: true,
  },
  {
    id: 3,
    title: 'How do you prove a relation is an equivalence relation?',
    body: 'I need to prove reflexive, symmetric, and transitive properties but I keep getting confused with the notation. For example, if R = {(a,b) | a - b is divisible by 3}, how do I write the formal proof...',
    tags: ['DMS', 'Relations'],
    answers: 2,
    upvotes: 8,
    time: '3h ago',
    aiAnswered: false,
  },
  {
    id: 4,
    title: 'Banker\'s Algorithm vs Deadlock Detection — exam tips?',
    body: 'Both seem similar in terms of the matrices used (Available, Max, Allocation, Need). What are the key differences the professor might ask about in the exam? Also, is there a shortcut for the safety...',
    tags: ['OS', 'Deadlocks'],
    answers: 7,
    upvotes: 24,
    time: '5h ago',
    aiAnswered: false,
  },
  {
    id: 5,
    title: 'BCNF decomposition losing functional dependencies',
    body: 'When decomposing a relation into BCNF, sometimes we lose functional dependencies that were present in the original relation. Is it always the case? How do we check for lossless join and dependency...',
    tags: ['DBMS', 'Normalization'],
    answers: 1,
    upvotes: 6,
    time: '1d ago',
    aiAnswered: true,
  },
]

export default function CommunityPage() {
  const [activeFilter, setActiveFilter] = useState('All')
  const [search, setSearch] = useState('')

  const filtered = doubts.filter((d) => {
    if (activeFilter !== 'All' && !d.tags.includes(activeFilter)) return false
    if (search && !d.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="space-y-5">
      {/* Top Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px] max-w-sm">
          <Input
            icon={Search}
            placeholder="Search doubts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button icon={Plus} size="md">
          Ask a Doubt
        </Button>
        <div className="flex gap-1.5 flex-wrap">
          {filterTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveFilter(tag)}
              className={`px-3 py-1.5 text-xs rounded-full border font-medium transition-all ${
                activeFilter === tag
                  ? 'bg-primary/10 text-[var(--text-primary)] border-primary/20'
                  : 'border-[var(--border-default)] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:border-[var(--border-strong)]'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Doubt Cards */}
      <motion.div className="space-y-3" variants={stagger} initial="initial" animate="animate">
        {filtered.map((doubt) => (
          <motion.div key={doubt.id} variants={fadeUp}>
            <Card hover className="space-y-3 cursor-pointer">
              <div className="flex items-start justify-between gap-4">
                <h3 className="font-semibold text-[var(--text-primary)] text-sm leading-snug">
                  {doubt.title}
                </h3>
                {doubt.aiAnswered && (
                  <Badge variant="info" size="sm" className="shrink-0">
                    <Bot className="h-3 w-3" />
                    AI Answered
                  </Badge>
                )}
              </div>

              <p className="text-xs text-[var(--text-secondary)] leading-relaxed line-clamp-2">
                {doubt.body}
              </p>

              <div className="flex items-center justify-between">
                <div className="flex gap-1.5">
                  {doubt.tags.map((tag) => (
                    <Badge key={tag} size="sm">{tag}</Badge>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-[var(--text-tertiary)]">
                  <span className="flex items-center gap-1">
                    <MessageCircle className="h-3 w-3" />
                    {doubt.answers} answers
                  </span>
                  <span className="flex items-center gap-1">
                    <ThumbsUp className="h-3 w-3" />
                    {doubt.upvotes} upvotes
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {doubt.time}
                  </span>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}

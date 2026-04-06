import { useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, BookOpen } from 'lucide-react'
import ChatLayout from '../../components/chat/ChatLayout'
import Badge from '../../components/ui/Badge'

const subjects = [
  { name: 'DAA', fullName: 'Design & Analysis of Algorithms', docs: 12 },
  { name: 'CN', fullName: 'Computer Networks', docs: 8 },
  { name: 'DMS', fullName: 'Discrete Mathematics', docs: 6 },
  { name: 'OS', fullName: 'Operating Systems', docs: 10 },
  { name: 'DBMS', fullName: 'Database Management Systems', docs: 9 },
]

const initialMessages = [
  {
    role: 'user',
    content: 'Explain TCP 3-way handshake in simple terms',
  },
  {
    role: 'assistant',
    content: `The TCP 3-way handshake is a process used to establish a reliable connection between a client and server before data transfer begins. Here's how it works:

1. SYN — The client sends a SYN (synchronize) packet to the server, indicating it wants to start a connection. It includes an initial sequence number.

2. SYN-ACK — The server responds with a SYN-ACK packet, acknowledging the client's SYN and sending its own sequence number.

3. ACK — The client sends an ACK (acknowledge) packet back to the server, confirming receipt of the server's SYN-ACK.

After these three steps, the connection is established and data can flow in both directions. This process ensures both sides are ready and agree on initial sequence numbers for reliable, ordered delivery.`,
    sources: ['CN Chapter 4 — Transport Layer', 'CN Lecture 12 — TCP Protocol'],
  },
  {
    role: 'user',
    content: 'What happens if the ACK packet is lost?',
  },
  {
    role: 'assistant',
    content: `If the final ACK packet is lost during the 3-way handshake, the server will remain in a SYN-RECEIVED state. Here's what happens:

- The server starts a retransmission timer after sending SYN-ACK
- If it doesn't receive the ACK within the timeout period, it retransmits the SYN-ACK
- The client, which is already in ESTABLISHED state, will re-send the ACK upon receiving the duplicate SYN-ACK
- If retransmissions exceed the maximum retry count, the server aborts the connection attempt

This is one reason TCP is considered reliable — it handles packet loss gracefully through retransmission mechanisms.`,
    sources: ['CN Chapter 4 — Transport Layer', 'CN Lab Manual — Wireshark TCP Analysis'],
  },
]

const suggestedQuestions = [
  'Explain TCP 3-way handshake',
  "What is Dijkstra's algorithm?",
  'Summarize Chapter 5 notes',
]

const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

export default function NoteAssistantPage() {
  const [activeSubject, setActiveSubject] = useState('CN')
  const [messages, setMessages] = useState(initialMessages)

  const handleSend = (text) => {
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
    ])
  }

  const leftPanel = (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3 px-2">
        <BookOpen className="h-4 w-4 text-[var(--text-tertiary)]" />
        <span className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Subjects</span>
      </div>
      {subjects.map((subject) => (
        <motion.button
          key={subject.name}
          variants={fadeUp}
          initial="initial"
          animate="animate"
          onClick={() => setActiveSubject(subject.name)}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
            activeSubject === subject.name
              ? 'bg-primary/10 text-[var(--text-primary)]'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <FileText className="h-3.5 w-3.5 shrink-0" />
            <div className="min-w-0">
              <span className="text-sm font-medium block">{subject.name}</span>
              <span className="text-[10px] text-[var(--text-tertiary)] truncate block">{subject.fullName}</span>
            </div>
          </div>
          <Badge size="sm" variant={activeSubject === subject.name ? 'primary' : 'default'}>
            {subject.docs}
          </Badge>
        </motion.button>
      ))}
    </div>
  )

  return (
    <ChatLayout
      messages={messages}
      onSend={handleSend}
      placeholder={`Ask about ${activeSubject} notes...`}
      leftPanel={leftPanel}
      suggestedQuestions={suggestedQuestions}
    />
  )
}

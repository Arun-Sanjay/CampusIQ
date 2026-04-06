import { useState } from 'react'
import { motion } from 'framer-motion'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import ChatLayout from '../../components/chat/ChatLayout'

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const suggestedQuestions = [
  "What's the TCS interview process?",
  'CGPA cutoff for Google?',
  'How to prepare for Amazon in 2 weeks?',
  'Best elective for product roles?',
]

const initialMessages = [
  {
    role: 'user',
    content: "What's the typical Google interview process?",
  },
  {
    role: 'assistant',
    content:
      "Google's interview process for new grads typically has 5 stages:\n\n1. **Online Assessment** \u2014 2 coding problems on a shared doc, 90 minutes. Focus on arrays, strings, and graph problems.\n\n2. **Phone Screen** \u2014 45-minute call with an engineer. One medium-hard coding problem with follow-ups.\n\n3. **Onsite (Virtual)** \u2014 4-5 rounds over one day:\n   - 2 Coding rounds (DSA focus)\n   - 1 System Design round\n   - 1 Googleyness & Leadership round\n   - 1 Hiring Manager chat\n\n4. **Hiring Committee Review** \u2014 Your packet is reviewed. This can take 2-4 weeks.\n\n5. **Offer** \u2014 Team matching, then the offer letter.\n\nBased on your profile (8.5 CGPA, strong in Python & SQL), I'd recommend focusing on DSA practice \u2014 especially graphs and dynamic programming. Your CGPA meets Google's typical cutoff of 7.0+.",
  },
]

export default function PlacementChatPage() {
  const [messages, setMessages] = useState(initialMessages)

  const handleSend = (text) => {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: text },
    ])
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content:
            "That's a great question! Based on your current profile and target companies, I'd recommend focusing on strengthening your DSA skills first, followed by system design fundamentals. Would you like me to create a personalized study plan?",
        },
      ])
    }, 600)
  }

  const rightPanel = (
    <motion.div variants={fadeUp} initial="initial" animate="animate">
      <Card>
        <CardHeader>
          <CardTitle>Your Profile</CardTitle>
        </CardHeader>
        <div className="space-y-3">
          <div>
            <CardLabel>Branch</CardLabel>
            <p className="text-sm text-[var(--text-primary)]">B.Tech CS</p>
          </div>
          <div>
            <CardLabel>Semester</CardLabel>
            <p className="text-sm text-[var(--text-primary)]">4</p>
          </div>
          <div>
            <CardLabel>CGPA</CardLabel>
            <p className="text-sm text-[var(--text-primary)]">8.5</p>
          </div>
          <div>
            <CardLabel>Target</CardLabel>
            <p className="text-sm text-[var(--text-primary)]">Google, Amazon</p>
          </div>
          <div>
            <CardLabel>Skills</CardLabel>
            <div className="flex flex-wrap gap-1.5 mt-1">
              <Badge variant="primary" size="sm">Python</Badge>
              <Badge variant="primary" size="sm">SQL</Badge>
              <Badge variant="primary" size="sm">React</Badge>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )

  return (
    <ChatLayout
      messages={messages}
      onSend={handleSend}
      placeholder="Ask about placements, companies, preparation..."
      rightPanel={rightPanel}
      suggestedQuestions={suggestedQuestions}
    />
  )
}

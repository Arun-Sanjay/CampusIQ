import { useState } from 'react'
import { Info } from 'lucide-react'
import ChatLayout from '../../components/chat/ChatLayout'
import Card from '../../components/ui/Card'

const initialMessages = [
  {
    role: 'user',
    content: 'What is the minimum attendance for labs?',
  },
  {
    role: 'assistant',
    content: `According to the college handbook (Academic Regulations 2024-25, Section 4.2):

The minimum attendance requirement for laboratory sessions is 85%. This is higher than the 75% requirement for theory classes.

Key points:
- Students falling below 85% lab attendance will be marked "Detained" for that subject
- Medical certificates can cover up to 10% of total sessions, but must be submitted within 7 days
- Lab attendance is tracked separately from theory attendance
- Condonation for lab attendance below 85% is NOT permitted, unlike theory subjects

If you're close to the threshold, speak to your lab instructor early — some departments allow makeup sessions at the end of the semester.`,
    sources: ['College Handbook — Academic Regulations 2024-25'],
  },
]

const suggestedQuestions = [
  'What is the attendance rule for labs?',
  'Which elective helps for product roles?',
  "What's the average package at Infosys?",
  'Hostel rules for first years?',
]

export default function CollegeGPTPage() {
  const [messages, setMessages] = useState(initialMessages)

  const handleSend = (text) => {
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
    ])
  }

  return (
    <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
      <Card className="flex items-center gap-3 py-3 shrink-0">
        <Info className="h-4 w-4 text-info shrink-0" />
        <span className="text-sm text-[var(--text-secondary)]">
          CollegeGPT answers from your college's official documents
        </span>
      </Card>

      <div className="flex-1 min-h-0">
        <ChatLayout
          messages={messages}
          onSend={handleSend}
          placeholder="Ask about college rules, placements, faculty..."
          suggestedQuestions={suggestedQuestions}
          className="!h-full"
        />
      </div>
    </div>
  )
}

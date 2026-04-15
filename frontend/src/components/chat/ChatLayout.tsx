import { useRef, useEffect } from 'react'
import type { ReactNode } from 'react'
import { clsx } from 'clsx'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'

export interface ChatLayoutMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
}

export interface ChatLayoutProps {
  messages?: ChatLayoutMessage[]
  onSend: (text: string) => void
  placeholder?: string
  disabled?: boolean
  leftPanel?: ReactNode
  rightPanel?: ReactNode
  suggestedQuestions?: string[]
  className?: string
}

export default function ChatLayout({
  messages = [],
  onSend,
  placeholder,
  disabled = false,
  leftPanel,
  rightPanel,
  suggestedQuestions,
  className,
}: ChatLayoutProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className={clsx('flex gap-4 h-[calc(100vh-8rem)]', className)}>
      {leftPanel && (
        <div className="w-56 shrink-0 overflow-y-auto">{leftPanel}</div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.length === 0 && suggestedQuestions && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="text-[var(--text-tertiary)] text-sm">Ask anything about your course materials</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => onSend(q)}
                    className="px-3 py-1.5 text-xs rounded-full border border-[var(--border-default)]
                               text-[var(--text-secondary)] hover:text-[var(--text-primary)]
                               hover:border-[var(--border-strong)] transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} {...msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-[var(--border-default)] pt-3">
          <ChatInput onSend={onSend} placeholder={placeholder} disabled={disabled} />
        </div>
      </div>

      {rightPanel && (
        <div className="w-64 shrink-0 overflow-y-auto">{rightPanel}</div>
      )}
    </div>
  )
}

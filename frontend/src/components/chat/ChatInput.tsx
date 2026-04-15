import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { clsx } from 'clsx'

export interface ChatInputProps {
  onSend: (text: string) => void
  placeholder?: string
  disabled?: boolean
}

export default function ChatInput({ onSend, placeholder = 'Type your message...', disabled = false }: ChatInputProps) {
  const [value, setValue] = useState<string>('')

  const handleSubmit = (e: FormEvent | KeyboardEvent) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-1">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={clsx(
            'input-base w-full resize-none min-h-[42px] max-h-32',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        />
      </div>
      <button
        type="submit"
        disabled={!value.trim() || disabled}
        className={clsx(
          'p-2.5 rounded-lg transition-all duration-200',
          value.trim() && !disabled
            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
            : 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] cursor-not-allowed',
        )}
      >
        <Send className="h-4 w-4" />
      </button>
    </form>
  )
}

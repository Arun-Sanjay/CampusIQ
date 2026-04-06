import { clsx } from 'clsx'
import Avatar from '../ui/Avatar'
import { Bot } from 'lucide-react'

export default function ChatMessage({ role, content, sources, isStreaming }) {
  const isUser = role === 'user'

  return (
    <div className={clsx('flex gap-3', isUser && 'flex-row-reverse')}>
      {isUser ? (
        <Avatar name="You" size="sm" className="shrink-0 mt-1" />
      ) : (
        <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center shrink-0 mt-1">
          <Bot className="h-3.5 w-3.5 text-primary-foreground" />
        </div>
      )}

      <div className={clsx('max-w-[75%] space-y-2', isUser && 'items-end')}>
        <div
          className={clsx(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-md'
              : 'card rounded-tl-md text-[var(--text-primary)]',
          )}
        >
          <div className="whitespace-pre-wrap">{content}</div>
          {isStreaming && (
            <span className="inline-flex gap-1 ml-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce" />
            </span>
          )}
        </div>

        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {sources.map((src, i) => (
              <button
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-md
                           card text-[var(--text-secondary)]
                           hover:text-[var(--text-primary)] transition-colors"
              >
                <span>📄</span>
                <span>{src}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

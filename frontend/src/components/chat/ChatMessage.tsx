import { clsx } from 'clsx'
import { Bot } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import Avatar from '../ui/Avatar'

export interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
}

// Markdown component overrides — small, opinionated, themed via CSS variables so
// they look at home in any of the 5 themes (light / dark / premium / aurora /
// luxury). Keeps the rhythm of Claude's web UI: tighter headings than default
// browser styles, code blocks with their own surface, indented lists.
const markdownComponents: Components = {
  h1: ({ node: _n, ...props }) => (
    <h1
      className="text-lg font-bold mt-2 mb-1.5 text-[var(--text-primary)]"
      {...props}
    />
  ),
  h2: ({ node: _n, ...props }) => (
    <h2
      className="text-base font-bold mt-2 mb-1.5 text-[var(--text-primary)]"
      {...props}
    />
  ),
  h3: ({ node: _n, ...props }) => (
    <h3
      className="text-sm font-semibold mt-2 mb-1 text-[var(--text-primary)]"
      {...props}
    />
  ),
  h4: ({ node: _n, ...props }) => (
    <h4
      className="text-sm font-semibold mt-1.5 mb-1 text-[var(--text-primary)]"
      {...props}
    />
  ),
  p: ({ node: _n, ...props }) => (
    <p className="my-1.5 leading-relaxed" {...props} />
  ),
  ul: ({ node: _n, ...props }) => (
    <ul className="my-1.5 pl-5 list-disc space-y-1" {...props} />
  ),
  ol: ({ node: _n, ...props }) => (
    <ol className="my-1.5 pl-5 list-decimal space-y-1" {...props} />
  ),
  li: ({ node: _n, ...props }) => (
    <li className="leading-relaxed" {...props} />
  ),
  strong: ({ node: _n, ...props }) => (
    <strong className="font-semibold text-[var(--text-primary)]" {...props} />
  ),
  em: ({ node: _n, ...props }) => <em className="italic" {...props} />,
  a: ({ node: _n, ...props }) => (
    <a
      className="text-primary underline underline-offset-2 hover:opacity-80"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    />
  ),
  blockquote: ({ node: _n, ...props }) => (
    <blockquote
      className="border-l-2 border-[var(--border-strong)] pl-3 my-2 text-[var(--text-secondary)] italic"
      {...props}
    />
  ),
  hr: ({ node: _n, ...props }) => (
    <hr className="my-3 border-[var(--border-default)]" {...props} />
  ),
  code: ({ node: _n, className, children, ...props }) => {
    // react-markdown sends `inline=true` for spans inside paragraphs and
    // omits it for fenced blocks. v9+ stopped exposing that prop directly,
    // so we sniff for the language- class instead.
    const isBlock = (className ?? '').startsWith('language-')
    if (isBlock) {
      return (
        <code
          className={clsx(
            'block whitespace-pre overflow-x-auto rounded-md px-3 py-2 my-2 text-[12.5px] font-mono',
            'bg-[var(--bg-tertiary)] border border-[var(--border-default)] text-[var(--text-primary)]',
          )}
          {...props}
        >
          {children}
        </code>
      )
    }
    return (
      <code
        className="px-1 py-0.5 rounded text-[12.5px] font-mono bg-[var(--bg-tertiary)] border border-[var(--border-default)] text-[var(--text-primary)]"
        {...props}
      >
        {children}
      </code>
    )
  },
  pre: ({ node: _n, children, ...props }) => (
    // The code block's <code> already renders its own surface; we only need
    // <pre> to wipe browser defaults and prevent double-padding.
    <pre className="my-2 not-prose" {...props}>
      {children}
    </pre>
  ),
  table: ({ node: _n, ...props }) => (
    <div className="my-2 overflow-x-auto">
      <table
        className="w-full text-[12.5px] border-collapse border border-[var(--border-default)]"
        {...props}
      />
    </div>
  ),
  th: ({ node: _n, ...props }) => (
    <th
      className="text-left font-semibold px-2 py-1 border border-[var(--border-default)] bg-[var(--bg-tertiary)]"
      {...props}
    />
  ),
  td: ({ node: _n, ...props }) => (
    <td className="px-2 py-1 border border-[var(--border-default)]" {...props} />
  ),
}

export default function ChatMessage({ role, content, sources, isStreaming }: ChatMessageProps) {
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
              ? 'bg-primary text-primary-foreground rounded-tr-md whitespace-pre-wrap'
              : 'card rounded-tl-md text-[var(--text-primary)] chat-markdown',
          )}
        >
          {isUser ? (
            content
          ) : (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {content}
              </ReactMarkdown>
              {/* Trim the awkward extra margin react-markdown leaves on the
                  very first/last children inside the bubble. */}
              <style>{`
                .chat-markdown > :first-child { margin-top: 0 !important; }
                .chat-markdown > :last-child { margin-bottom: 0 !important; }
              `}</style>
            </>
          )}
          {isStreaming && (
            <span className="inline-flex gap-1 ml-1 align-middle">
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

import { clsx } from 'clsx'

export default function Card({
  children,
  hover = false,
  padding = true,
  className,
  ...props
}) {
  return (
    <div
      className={clsx(
        hover ? 'card-hover' : 'card',
        padding && 'p-4',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, action, className }) {
  return (
    <div className={clsx('flex items-center justify-between mb-3', className)}>
      <div>{children}</div>
      {action && <div>{action}</div>}
    </div>
  )
}

export function CardTitle({ children, className }) {
  return (
    <h3 className={clsx('font-semibold text-[var(--text-primary)]', className)}>{children}</h3>
  )
}

export function CardLabel({ children, className }) {
  return (
    <span className={clsx('label', className)}>{children}</span>
  )
}

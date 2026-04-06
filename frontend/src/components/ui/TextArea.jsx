import { clsx } from 'clsx'
import { forwardRef } from 'react'

const TextArea = forwardRef(({
  label,
  error,
  className,
  rows = 3,
  ...props
}, ref) => {
  return (
    <div className="space-y-1.5">
      {label && <label className="label">{label}</label>}
      <textarea
        ref={ref}
        rows={rows}
        className={clsx(
          'input-base w-full resize-none',
          error && 'border-danger/50 focus:border-danger focus:ring-danger/20',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
})

TextArea.displayName = 'TextArea'
export default TextArea

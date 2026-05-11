/**
 * Common shared types used across the app.
 */
import type { LucideIcon } from 'lucide-react'

export type { LucideIcon }

/** Theme variants — only light & dark now. Earlier premium / aurora / luxury
 *  were dropped (visually noisy, didn't earn their weight). */
export type Theme = 'light' | 'dark'

/** Generic API response wrapper for list endpoints */
export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** Utility: extract props from a JSX component type */
export type PropsOf<C> = C extends (props: infer P) => unknown ? P : never

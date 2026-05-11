import { describe, expect, it } from 'vitest'

import { wordDiff } from '../utils/wordDiff'

describe('wordDiff', () => {
  it('produces a single "same" segment for identical strings', () => {
    const segs = wordDiff('Lab attendance is 80%.', 'Lab attendance is 80%.')
    expect(segs).toHaveLength(1)
    expect(segs[0]!.op).toBe('same')
    expect(segs[0]!.text).toBe('Lab attendance is 80%.')
  })

  it('marks added text as "add" only', () => {
    const segs = wordDiff(
      'Lab attendance is 80%.',
      'Lab attendance is 80%. Mandatory effective this term.',
    )
    expect(segs.find((s) => s.op === 'remove')).toBeUndefined()
    const added = segs.filter((s) => s.op === 'add').map((s) => s.text).join('')
    expect(added).toContain('Mandatory effective this term')
  })

  it('marks removed text as "remove" only', () => {
    const segs = wordDiff(
      'Lab attendance is 80%. Mandatory effective this term.',
      'Lab attendance is 80%.',
    )
    expect(segs.find((s) => s.op === 'add')).toBeUndefined()
    const removed = segs.filter((s) => s.op === 'remove').map((s) => s.text).join('')
    expect(removed).toContain('Mandatory effective this term')
  })

  it('mixes add + remove + same when a value changes', () => {
    const segs = wordDiff(
      'Lab attendance is 80% as of the current handbook.',
      'Lab attendance is 75% as of the current handbook.',
    )
    const ops = new Set(segs.map((s) => s.op))
    expect(ops.has('same')).toBe(true)
    expect(ops.has('add')).toBe(true)
    expect(ops.has('remove')).toBe(true)
  })
})

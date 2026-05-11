/**
 * Word-level LCS diff for the Knowledge Editor's edit-preview UI.
 *
 * We want to render side-by-side current vs proposed text with additions
 * highlighted green and removals struck through red. Character-level diff
 * is too noisy for prose; word-level reads cleanly.
 *
 * Returns the diff as an array of segments, each tagged "same" | "remove"
 * | "add". Consumers render the segments with the appropriate styling.
 *
 * Implementation: classic O(m*n) LCS. Inputs are sliced into words by
 * splitting on whitespace; the splitter preserves the original whitespace
 * so re-joining gives back a faithful reconstruction.
 */

export type DiffOp = 'same' | 'remove' | 'add'

export interface DiffSegment {
  op: DiffOp
  text: string
}

const splitWords = (input: string): string[] => {
  // Split on whitespace boundaries while keeping the runs of whitespace as
  // their own tokens (so "hello world" → ["hello", " ", "world"]).
  // This way re-joining segments gives back the original spacing.
  if (!input) return []
  return input.split(/(\s+)/).filter((t) => t.length > 0)
}

const buildLcsTable = (a: string[], b: string[]): number[][] => {
  const m = a.length
  const n = b.length
  const table: number[][] = Array.from({ length: m + 1 }, () =>
    new Array<number>(n + 1).fill(0),
  )
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        table[i]![j] = table[i - 1]![j - 1]! + 1
      } else {
        const up = table[i - 1]![j]!
        const left = table[i]![j - 1]!
        table[i]![j] = up >= left ? up : left
      }
    }
  }
  return table
}

const mergeAdjacent = (segments: DiffSegment[]): DiffSegment[] => {
  const out: DiffSegment[] = []
  for (const seg of segments) {
    const last = out[out.length - 1]
    if (last && last.op === seg.op) {
      last.text += seg.text
    } else {
      out.push({ ...seg })
    }
  }
  return out
}

export const wordDiff = (current: string, proposed: string): DiffSegment[] => {
  const a = splitWords(current)
  const b = splitWords(proposed)

  if (a.length === 0 && b.length === 0) return []
  if (a.length === 0) return [{ op: 'add', text: proposed }]
  if (b.length === 0) return [{ op: 'remove', text: current }]

  const table = buildLcsTable(a, b)
  // Walk backwards through the LCS table to recover the diff path.
  const reversed: DiffSegment[] = []
  let i = a.length
  let j = b.length
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      reversed.push({ op: 'same', text: a[i - 1]! })
      i--
      j--
    } else if (table[i - 1]![j]! >= table[i]![j - 1]!) {
      reversed.push({ op: 'remove', text: a[i - 1]! })
      i--
    } else {
      reversed.push({ op: 'add', text: b[j - 1]! })
      j--
    }
  }
  while (i > 0) {
    reversed.push({ op: 'remove', text: a[i - 1]! })
    i--
  }
  while (j > 0) {
    reversed.push({ op: 'add', text: b[j - 1]! })
    j--
  }

  return mergeAdjacent(reversed.reverse())
}

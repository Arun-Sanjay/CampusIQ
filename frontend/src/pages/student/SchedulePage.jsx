import { motion } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const hours = Array.from({ length: 13 }, (_, i) => i + 9) // 9am to 9pm

const subjectColors = {
  DAA: 'bg-info/15 border-info/30 text-info',
  CN: 'bg-feature-place/15 border-feature-place/30 text-feature-place',
  DMS: 'bg-success/15 border-success/30 text-success',
  OS: 'bg-warning/15 border-warning/30 text-warning',
  Lab: 'bg-danger/15 border-danger/30 text-danger',
}

// schedule[dayIndex][hour] = { subject, room, span? } or 'break'/'lunch' or null
const schedule = {
  0: { // Mon
    9: { subject: 'DAA', room: 'LH-301' },
    10: { subject: 'CN', room: 'LH-204' },
    11: { subject: 'DMS', room: 'LH-102' },
    13: 'lunch',
    14: { subject: 'Lab', room: 'Lab-A2', span: 2 },
    17: { subject: 'OS', room: 'LH-301' },
  },
  1: { // Tue
    9: { subject: 'CN', room: 'LH-204' },
    10: { subject: 'OS', room: 'LH-301' },
    11: 'break',
    12: { subject: 'DAA', room: 'LH-301' },
    13: 'lunch',
    14: { subject: 'DMS', room: 'LH-102' },
    16: { subject: 'Lab', room: 'Lab-B1', span: 2 },
  },
  2: { // Wed
    9: { subject: 'DMS', room: 'LH-102' },
    10: { subject: 'DAA', room: 'LH-301' },
    11: { subject: 'CN', room: 'LH-204' },
    13: 'lunch',
    14: { subject: 'OS', room: 'LH-301' },
    15: 'break',
    16: { subject: 'DAA', room: 'LH-301' },
  },
  3: { // Thu
    9: { subject: 'OS', room: 'LH-301' },
    10: { subject: 'DMS', room: 'LH-102' },
    11: { subject: 'CN', room: 'LH-204' },
    13: 'lunch',
    14: { subject: 'Lab', room: 'Lab-A2', span: 2 },
    17: { subject: 'DAA', room: 'LH-301' },
  },
  4: { // Fri
    9: { subject: 'CN', room: 'LH-204' },
    10: { subject: 'DAA', room: 'LH-301' },
    11: 'break',
    12: { subject: 'OS', room: 'LH-301' },
    13: 'lunch',
    14: { subject: 'DMS', room: 'LH-102' },
    15: { subject: 'Lab', room: 'Lab-B1', span: 2 },
  },
  5: { // Sat
    9: { subject: 'DAA', room: 'LH-301' },
    10: { subject: 'CN', room: 'LH-204' },
    11: 'break',
  },
  6: {}, // Sun — empty
}

const constraints = [
  'No heavy subjects back-to-back',
  'Lunch 1-2pm',
  'Labs in afternoon only',
  'Free Sunday',
]

// Which hours are covered by a span from a previous slot
function isSpannedOver(dayIdx, hour) {
  const daySchedule = schedule[dayIdx] || {}
  for (let h = hour - 1; h >= 9; h--) {
    const slot = daySchedule[h]
    if (slot && typeof slot === 'object' && slot.span && h + slot.span > hour) {
      return true
    }
  }
  return false
}

function formatHour(h) {
  if (h === 12) return '12 PM'
  if (h > 12) return `${h - 12} PM`
  return `${h} AM`
}

export default function SchedulePage() {
  return (
    <motion.div className="space-y-5" variants={fadeUp} initial="initial" animate="animate">
      {/* Top Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {constraints.map((c) => (
            <span
              key={c}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full
                         border border-[var(--border-default)] text-[var(--text-secondary)]
                         bg-[var(--bg-tertiary)]"
            >
              {c}
              <X className="h-3 w-3 text-[var(--text-tertiary)] cursor-pointer hover:text-[var(--text-primary)]" />
            </span>
          ))}
        </div>
        <Button icon={Sparkles} size="md">
          Generate Schedule
        </Button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {Object.entries(subjectColors).map(([subject, classes]) => (
          <div key={subject} className="flex items-center gap-1.5">
            <div className={`h-3 w-3 rounded-sm border ${classes}`} />
            <span className="text-xs text-[var(--text-secondary)]">{subject}</span>
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <Card padding={false} className="overflow-x-auto">
        <div
          className="grid min-w-[800px]"
          style={{
            gridTemplateColumns: '72px repeat(7, 1fr)',
            gridTemplateRows: `40px repeat(${hours.length}, 56px)`,
          }}
        >
          {/* Header: empty corner + day names */}
          <div className="border-b border-r border-[var(--border-default)]" />
          {days.map((day, i) => (
            <div
              key={day}
              className={`flex items-center justify-center text-xs font-semibold border-b border-[var(--border-default)] ${
                i < 6 ? 'border-r' : ''
              } ${i === 6 ? 'text-[var(--text-tertiary)]' : 'text-[var(--text-primary)]'}`}
            >
              {day}
            </div>
          ))}

          {/* Time slots */}
          {hours.map((hour, rowIdx) => (
            <>
              {/* Time label */}
              <div
                key={`time-${hour}`}
                className="flex items-start justify-end pr-3 pt-1 text-[10px] text-[var(--text-tertiary)] border-r border-[var(--border-default)]"
              >
                {formatHour(hour)}
              </div>

              {/* Day cells */}
              {days.map((day, dayIdx) => {
                if (isSpannedOver(dayIdx, hour)) return null

                const slot = (schedule[dayIdx] || {})[hour]
                const isLast = dayIdx < 6
                const span = slot && typeof slot === 'object' && slot.span ? slot.span : 1

                if (!slot) {
                  return (
                    <div
                      key={`${dayIdx}-${hour}`}
                      className={`border-b border-[var(--border-default)] ${isLast ? 'border-r' : ''}`}
                    />
                  )
                }

                if (slot === 'lunch' || slot === 'break') {
                  return (
                    <div
                      key={`${dayIdx}-${hour}`}
                      className={`flex items-center justify-center text-[10px] text-[var(--text-tertiary)] italic border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] ${isLast ? 'border-r' : ''}`}
                      style={span > 1 ? { gridRow: `span ${span}` } : undefined}
                    >
                      {slot === 'lunch' ? 'Lunch' : 'Break'}
                    </div>
                  )
                }

                const colors = subjectColors[slot.subject] || 'bg-[var(--bg-tertiary)] border-[var(--border-default)] text-[var(--text-primary)]'

                return (
                  <div
                    key={`${dayIdx}-${hour}`}
                    className={`p-1.5 border-b border-[var(--border-default)] ${isLast ? 'border-r' : ''}`}
                    style={span > 1 ? { gridRow: `span ${span}` } : undefined}
                  >
                    <div className={`h-full rounded-md border px-2 py-1 flex flex-col justify-center ${colors}`}>
                      <span className="text-xs font-semibold leading-tight">{slot.subject}</span>
                      <span className="text-[10px] opacity-70">{slot.room}</span>
                    </div>
                  </div>
                )
              })}
            </>
          ))}
        </div>
      </Card>
    </motion.div>
  )
}

import { motion } from 'framer-motion'
import { Mic } from 'lucide-react'

const reveal = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
}

export default function InterviewShowcase() {
  return (
    <section id="interview" className="section">
      <div className="container">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 56,
            alignItems: 'center',
          }}
        >
          <motion.div
            {...reveal}
            style={{ position: 'relative', minHeight: 420, order: 1 }}
          >
            <span
              aria-hidden
              className="halo"
              style={{
                width: 320,
                height: 320,
                background: 'radial-gradient(circle, rgba(34,211,238,0.45), transparent 60%)',
                bottom: '-60px',
                left: '-40px',
              }}
            />
            <div
              className="glass"
              style={{
                aspectRatio: '4 / 3',
                width: '100%',
                position: 'relative',
                zIndex: 1,
                padding: 0,
                overflow: 'hidden',
              }}
            >
              <img
                src="/img/interview-personas.png"
                alt="Five AI persona orbs representing the five interview rounds"
                loading="eager"
                decoding="async"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: 'block',
                }}
              />
            </div>
          </motion.div>

          <motion.div
            {...reveal}
            transition={{ ...reveal.transition, delay: 0.1 }}
            style={{ order: 2 }}
          >
            <span className="chip" style={{ marginBottom: 20 }}>
              <Mic size={12} strokeWidth={2.5} />
              DEMO SHOWSTOPPER — PHASE 20
            </span>
            <h2
              className="display"
              style={{
                fontSize: 'clamp(32px, 4.5vw, 52px)',
                margin: '0 0 20px',
              }}
            >
              Five rounds. Five voices.{' '}
              <span className="gradient-text">One verdict.</span>
            </h2>
            <p
              style={{
                fontSize: 16,
                lineHeight: 1.7,
                color: 'var(--landing-fg-muted)',
                marginBottom: 28,
              }}
            >
              A full-loop voice mock interview across HR, technical, system design, managerial, and negotiation rounds. Claude scores every answer 0–10, advances you between rounds, and ships a final hire/no-hire debrief with strengths, gaps, and your standout answer.
            </p>
            <ul
              style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              {[
                'ElevenLabs Scribe ASR + a different voice per round.',
                '4 personas: Friendly, Tough, Rapid-fire, Unpredictable.',
                'Browser Web Speech API fallback when API keys are off.',
                'Final debrief: strengths, improvements, standout, biggest gap.',
              ].map((line) => (
                <li
                  key={line}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12,
                    fontSize: 14,
                    color: 'var(--landing-fg)',
                  }}
                >
                  <span
                    aria-hidden
                    style={{
                      flexShrink: 0,
                      marginTop: 7,
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #22D3EE, #A78BFA)',
                      boxShadow: '0 0 12px rgba(34,211,238,0.5)',
                    }}
                  />
                  {line}
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>

      <style>{`
        @media (min-width: 768px) {
          #interview .container > div > div:nth-child(1) { order: 1; }
          #interview .container > div > div:nth-child(2) { order: 2; }
        }
      `}</style>
    </section>
  )
}

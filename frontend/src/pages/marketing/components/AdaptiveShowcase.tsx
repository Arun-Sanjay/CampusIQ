import { motion } from 'framer-motion'
import { Network } from 'lucide-react'

const reveal = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
}

export default function AdaptiveShowcase() {
  return (
    <section id="adaptive" className="section grid-bg">
      <div className="container">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 56,
            alignItems: 'center',
          }}
        >
          <motion.div {...reveal}>
            <span className="chip" style={{ marginBottom: 20 }}>
              <Network size={12} strokeWidth={2.5} />
              RESEARCH CORE — PHASE 15
            </span>
            <h2
              className="display"
              style={{
                fontSize: 'clamp(32px, 4.5vw, 52px)',
                margin: '0 0 20px',
              }}
            >
              Your shortest path to{' '}
              <span className="gradient-text">placement-ready.</span>
            </h2>
            <p
              style={{
                fontSize: 16,
                lineHeight: 1.7,
                color: 'var(--landing-fg-muted)',
                marginBottom: 28,
              }}
            >
              Tell CampusIQ which company you're targeting and how many hours you have. The Adaptive Learning Engine runs Dijkstra over a weighted skill graph, with edges that re-weight live based on your quiz performance, then solves a 0/1 Knapsack DP to pack the highest-value topics into your time budget.
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
                'Dijkstra finds the shortest learning path to every required skill.',
                'Edge weights adjust per student via mastery × prerequisite gap.',
                'Knapsack picks the topics that fit your hours.',
                'Prim’s MST renders the minimum prerequisite tree.',
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
                      background: 'linear-gradient(135deg, #A78BFA, #22D3EE)',
                      boxShadow: '0 0 12px rgba(167,139,250,0.5)',
                    }}
                  />
                  {line}
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            {...reveal}
            transition={{ ...reveal.transition, delay: 0.1 }}
            style={{ position: 'relative', minHeight: 420 }}
          >
            <span
              aria-hidden
              className="halo"
              style={{
                width: 280,
                height: 280,
                background: 'radial-gradient(circle, rgba(139,92,246,0.55), transparent 60%)',
                top: '-40px',
                right: '-40px',
              }}
            />
            <div
              className="glass"
              style={{
                aspectRatio: '4 / 3',
                width: '100%',
                position: 'relative',
                zIndex: 1,
                overflow: 'hidden',
                padding: 0,
              }}
            >
              <img
                src="/img/adaptive-skill-graph.png"
                alt="Stylized skill graph showing the shortest learning path"
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
        </div>
      </div>
    </section>
  )
}

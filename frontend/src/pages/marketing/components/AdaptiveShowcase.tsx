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
              className="glass img-slot"
              data-img="adaptive-skill-graph"
              data-img-label="adaptive-skill-graph"
              style={{
                aspectRatio: '4 / 3',
                width: '100%',
                position: 'relative',
                zIndex: 1,
                overflow: 'hidden',
              }}
            >
              {/* Decorative skeletal graph rendered until image is dropped in */}
              <svg
                viewBox="0 0 400 300"
                width="100%"
                height="100%"
                aria-hidden
                style={{ position: 'absolute', inset: 0 }}
              >
                <defs>
                  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stopColor="#A78BFA" stopOpacity="0.7" />
                    <stop offset="1" stopColor="#22D3EE" stopOpacity="0.7" />
                  </linearGradient>
                  <radialGradient id="node" cx="0.5" cy="0.5" r="0.5">
                    <stop offset="0" stopColor="#FFFFFF" stopOpacity="1" />
                    <stop offset="0.6" stopColor="#A78BFA" stopOpacity="0.9" />
                    <stop offset="1" stopColor="#A78BFA" stopOpacity="0" />
                  </radialGradient>
                </defs>
                <g stroke="url(#edge)" strokeWidth="1.2" fill="none" opacity="0.9">
                  <path d="M60,200 L160,140" />
                  <path d="M60,200 L160,240" />
                  <path d="M160,140 L260,90" />
                  <path d="M160,140 L260,170" />
                  <path d="M160,240 L260,250" />
                  <path d="M260,90 L350,70" />
                  <path d="M260,170 L350,140" />
                  <path d="M260,170 L350,210" />
                  <path d="M260,250 L350,260" />
                </g>
                <g>
                  {[
                    [60, 200, 6],
                    [160, 140, 5],
                    [160, 240, 5],
                    [260, 90, 5],
                    [260, 170, 7],
                    [260, 250, 5],
                    [350, 70, 4],
                    [350, 140, 4],
                    [350, 210, 4],
                    [350, 260, 4],
                  ].map(([x, y, r], i) => (
                    <g key={i}>
                      <circle cx={x} cy={y} r={(r as number) + 6} fill="url(#node)" opacity="0.45" />
                      <circle cx={x} cy={y} r={r} fill="#ECECEE" />
                    </g>
                  ))}
                </g>
              </svg>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

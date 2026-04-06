import { useTheme } from '../../hooks/useTheme'

function PremiumV1Background() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <div className="absolute w-[600px] h-[600px] rounded-full opacity-[0.07] blur-[120px] animate-float"
        style={{ background: 'radial-gradient(circle, #7B61FF, transparent)', top: '10%', left: '15%' }} />
      <div className="absolute w-[500px] h-[500px] rounded-full opacity-[0.05] blur-[100px] animate-float"
        style={{ background: 'radial-gradient(circle, #3B82F6, transparent)', top: '60%', right: '10%', animationDelay: '-2s' }} />
      <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.04] blur-[80px] animate-float"
        style={{ background: 'radial-gradient(circle, #A855F7, transparent)', bottom: '20%', left: '40%', animationDelay: '-4s' }} />
    </div>
  )
}

function AuroraBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Main aurora bands */}
      <div className="absolute w-[900px] h-[400px] opacity-[0.06] blur-[80px] animate-aurora-drift"
        style={{ background: 'linear-gradient(180deg, transparent, #00FFC8, #00B4FF, transparent)', top: '5%', left: '10%', transform: 'rotate(-5deg)' }} />
      <div className="absolute w-[700px] h-[350px] opacity-[0.05] blur-[100px] animate-aurora-drift"
        style={{ background: 'linear-gradient(180deg, transparent, #00E5A0, #00D4FF, transparent)', top: '30%', right: '5%', animationDelay: '-4s', transform: 'rotate(3deg)' }} />
      <div className="absolute w-[500px] h-[300px] opacity-[0.04] blur-[90px] animate-aurora-drift"
        style={{ background: 'linear-gradient(180deg, transparent, #80FFD0, #40C0FF, transparent)', bottom: '10%', left: '30%', animationDelay: '-8s', transform: 'rotate(-2deg)' }} />
      {/* Subtle star dots */}
      {Array.from({ length: 30 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-white animate-pulse-slow"
          style={{
            width: Math.random() * 2 + 1,
            height: Math.random() * 2 + 1,
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            opacity: Math.random() * 0.3 + 0.1,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${Math.random() * 3 + 2}s`,
          }}
        />
      ))}
    </div>
  )
}

function LuxuryBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Gold radial accents */}
      {/* Large gold ambient glow */}
      <div className="absolute w-[700px] h-[700px] rounded-full opacity-[0.10] blur-[150px] animate-float"
        style={{ background: 'radial-gradient(circle, #D4AF37, transparent)', top: '5%', right: '15%' }} />
      <div className="absolute w-[500px] h-[500px] rounded-full opacity-[0.08] blur-[120px] animate-float"
        style={{ background: 'radial-gradient(circle, #B8860B, transparent)', bottom: '15%', left: '10%', animationDelay: '-3s' }} />
      <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.06] blur-[100px] animate-float"
        style={{ background: 'radial-gradient(circle, #F5D060, transparent)', top: '50%', left: '50%', animationDelay: '-5s' }} />
      {/* Diagonal gold line accents */}
      <div className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `repeating-linear-gradient(
            135deg,
            transparent,
            transparent 80px,
            rgba(212,175,55,0.4) 80px,
            rgba(212,175,55,0.4) 81px
          )`,
        }}
      />
      {/* Gold particle dots */}
      {Array.from({ length: 25 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full animate-float animate-gold-shimmer"
          style={{
            width: Math.random() * 3 + 1.5,
            height: Math.random() * 3 + 1.5,
            background: `rgba(212,175,55,${Math.random() * 0.5 + 0.3})`,
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 6}s`,
          }}
        />
      ))}
    </div>
  )
}

export default function GradientMesh() {
  const { theme } = useTheme()

  return (
    <>
      {theme === 'premium' && <PremiumV1Background />}
      {theme === 'aurora' && <AuroraBackground />}
      {theme === 'luxury' && <LuxuryBackground />}

      {/* Noise overlay for all premium themes */}
      {(theme === 'premium' || theme === 'aurora' || theme === 'luxury') && (
        <div className="noise-overlay" />
      )}
    </>
  )
}

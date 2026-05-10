import '../marketing/landing.css'

import MarketingNav from '../marketing/components/MarketingNav'
import Hero from '../marketing/components/Hero'
import FeatureBento from '../marketing/components/FeatureBento'
import AdaptiveShowcase from '../marketing/components/AdaptiveShowcase'
import InterviewShowcase from '../marketing/components/InterviewShowcase'
import CTASection from '../marketing/components/CTASection'
import Footer from '../marketing/components/Footer'

export default function LandingPage() {
  return (
    <div className="landing-theme">
      <MarketingNav />
      <Hero />
      <FeatureBento />
      <AdaptiveShowcase />
      <InterviewShowcase />
      <CTASection />
      <Footer />
    </div>
  )
}

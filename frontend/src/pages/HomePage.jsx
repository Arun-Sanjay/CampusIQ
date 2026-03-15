import PageSection from '../components/PageSection'
import { homeHighlights } from '../features/dashboard/data'
import { usePageTitle } from '../hooks/usePageTitle'

function HomePage() {
  usePageTitle('Home')

  return (
    <PageSection
      eyebrow="Platform Overview"
      title="Home Page"
      description="CampusIQ V1 is being scaffolded as an AI-assisted academic platform for teacher content workflows, student study tools, and role-based analytics."
      items={homeHighlights}
    />
  )
}

export default HomePage

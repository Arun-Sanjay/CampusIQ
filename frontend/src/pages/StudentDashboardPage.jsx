import PageSection from '../components/PageSection'
import { dashboardModules } from '../features/dashboard/data'
import { usePageTitle } from '../hooks/usePageTitle'

function StudentDashboardPage() {
  usePageTitle('Student Dashboard')

  return (
    <PageSection
      eyebrow="Student Workspace"
      title="Student Dashboard Page"
      description="Scaffold for studying AI-generated summaries, flashcards, and quizzes while tracking learning progress."
      items={dashboardModules.student}
    />
  )
}

export default StudentDashboardPage

import PageSection from '../components/PageSection'
import { dashboardModules } from '../features/dashboard/data'
import { usePageTitle } from '../hooks/usePageTitle'

function TeacherDashboardPage() {
  usePageTitle('Teacher Dashboard')

  return (
    <PageSection
      eyebrow="Teacher Workspace"
      title="Teacher Dashboard Page"
      description="Scaffold for uploading study documents, generating AI learning materials, editing quizzes, and monitoring student progress."
      items={dashboardModules.teacher}
    />
  )
}

export default TeacherDashboardPage

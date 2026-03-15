import PageSection from '../components/PageSection'
import { dashboardModules } from '../features/dashboard/data'
import { usePageTitle } from '../hooks/usePageTitle'

function AdminDashboardPage() {
  usePageTitle('Admin Dashboard')

  return (
    <PageSection
      eyebrow="Admin Workspace"
      title="Admin Dashboard Page"
      description="Scaffold for overseeing platform access, operational health, and institution-level analytics."
      items={dashboardModules.admin}
    />
  )
}

export default AdminDashboardPage

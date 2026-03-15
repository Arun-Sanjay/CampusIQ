import PageSection from '../components/PageSection'
import { usePageTitle } from '../hooks/usePageTitle'

const loginItems = [
  {
    kicker: 'Authentication',
    title: 'Login form placeholder',
    description:
      'This route is ready for a real auth form once Supabase or another auth provider is wired in.',
  },
  {
    kicker: 'Routing',
    title: 'Post-login redirects',
    description:
      'Role-aware navigation can later send users to the correct student, teacher, or admin dashboard.',
  },
]

function LoginPage() {
  usePageTitle('Login')

  return (
    <PageSection
      eyebrow="Access"
      title="Login Page"
      description="Use this route as the entry point for the future authentication flow. No real auth logic is connected yet."
      items={loginItems}
    />
  )
}

export default LoginPage

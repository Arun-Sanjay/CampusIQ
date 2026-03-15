import PageSection from '../components/PageSection'
import { usePageTitle } from '../hooks/usePageTitle'

const signupItems = [
  {
    kicker: 'Onboarding',
    title: 'Signup form placeholder',
    description:
      'Reserved for account creation, role assignment, and institution onboarding logic.',
  },
  {
    kicker: 'Validation',
    title: 'Profile setup',
    description:
      'A future iteration can collect name, organization, and role-specific metadata here.',
  },
]

function SignupPage() {
  usePageTitle('Signup')

  return (
    <PageSection
      eyebrow="Account Creation"
      title="Signup Page"
      description="This route is scaffolded for the future registration experience and remains intentionally non-functional."
      items={signupItems}
    />
  )
}

export default SignupPage

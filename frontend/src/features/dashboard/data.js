export const homeHighlights = [
  {
    kicker: 'Role-aware',
    title: 'Three workspace types',
    description:
      'Separate dashboard entry points keep student, teacher, and admin concerns isolated from the start.',
  },
  {
    kicker: 'AI workflow',
    title: 'Summary and quiz pipeline',
    description:
      'The scaffold leaves room for document upload, AI summary generation, quiz review, and publishing.',
  },
  {
    kicker: 'Progress signals',
    title: 'Analytics-ready structure',
    description:
      'Teachers and admins will be able to inspect learner progress once backend services and tracking land.',
  },
]

export const dashboardModules = {
  teacher: [
    {
      kicker: 'Content',
      title: 'Document uploads',
      description:
        'Placeholder space for class resources, syllabus material, and processing status.',
    },
    {
      kicker: 'AI tools',
      title: 'Summaries and quizzes',
      description:
        'Will support summary generation, quiz editing, and controlled publishing flows.',
    },
    {
      kicker: 'Insight',
      title: 'Student progress',
      description:
        'Reserved for per-class completion stats and topic-level performance snapshots.',
    },
  ],
  student: [
    {
      kicker: 'Study',
      title: 'Summaries',
      description:
        'Quick review materials generated from teacher-uploaded course content.',
    },
    {
      kicker: 'Recall',
      title: 'Flashcards',
      description:
        'Placeholder workspace for spaced-repetition style revision and topic drills.',
    },
    {
      kicker: 'Practice',
      title: 'Quizzes',
      description:
        'Students will take published quizzes and track confidence over time.',
    },
  ],
  admin: [
    {
      kicker: 'Governance',
      title: 'User oversight',
      description:
        'Reserved for role management, organization settings, and account health.',
    },
    {
      kicker: 'Operations',
      title: 'Platform activity',
      description:
        'Placeholder area for system usage summaries, queues, and service visibility.',
    },
    {
      kicker: 'Reporting',
      title: 'Adoption analytics',
      description:
        'Will eventually surface institution-wide engagement and content activity.',
    },
  ],
}

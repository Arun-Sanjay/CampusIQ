import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import GradientMesh from './GradientMesh'
import PageTransition from './PageTransition'
import { useAuthStore } from '../../store/authStore'

type Role = 'student' | 'teacher' | 'admin'

const pageTitles: Record<string, string> = {
  '/student': 'Dashboard',
  '/student/notes': 'AI Note Assistant',
  '/student/college-gpt': 'CollegeGPT',
  '/student/quizzes': 'Quiz Engine',
  '/student/community': 'Doubt Community',
  '/student/schedule': 'Study Schedule',
  '/student/resume': 'Resume Builder',
  '/student/skill-gap': 'Skill Gap Analyzer',
  '/student/interview': 'Mock Interview',
  '/student/confidence': 'Confidence Coach',
  '/student/jobs': 'Job Tracker',
  '/student/placement-chat': 'Placement Chat',
  '/student/crash-mode': 'Crash Mode',
  '/student/skill-tree': 'Skill Tree',
  '/student/leaderboard': 'Leaderboard',
  '/student/profile': 'My Profile',
  '/teacher': 'Dashboard',
  '/teacher/subjects': 'My Subjects',
  '/teacher/documents': 'Documents',
  '/teacher/quizzes': 'Quiz Management',
  '/teacher/announcements': 'Announcements',
  '/teacher/quiz-scheduling': 'Quiz Scheduling',
  '/teacher/analytics': 'Class Performance',
  '/teacher/students': 'Student Details',
  '/teacher/similarity': 'Similarity Checker',
  '/admin': 'Dashboard',
  '/admin/college-docs': 'College Documents',
  '/admin/users': 'User Management',
  '/admin/skill-analytics': 'Skill Analytics',
  '/admin/notifications': 'Notification Status',
}

function getRoleFromPath(pathname: string): Role {
  if (pathname.startsWith('/teacher')) return 'teacher'
  if (pathname.startsWith('/admin')) return 'admin'
  return 'student'
}

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const role: Role = user?.role ?? getRoleFromPath(location.pathname)
  const title = pageTitles[location.pathname] || 'CampusIQ'

  // Student-only stats — pull from profile once available, fallback to placeholders
  const sp = user?.student_profile
  const stats = {
    streak: sp?.streak_days ?? 0,
    level: sp?.current_level ?? 1,
    // CampusIQ score comes from a separate endpoint in Phase 12; show a placeholder for now
    score: undefined as number | undefined,
  }

  const displayUser = {
    name: user?.full_name || 'User',
    email: user?.email || '',
  }

  return (
    <div className="min-h-screen relative" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Premium gradient mesh background */}
      <GradientMesh />

      <Sidebar
        role={role}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        user={displayUser}
      />

      <div
        className={clsx(
          'min-h-screen transition-all duration-300 flex flex-col relative z-10',
          sidebarCollapsed ? 'ml-16' : 'ml-60',
        )}
      >
        <TopBar
          title={title}
          streak={role === 'student' ? stats.streak : undefined}
          level={role === 'student' ? stats.level : undefined}
          score={role === 'student' ? stats.score : undefined}
        />

        <main className="flex-1 p-6">
          <AnimatePresence mode="wait">
            <PageTransition key={location.pathname}>
              <Outlet />
            </PageTransition>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

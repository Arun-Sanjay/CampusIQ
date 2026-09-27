import {
  LayoutDashboard, BookOpen, GraduationCap, Brain, MessageSquare,
  Calendar, FileText, Target, Mic, Video, Briefcase, MessageCircle,
  Trophy, User, Upload, BarChart3, Users, Shield, Bell, ClipboardList,
  GitBranch, AlertTriangle, Swords, PenLine, Code2, UserPlus, ScanText, Award,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type Role = 'student' | 'teacher' | 'admin'

export interface NavItem {
  to: string
  icon: LucideIcon
  label: string
  /** Match the route exactly (used for index routes like `/student`). */
  end?: boolean
}

export interface NavSection {
  group: string
  items: NavItem[]
}

const studentNav: NavSection[] = [
  {
    group: 'LEARN MODE',
    items: [
      { to: '/student', icon: LayoutDashboard, label: 'Dashboard', end: true },
      { to: '/student/notes', icon: BookOpen, label: 'AI Note Assistant' },
      { to: '/student/coding', icon: Code2, label: 'Coding' },
      { to: '/student/college-gpt', icon: GraduationCap, label: 'CollegeGPT' },
      { to: '/student/quizzes', icon: Brain, label: 'Quiz Engine' },
      { to: '/student/community', icon: MessageSquare, label: 'Doubt Community' },
      { to: '/student/schedule', icon: Calendar, label: 'Study Schedule' },
    ],
  },
  {
    group: 'PLACE MODE',
    items: [
      { to: '/student/resume', icon: FileText, label: 'Resume Builder' },
      { to: '/student/skill-gap', icon: Target, label: 'Skill Gap Analyzer' },
      { to: '/student/interview', icon: Mic, label: 'Mock Interview' },
      { to: '/student/confidence', icon: Video, label: 'Confidence Coach' },
      { to: '/student/jobs', icon: Briefcase, label: 'Job Tracker' },
      { to: '/student/placement-chat', icon: MessageCircle, label: 'Placement Chat' },
      { to: '/student/crash-mode', icon: AlertTriangle, label: 'Crash Mode' },
    ],
  },
  {
    group: 'PROFILE',
    items: [
      { to: '/student/grades', icon: Award, label: 'My Grades' },
      { to: '/student/skill-tree', icon: GitBranch, label: 'Skill Tree' },
      { to: '/student/leaderboard', icon: Trophy, label: 'Leaderboard' },
      { to: '/student/boss-battles', icon: Swords, label: 'Boss Battles' },
      { to: '/student/profile', icon: User, label: 'My Profile' },
    ],
  },
]

const teacherNav: NavSection[] = [
  {
    group: 'DASHBOARD',
    items: [
      { to: '/teacher', icon: LayoutDashboard, label: 'Overview', end: true },
      { to: '/teacher/subjects', icon: BookOpen, label: 'My Subjects' },
      { to: '/teacher/roster', icon: UserPlus, label: 'My Students' },
      { to: '/teacher/announcements', icon: Bell, label: 'Announcements' },
    ],
  },
  {
    group: 'CONTENT',
    items: [
      { to: '/teacher/documents', icon: Upload, label: 'Documents' },
      { to: '/teacher/quizzes', icon: ClipboardList, label: 'Quiz Management' },
      { to: '/teacher/grading', icon: ScanText, label: 'AI Auto-Grader' },
      { to: '/teacher/quiz-scheduling', icon: Calendar, label: 'Quiz Scheduling' },
    ],
  },
  {
    group: 'ANALYTICS',
    items: [
      { to: '/teacher/analytics', icon: BarChart3, label: 'Class Performance' },
      { to: '/teacher/grades', icon: Award, label: 'Class Grades' },
      { to: '/teacher/students', icon: Users, label: 'Student Details' },
      { to: '/teacher/similarity', icon: Shield, label: 'Similarity Checker' },
    ],
  },
]

const adminNav: NavSection[] = [
  {
    group: 'DASHBOARD',
    items: [
      { to: '/admin', icon: LayoutDashboard, label: 'Overview', end: true },
      { to: '/admin/college-docs', icon: Upload, label: 'College Documents' },
      { to: '/admin/knowledge', icon: PenLine, label: 'Knowledge Editor' },
      { to: '/admin/users', icon: Users, label: 'User Management' },
    ],
  },
  {
    group: 'ANALYTICS',
    items: [
      { to: '/admin/skill-analytics', icon: BarChart3, label: 'Skill Analytics' },
      { to: '/admin/notifications', icon: Bell, label: 'Notification Status' },
    ],
  },
]

export const navByRole: Record<Role, NavSection[]> = {
  student: studentNav,
  teacher: teacherNav,
  admin: adminNav,
}

/**
 * The 4 thumb-reachable destinations shown in the mobile bottom tab bar per
 * role. Short labels (vs the full sidebar labels) so they fit a tab. A 5th
 * "More" entry is added by BottomTabBar to open the full nav drawer.
 */
export const primaryNavByRole: Record<Role, NavItem[]> = {
  student: [
    { to: '/student', icon: LayoutDashboard, label: 'Home', end: true },
    { to: '/student/coding', icon: Code2, label: 'Coding' },
    { to: '/student/quizzes', icon: Brain, label: 'Quizzes' },
    { to: '/student/notes', icon: BookOpen, label: 'Notes' },
  ],
  teacher: [
    { to: '/teacher', icon: LayoutDashboard, label: 'Home', end: true },
    { to: '/teacher/roster', icon: UserPlus, label: 'Students' },
    { to: '/teacher/quizzes', icon: ClipboardList, label: 'Quizzes' },
    { to: '/teacher/grading', icon: ScanText, label: 'Grading' },
  ],
  admin: [
    { to: '/admin', icon: LayoutDashboard, label: 'Home', end: true },
    { to: '/admin/college-docs', icon: Upload, label: 'Docs' },
    { to: '/admin/users', icon: Users, label: 'Users' },
    { to: '/admin/knowledge', icon: PenLine, label: 'Editor' },
  ],
}

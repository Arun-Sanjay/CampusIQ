import {
  createBrowserRouter,
  createRoutesFromElements,
  Route,
  RouterProvider,
} from 'react-router-dom'

import AppLayout from '../components/layout/AppLayout'

// Auth pages (no sidebar)
import LandingPage from '../pages/auth/LandingPage'
import LoginPage from '../pages/auth/LoginPage'
import SignupPage from '../pages/auth/SignupPage'

// Student pages
import StudentDashboard from '../pages/student/DashboardPage'
import NoteAssistantPage from '../pages/student/NoteAssistantPage'
import CollegeGPTPage from '../pages/student/CollegeGPTPage'
import QuizListPage from '../pages/student/QuizListPage'
import CommunityPage from '../pages/student/CommunityPage'
import SchedulePage from '../pages/student/SchedulePage'
import ResumeBuilderPage from '../pages/student/ResumeBuilderPage'
import SkillGapPage from '../pages/student/SkillGapPage'
import MockInterviewPage from '../pages/student/MockInterviewPage'
import ConfidenceCoachPage from '../pages/student/ConfidenceCoachPage'
import JobTrackerPage from '../pages/student/JobTrackerPage'
import PlacementChatPage from '../pages/student/PlacementChatPage'
import CrashModePage from '../pages/student/CrashModePage'
import SkillTreePage from '../pages/student/SkillTreePage'
import LeaderboardPage from '../pages/student/LeaderboardPage'
import ProfilePage from '../pages/student/ProfilePage'

// Teacher pages
import TeacherDashboard from '../pages/teacher/DashboardPage'
import SubjectsPage from '../pages/teacher/SubjectsPage'
import DocumentsPage from '../pages/teacher/DocumentsPage'
import QuizManagementPage from '../pages/teacher/QuizManagementPage'
import AnnouncementsPage from '../pages/teacher/AnnouncementsPage'
import QuizSchedulingPage from '../pages/teacher/QuizSchedulingPage'
import AnalyticsPage from '../pages/teacher/AnalyticsPage'
import StudentDetailsPage from '../pages/teacher/StudentDetailsPage'
import SimilarityCheckerPage from '../pages/teacher/SimilarityCheckerPage'

// Admin pages
import AdminDashboard from '../pages/admin/DashboardPage'
import CollegeDocsPage from '../pages/admin/CollegeDocsPage'
import UserManagementPage from '../pages/admin/UserManagementPage'
import SkillAnalyticsPage from '../pages/admin/SkillAnalyticsPage'
import NotificationStatusPage from '../pages/admin/NotificationStatusPage'

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
      {/* Public routes (no sidebar) */}
      <Route path="/" element={<LandingPage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="signup" element={<SignupPage />} />

      {/* Student routes */}
      <Route path="student" element={<AppLayout />}>
        <Route index element={<StudentDashboard />} />
        <Route path="notes" element={<NoteAssistantPage />} />
        <Route path="college-gpt" element={<CollegeGPTPage />} />
        <Route path="quizzes" element={<QuizListPage />} />
        <Route path="community" element={<CommunityPage />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="resume" element={<ResumeBuilderPage />} />
        <Route path="skill-gap" element={<SkillGapPage />} />
        <Route path="interview" element={<MockInterviewPage />} />
        <Route path="confidence" element={<ConfidenceCoachPage />} />
        <Route path="jobs" element={<JobTrackerPage />} />
        <Route path="placement-chat" element={<PlacementChatPage />} />
        <Route path="crash-mode" element={<CrashModePage />} />
        <Route path="skill-tree" element={<SkillTreePage />} />
        <Route path="leaderboard" element={<LeaderboardPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>

      {/* Teacher routes */}
      <Route path="teacher" element={<AppLayout />}>
        <Route index element={<TeacherDashboard />} />
        <Route path="subjects" element={<SubjectsPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="quizzes" element={<QuizManagementPage />} />
        <Route path="announcements" element={<AnnouncementsPage />} />
        <Route path="quiz-scheduling" element={<QuizSchedulingPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="students" element={<StudentDetailsPage />} />
        <Route path="similarity" element={<SimilarityCheckerPage />} />
      </Route>

      {/* Admin routes */}
      <Route path="admin" element={<AppLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="college-docs" element={<CollegeDocsPage />} />
        <Route path="users" element={<UserManagementPage />} />
        <Route path="skill-analytics" element={<SkillAnalyticsPage />} />
        <Route path="notifications" element={<NotificationStatusPage />} />
      </Route>
    </>,
  ),
)

export function AppRouter() {
  return <RouterProvider router={router} />
}

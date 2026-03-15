import {
  createBrowserRouter,
  createRoutesFromElements,
  Route,
  RouterProvider,
} from 'react-router-dom'

import AppLayout from '../components/layout/AppLayout'
import AdminDashboardPage from '../pages/AdminDashboardPage'
import HomePage from '../pages/HomePage'
import LoginPage from '../pages/LoginPage'
import SignupPage from '../pages/SignupPage'
import StudentDashboardPage from '../pages/StudentDashboardPage'
import TeacherDashboardPage from '../pages/TeacherDashboardPage'

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route path="/" element={<AppLayout />}>
      <Route index element={<HomePage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="signup" element={<SignupPage />} />
      <Route path="teacher" element={<TeacherDashboardPage />} />
      <Route path="student" element={<StudentDashboardPage />} />
      <Route path="admin" element={<AdminDashboardPage />} />
    </Route>,
  ),
)

export function AppRouter() {
  return <RouterProvider router={router} />
}

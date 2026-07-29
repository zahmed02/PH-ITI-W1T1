// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Doctors from './pages/Doctors';
import Appointments from './pages/Appointments';
import CalendarPage from './pages/CalendarPage';
import AdminPanel from './pages/AdminPanel';
import AppointmentSlips from './pages/AppointmentSlips';
import Login from './pages/Login';
import Register from './pages/Register';
import ProtectedRoute from './auth/ProtectedRoute';
import { AuthProvider, useAuth } from './auth/AuthContext';

// The AI Assistant (booking chat) isn't available to doctor logins - see
// backend/chat_router.py, which returns 403 for role="doctor". Rather than
// let a doctor land on a page that will just error, send them straight to
// their schedule instead.
function IndexRoute() {
  const { user } = useAuth();
  if (user?.role === 'doctor') {
    return <Navigate to="/calendar" replace />;
  }
  return <Home />;
}

function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Everything below requires a valid, non-logged-out session.
          Typing /calendar, /doctors, or /admin directly while logged out
          redirects to /login instead of rendering the page. */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<IndexRoute />} />
          <Route path="doctors" element={<Doctors />} />
          <Route path="appointments" element={<Appointments />} />
          <Route path="calendar" element={<CalendarPage />} />

          {/* Doctor-only - the "3rd menu option": view the same PDF slip
              patients received, cancel a visit, or transfer a cancelled
              patient to a colleague. */}
          <Route element={<ProtectedRoute allow={['doctor']} />}>
            <Route path="slips" element={<AppointmentSlips />} />
          </Route>

          {/* Admin-only - a logged-in patient/doctor hitting /admin
              directly gets redirected to "/" rather than seeing the page,
              since ProtectedRoute's `allow` check runs before this
              renders. */}
          <Route element={<ProtectedRoute allow={['admin']} />}>
            <Route path="admin" element={<AdminPanel />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function WrappedApp() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  );
}
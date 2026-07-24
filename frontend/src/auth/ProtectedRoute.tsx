// frontend/src/auth/ProtectedRoute.tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { Role } from '../api/auth';

interface ProtectedRouteProps {
  /** If provided, only these roles may access the nested routes. Omit to
   *  allow any logged-in role through (still requires being logged in). */
  allow?: Role[];
}

export default function ProtectedRoute({ allow }: ProtectedRouteProps) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    // Brief moment while we validate any stored token against the backend.
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-on-surface-variant text-sm">Checking your session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Typing /calendar, /doctors, or /admin directly while logged out
    // lands here - it never renders the protected page, it redirects to
    // /login instead.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (allow && user && !allow.includes(user.role)) {
    // Logged in, but the wrong role for this section (e.g. a patient
    // trying to reach /admin). They ARE authenticated, so redirect to the
    // app home rather than back to /login.
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
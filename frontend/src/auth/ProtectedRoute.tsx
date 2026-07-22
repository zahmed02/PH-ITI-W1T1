import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
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
    // Typing /calendar or /doctors directly while logged out lands here -
    // it never renders the protected page, it redirects to /login instead.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

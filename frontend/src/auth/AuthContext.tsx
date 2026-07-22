// frontend/src/auth/AuthContext.tsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { fetchMe, loginRequest, logoutRequest, registerRequest } from '../api/auth';
import { getStoredAuth, setStoredAuth, clearStoredAuth, subscribeToAuthChanges } from './authStorage';

interface AuthUser {
  id: number;
  username: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Re-checks localStorage and, if a token is present, validates it against
  // the backend (this also catches tokens revoked server-side, e.g. logged
  // out from a different browser/device, not just this one).
  const syncFromStorage = useCallback(async () => {
    const stored = getStoredAuth();
    if (!stored?.token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser({ id: me.id, username: me.username });
    } catch {
      clearStoredAuth();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    syncFromStorage();

    // Fires instantly when the auth key changes - in this tab (custom
    // event) or any other tab of the same origin (native storage event).
    const unsubscribe = subscribeToAuthChanges(() => {
      const stored = getStoredAuth();
      if (!stored?.token) {
        // Logged out (here or elsewhere) - reflect it immediately without
        // waiting on a network round trip.
        setUser(null);
        setLoading(false);
      } else {
        // Token appeared/changed (e.g. logged in in another tab) - validate it.
        syncFromStorage();
      }
    });

    return unsubscribe;
  }, [syncFromStorage]);

  const login = async (username: string, password: string) => {
    const data = await loginRequest(username, password);
    setStoredAuth({ token: data.access_token, username: data.username });
    setUser({ id: data.user_id, username: data.username });
  };

  const register = async (username: string, password: string) => {
    const data = await registerRequest(username, password);
    setStoredAuth({ token: data.access_token, username: data.username });
    setUser({ id: data.user_id, username: data.username });
  };

  const logout = async () => {
    try {
      await logoutRequest();
    } catch {
      // Best-effort - even if the network call fails, clear locally so the
      // user isn't stuck "logged in" on a dead connection.
    }
    clearStoredAuth();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
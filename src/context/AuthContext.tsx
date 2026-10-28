// ============================================================
// Authentication Context
// Provides logged-in user state, login, signup, and logout methods
// ============================================================

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService, type AuthUser, type RegistrationResult } from '@/services/auth';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<RegistrationResult>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => authService.getStoredUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    authService.verifySession().then(verifiedUser => {
      if (mounted) {
        setUser(verifiedUser);
        setLoading(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const session = await authService.login(email, password);
    setUser(session.user);
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    const result = await authService.register(email, password, displayName);
    if (result.session) {
      setUser(result.session.user);
    }
    return result;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

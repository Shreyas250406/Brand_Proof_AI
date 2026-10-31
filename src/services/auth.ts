// ============================================================
// Authentication Service for BrandProof AI
// Communicates with FastAPI Supabase Auth endpoints and direct Supabase
// ============================================================

export interface AuthUser {
  id: string;
  email: string;
  displayName?: string;
}

export interface AuthSession {
  user: AuthUser;
  accessToken: string;
  refreshToken?: string;
  expiresAt?: number;
}

export interface RegistrationResult {
  user?: AuthUser;
  session?: AuthSession | null;
  requiresConfirmation: boolean;
  message?: string;
}

const TOKEN_KEY = 'brandproof_auth_token';
const USER_KEY = 'brandproof_auth_user';

export const SUPABASE_CONFIG = {
  url: 'https://njxdmshsnorqtsgkzsqc.supabase.co',
  publishableKey: 'sb_publishable_ECnWMTxGBceW-cDUW4Z9fw_h_TvFJpe',
};

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = `${BASE_URL}/api/v1/ai`;

/**
 * Fast network fetch wrapper with configurable abort timeout to prevent UI hanging.
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 3500): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

export const DEMO_ADMIN_SESSION: AuthSession = {
  user: {
    id: '00000000-0000-4000-a000-000000000001',
    email: 'admin@brandproof.ai',
    displayName: 'Brand Admin',
  },
  accessToken: 'brandproof_demo_admin_jwt_token',
  expiresAt: Math.floor(Date.now() / 1000) + 86400 * 30,
};

export const authService = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  getStoredUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      return null;
    }
  },

  setSession(session: AuthSession): void {
    localStorage.setItem(TOKEN_KEY, session.accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(session.user));
  },

  clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  async login(email: string, password: string): Promise<AuthSession> {
    const cleanEmail = email.trim().toLowerCase();

    // Fast path: instant verification for demo Brand Admin
    if (cleanEmail === 'admin@brandproof.ai' && password === 'BrandProof2026!') {
      this.setSession(DEMO_ADMIN_SESSION);
      return DEMO_ADMIN_SESSION;
    }

    try {
      // 1. Try FastAPI backend endpoint with fast 3.5s timeout
      const res = await fetchWithTimeout(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: cleanEmail, password }),
      }, 3500);

      if (res.ok) {
        const data = await res.json();
        const session: AuthSession = {
          user: {
            id: data.user_id,
            email: data.email,
            displayName: data.display_name,
          },
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          expiresAt: data.expires_at,
        };
        this.setSession(session);
        return session;
      }

      // If backend gave a specific 401 error message
      if (res.status === 401 || res.status === 400) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || 'Invalid email or password.');
      }
    } catch (e: unknown) {
      if (e instanceof Error && !e.message.includes('Failed to fetch') && e.name !== 'AbortError') {
        throw e;
      }
    }

    // 2. Direct Supabase fallback with fast 3.5s timeout
    const directRes = await fetchWithTimeout(
      `${SUPABASE_CONFIG.url}/auth/v1/token?grant_type=password`,
      {
        method: 'POST',
        headers: {
          apikey: SUPABASE_CONFIG.publishableKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: cleanEmail, password }),
      },
      3500
    );

    if (!directRes.ok) {
      const err = await directRes.json().catch(() => ({}));
      throw new Error(err.error_description || err.msg || 'Invalid email or password.');
    }

    const data = await directRes.json();
    const session: AuthSession = {
      user: {
        id: data.user?.id,
        email: data.user?.email || email,
        displayName: data.user?.user_metadata?.display_name,
      },
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      expiresAt: data.expires_at,
    };
    this.setSession(session);
    return session;
  },

  async register(email: string, password: string, displayName?: string): Promise<RegistrationResult> {
    try {
      // 1. Try FastAPI backend endpoint first with 3.5s timeout
      const res = await fetchWithTimeout(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password, display_name: displayName?.trim() || undefined }),
      }, 3500);

      if (res.ok) {
        const data = await res.json();
        const user: AuthUser = {
          id: data.user_id,
          email: data.email,
          displayName: data.display_name,
        };

        // If registration returned access_token immediately (email confirmation disabled)
        if (data.access_token) {
          const session: AuthSession = {
            user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            expiresAt: data.expires_at,
          };
          this.setSession(session);
          return {
            user,
            session,
            requiresConfirmation: false,
            message: data.message || 'Account created successfully!',
          };
        }

        // Email confirmation is required / pending
        return {
          user,
          session: null,
          requiresConfirmation: true,
          message: data.message || 'Please check your email to confirm your account before logging in.',
        };
      }

      // If backend responded with an error status (400, 409, 422, etc.)
      const err = await res.json().catch(() => ({}));
      const errMessage =
        err.detail?.message ||
        err.message ||
        (typeof err.detail === 'string' ? err.detail : null) ||
        'Registration failed.';
      throw new Error(errMessage);
    } catch (e: unknown) {
      if (e instanceof Error && !e.message.includes('Failed to fetch') && e.name !== 'AbortError') {
        throw e;
      }
    }

    // 2. Direct Supabase fallback with 3.5s timeout
    const directRes = await fetchWithTimeout(`${SUPABASE_CONFIG.url}/auth/v1/signup`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_CONFIG.publishableKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email.trim(),
        password,
        data: displayName?.trim() ? { display_name: displayName.trim() } : undefined,
      }),
    }, 3500);

    if (!directRes.ok) {
      const err = await directRes.json().catch(() => ({}));
      if (err.error_code === 'over_email_send_rate_limit' || (err.msg && err.msg.includes('rate limit'))) {
        throw new Error('Email sending rate limit reached. Please wait a few minutes before trying again.');
      }
      throw new Error(err.msg || err.error_description || 'Registration failed.');
    }

    const data = await directRes.json();
    const userObj = data.user || data;

    // Supabase GoTrue returns identities: [] when an account with that email already exists
    if (userObj.identities && Array.isArray(userObj.identities) && userObj.identities.length === 0) {
      throw new Error('An account with this email address already exists. Please sign in instead.');
    }

    const user: AuthUser = {
      id: userObj.id,
      email: userObj.email || email,
      displayName: userObj.user_metadata?.display_name || displayName,
    };

    if (data.access_token) {
      const session: AuthSession = {
        user,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresAt: data.expires_at,
      };
      this.setSession(session);
      return {
        user,
        session,
        requiresConfirmation: false,
        message: 'Account created successfully!',
      };
    }

    return {
      user,
      session: null,
      requiresConfirmation: true,
      message: 'Please check your email to confirm your account before logging in.',
    };
  },

  async logout(): Promise<void> {
    const token = this.getToken();
    if (token) {
      try {
        await fetchWithTimeout(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        }, 2000);
      } catch {
        // Continue cleanup even if server is unreachable
      }
    }
    this.clearSession();
  },

  async verifySession(): Promise<AuthUser | null> {
    const token = this.getToken();
    if (!token) {
      this.clearSession();
      return null;
    }

    // Fast path: instant verification for demo Brand Admin
    if (token === DEMO_ADMIN_SESSION.accessToken) {
      return DEMO_ADMIN_SESSION.user;
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }, 2500);
      if (res.ok) {
        const data = await res.json();
        const user: AuthUser = {
          id: data.user_id,
          email: data.email,
          displayName: data.display_name,
        };
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return user;
      }
    } catch {
      // Fallback: check stored user
    }

    return this.getStoredUser();
  },

  async loginDemoAdmin(): Promise<AuthSession> {
    // Instant zero-latency authentication for Brand Admin
    this.setSession(DEMO_ADMIN_SESSION);
    return DEMO_ADMIN_SESSION;
  },
};

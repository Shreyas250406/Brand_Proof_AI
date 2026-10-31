// ============================================================
// Authentication Page (Login + Signup)
// ============================================================

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useApp } from '@/context/AppContext';

export function AuthPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login, register, loginDemoAdmin } = useAuth();
  const [demoLoading, setDemoLoading] = useState(false);
  const { addToast } = useApp();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please fill in both email and password.');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      if (isSignUp) {
        const result = await register(email.trim(), password, displayName.trim() || undefined);
        if (result.requiresConfirmation) {
          addToast({
            title: 'Account created!',
            description: result.message || `Please check your email (${email.trim()}) to confirm your account before logging in.`,
            variant: 'info',
          });
          setIsSignUp(false);
          setErrorMessage(null);
          return;
        }
        addToast({
          title: 'Account created!',
          description: `Welcome to BrandProof AI, ${displayName || email}!`,
          variant: 'success',
        });
      } else {
        await login(email.trim(), password);
        addToast({
          title: 'Welcome back!',
          description: `Logged in as ${email}.`,
          variant: 'success',
        });
      }
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed. Please check your credentials.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoAdminLogin = async () => {
    setErrorMessage(null);
    setDemoLoading(true);
    try {
      await loginDemoAdmin();
      addToast({
        title: 'Welcome, Brand Admin!',
        description: 'Logged in successfully with demo Brand Admin credentials.',
        variant: 'success',
      });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Demo login failed.';
      setErrorMessage(msg);
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-50 p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md space-y-6">
        {/* Brand header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand-600 shadow-md shadow-brand-500/20 text-white mb-2">
            <Shield className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-surface-900 tracking-tight">
            BrandProof AI
          </h1>
          <p className="text-sm text-surface-500">
            {isSignUp ? 'Create your brand quality assurance account' : 'Sign in to access your content quality dashboard'}
          </p>
        </div>

        {/* Card */}
        <div className="card p-6 sm:p-8 space-y-6 shadow-sm border border-surface-200 bg-white">
          {/* Mode Switcher Tabs */}
          <div className="flex rounded-lg bg-surface-100 p-1">
            <button
              type="button"
              onClick={() => {
                setIsSignUp(false);
                setErrorMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all ${
                !isSignUp
                  ? 'bg-white text-surface-900 shadow-xs'
                  : 'text-surface-500 hover:text-surface-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setIsSignUp(true);
                setErrorMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all ${
                isSignUp
                  ? 'bg-white text-surface-900 shadow-xs'
                  : 'text-surface-500 hover:text-surface-900'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs animate-in fade-in duration-150">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-600" />
              <div className="flex-1">{errorMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignUp && (
              <div>
                <label className="block text-xs font-medium text-surface-700 mb-1">
                  Display Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-surface-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    placeholder="e.g. Alex Morgan"
                    className="input pl-9 text-sm w-full"
                    autoComplete="name"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-surface-700 mb-1">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-surface-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="input pl-9 text-sm w-full"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-surface-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-surface-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  className="input pl-9 text-sm w-full"
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 text-sm font-semibold flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2.5 text-surface-400 font-medium">Or Quick Access</span>
            </div>
          </div>

          {/* Demo Brand Admin Login Button */}
          <div className="space-y-2">
            <button
              type="button"
              disabled={loading || demoLoading}
              onClick={handleDemoAdminLogin}
              className="w-full py-2.5 px-4 rounded-xl border border-brand-200 bg-brand-50/80 hover:bg-brand-100 text-brand-700 text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-xs hover:shadow-sm disabled:opacity-50"
              title="One-click login as Brand Admin using verified demo credentials"
            >
              {demoLoading ? (
                <div className="w-4 h-4 border-2 border-brand-600/30 border-t-brand-600 rounded-full animate-spin" />
              ) : (
                <>
                  <Shield className="w-4 h-4 text-brand-600" />
                  <span>Demo Credentials (Brand Admin Login)</span>
                </>
              )}
            </button>
            <p className="text-[11px] text-center text-surface-400">
              One-click instant login with pre-configured Brand Admin role (<code className="text-surface-600 font-mono">admin@brandproof.ai</code>)
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-surface-400">
          Powered by Supabase PostgreSQL Authentication & Google Gemini AI
        </p>
      </div>
    </div>
  );
}

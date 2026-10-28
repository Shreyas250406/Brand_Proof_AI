// ============================================================
// Authentication Page (Login + Signup)
// ============================================================

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useApp } from '@/context/AppContext';

export function AuthPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login, register } = useAuth();
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

  const fillAdminCredentials = () => {
    setEmail('admin@brandproof.ai');
    setPassword('BrandProof2026!');
    setIsSignUp(false);
    setErrorMessage(null);
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

          {/* Quick Initial User Fill */}
          <div className="pt-2 border-t border-surface-100 text-center">
            <button
              type="button"
              onClick={fillAdminCredentials}
              className="text-xs text-brand-600 hover:text-brand-700 font-medium inline-flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Use initial admin credentials (admin@brandproof.ai)</span>
            </button>
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
